import hashlib
import json
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlencode

import httpx

from app.modules.media.errors import MediaProviderUnavailableError


class MediaContentTooLargeError(Exception):
    """The provider returned more bytes than the authorized upload size."""


_ENCRYPTED_PART_BYTES = 8 * 1_048_576
_ENCRYPTED_MANIFEST_MAX_BYTES = 1_048_576
_ENCRYPTED_ASSET_MAX_BYTES = 104_857_600
_ENCRYPTED_MANIFEST_PREFIX = b"TMI-ENCRYPTED-PARTS-V1\n"


@dataclass(frozen=True, slots=True)
class UploadAuthorization:
    upload_url: str
    cloud_name: str
    api_key: str
    signature: str
    parameters: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ProviderAssetMetadata:
    public_id: str
    version: int
    resource_type: str
    delivery_type: str
    file_format: str
    bytes: int
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class PublicDerivativeMetadata:
    public_id: str
    url: str
    mime_type: str
    bytes: int
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None


@dataclass(frozen=True, slots=True)
class StoredEncryptedAsset:
    public_id: str
    version: int
    bytes: int


class MediaGateway(Protocol):
    async def create_upload_signature(
        self,
        *,
        public_id: str,
        resource_type: str,
        timestamp: int,
        allowed_format: str,
        max_bytes: int,
    ) -> UploadAuthorization: ...

    def verify_upload_result(
        self,
        *,
        public_id: str,
        version: int,
        signature: str,
    ) -> bool: ...

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> ProviderAssetMetadata: ...

    async def download_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes: ...

    async def upload_encrypted_asset(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredEncryptedAsset: ...

    def create_signed_delivery_url(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        expires_at: int,
    ) -> str: ...

    async def delete_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> None: ...

    async def close(self) -> None: ...


class PublicDerivativeGateway(Protocol):
    async def create_public_derivative(
        self,
        *,
        source_public_id: str,
        source_resource_type: str,
        source_format: str,
        derivative_public_id: str,
        transformation: str,
    ) -> PublicDerivativeMetadata: ...


class CloudinaryMediaGateway:
    _DELIVERY_TYPE = "authenticated"

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        timeout_seconds: float = 5.0,
        clock: Callable[[], float] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not cloud_name or not api_key or not api_secret:
            raise RuntimeError("Cloudinary credentials are not configured.")
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret
        self._clock = clock or time.time
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None

    def sign_parameters(self, parameters: Mapping[str, str]) -> str:
        # https://cloudinary.com/documentation/authentication_signatures
        serialized = "&".join(
            f"{key}={value}" for key, value in sorted(parameters.items()) if value != ""
        )
        return hashlib.sha1(
            f"{serialized}{self._api_secret}".encode(),
            usedforsecurity=True,
        ).hexdigest()

    async def create_upload_signature(
        self,
        *,
        public_id: str,
        resource_type: str,
        timestamp: int,
        allowed_format: str,
        max_bytes: int,
    ) -> UploadAuthorization:
        # Cloudinary accepts max_file_size only in upload presets. Including it
        # in a signed Upload API request makes Cloudinary omit it from its own
        # signature calculation and reject the request as an invalid signature.
        # Size is enforced when the intent is issued and metadata is verified.
        _ = max_bytes
        parameters = {
            "allowed_formats": allowed_format,
            "overwrite": "false",
            "public_id": public_id,
            "timestamp": str(timestamp),
            "type": self._DELIVERY_TYPE,
        }
        return UploadAuthorization(
            upload_url=(
                f"https://api.cloudinary.com/v1_1/"
                f"{quote(self._cloud_name, safe='')}/{resource_type}/upload"
            ),
            cloud_name=self._cloud_name,
            api_key=self._api_key,
            signature=self.sign_parameters(parameters),
            parameters=parameters,
        )

    def verify_upload_result(
        self,
        *,
        public_id: str,
        version: int,
        signature: str,
    ) -> bool:
        expected = self.sign_parameters(
            {"public_id": public_id, "version": str(version)}
        )
        return secrets.compare_digest(expected, signature)

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> ProviderAssetMetadata:
        url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{quote(self._cloud_name, safe='')}/resources/{resource_type}/"
            f"{self._DELIVERY_TYPE}/{quote(public_id, safe='')}"
        )
        payload = await self._request_json("GET", url)
        duration = self._optional_number(payload, "duration")
        sha256 = payload.get("sha256")
        if sha256 is not None and (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in sha256)
        ):
            raise MediaProviderUnavailableError()
        return ProviderAssetMetadata(
            public_id=self._required_str(payload, "public_id"),
            version=self._required_int(payload, "version"),
            resource_type=self._required_str(payload, "resource_type"),
            delivery_type=self._required_str(payload, "type"),
            file_format=self._required_str(payload, "format"),
            bytes=self._required_int(payload, "bytes"),
            width=self._optional_int(payload, "width"),
            height=self._optional_int(payload, "height"),
            duration_ms=round(duration * 1_000) if duration is not None else None,
            sha256=sha256.lower() if isinstance(sha256, str) else None,
        )

    def create_signed_delivery_url(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        expires_at: int,
    ) -> str:
        # https://cloudinary.com/documentation/control_access_to_media
        timestamp = int(self._clock())
        parameters = {
            "expires_at": str(expires_at),
            "format": file_format,
            "public_id": public_id,
            "timestamp": str(timestamp),
            "type": self._DELIVERY_TYPE,
        }
        query = {
            **parameters,
            "api_key": self._api_key,
            "signature": self.sign_parameters(parameters),
        }
        return (
            f"https://api.cloudinary.com/v1_1/"
            f"{quote(self._cloud_name, safe='')}/{resource_type}/download?"
            f"{urlencode(query)}"
        )

    async def download_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes:
        content = await self._download_single_asset(
            public_id=public_id,
            resource_type=resource_type,
            file_format=file_format,
            max_bytes=max_bytes,
        )
        parts = self._encrypted_manifest_parts(
            content,
            public_id=public_id,
            max_bytes=max_bytes,
        )
        if parts is None:
            return content
        assembled = bytearray()
        for part_public_id, part_bytes, part_sha256 in parts:
            part = await self._download_single_asset(
                public_id=part_public_id,
                resource_type="raw",
                file_format="bin",
                max_bytes=part_bytes,
            )
            if (
                len(part) != part_bytes
                or hashlib.sha256(part).hexdigest() != part_sha256
            ):
                raise MediaProviderUnavailableError()
            assembled.extend(part)
        if len(assembled) > max_bytes:
            raise MediaContentTooLargeError()
        return bytes(assembled)

    async def _download_single_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes:
        url = self.create_signed_delivery_url(
            public_id=public_id,
            resource_type=resource_type,
            file_format=file_format,
            expires_at=int(self._clock()) + 300,
        )
        content = bytearray()
        try:
            async with self._client.stream("GET", url) as response:
                response.raise_for_status()
                declared_length = response.headers.get("content-length")
                if declared_length is not None and int(declared_length) > max_bytes:
                    raise MediaContentTooLargeError()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise MediaContentTooLargeError()
        except MediaContentTooLargeError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise MediaProviderUnavailableError() from exc
        return bytes(content)

    async def upload_encrypted_asset(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredEncryptedAsset:
        if len(content) <= _ENCRYPTED_PART_BYTES:
            return await self._upload_raw_asset(
                public_id=public_id,
                content=content,
                reported_bytes=len(content),
            )
        parts: list[dict[str, str | int]] = []
        uploaded_public_ids: list[str] = []
        try:
            offsets = range(0, len(content), _ENCRYPTED_PART_BYTES)
            for index, offset in enumerate(offsets):
                part = content[offset : offset + _ENCRYPTED_PART_BYTES]
                part_public_id = f"{public_id}.part-{index:05d}"
                await self._upload_raw_asset(
                    public_id=part_public_id,
                    content=part,
                    reported_bytes=len(part),
                )
                uploaded_public_ids.append(part_public_id)
                parts.append(
                    {
                        "bytes": len(part),
                        "public_id": part_public_id,
                        "sha256": hashlib.sha256(part).hexdigest(),
                    }
                )
            manifest = _ENCRYPTED_MANIFEST_PREFIX + json.dumps(
                {"bytes": len(content), "parts": parts, "version": 1},
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
            stored = await self._upload_raw_asset(
                public_id=public_id,
                content=manifest,
                reported_bytes=len(content),
            )
        except MediaProviderUnavailableError:
            for uploaded_public_id in reversed(uploaded_public_ids):
                try:
                    await self._delete_single_asset(
                        public_id=uploaded_public_id,
                        resource_type="raw",
                    )
                except MediaProviderUnavailableError:
                    pass
            raise
        return stored

    async def _upload_raw_asset(
        self,
        *,
        public_id: str,
        content: bytes,
        reported_bytes: int,
    ) -> StoredEncryptedAsset:
        timestamp = int(self._clock())
        parameters = {
            "overwrite": "true",
            "public_id": public_id,
            "timestamp": str(timestamp),
            "type": self._DELIVERY_TYPE,
        }
        form = {
            **parameters,
            "api_key": self._api_key,
            "signature": self.sign_parameters(parameters),
        }
        url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{quote(self._cloud_name, safe='')}/raw/upload"
        )
        payload = await self._request_json(
            "POST",
            url,
            data=form,
            # Raw uploads inherit the multipart filename extension in public_id.
            # Keep it extensionless so Cloudinary preserves our signed public_id.
            files={"file": ("document", content, "application/octet-stream")},
        )
        if (
            self._required_str(payload, "public_id") != public_id
            or self._required_str(payload, "resource_type") != "raw"
            or self._required_str(payload, "type") != self._DELIVERY_TYPE
            or self._required_int(payload, "bytes") != len(content)
        ):
            raise MediaProviderUnavailableError()
        return StoredEncryptedAsset(
            public_id=public_id,
            version=self._required_int(payload, "version"),
            bytes=reported_bytes,
        )

    @staticmethod
    def _encrypted_manifest_parts(
        content: bytes,
        *,
        public_id: str,
        max_bytes: int | None,
    ) -> list[tuple[str, int, str]] | None:
        if not content.startswith(_ENCRYPTED_MANIFEST_PREFIX):
            return None
        try:
            manifest = json.loads(content[len(_ENCRYPTED_MANIFEST_PREFIX) :])
            if (
                not isinstance(manifest, dict)
                or manifest.get("version") != 1
                or not isinstance(manifest.get("bytes"), int)
                or not 0 < manifest["bytes"] <= _ENCRYPTED_ASSET_MAX_BYTES
                or (max_bytes is not None and manifest["bytes"] != max_bytes)
                or not isinstance(manifest.get("parts"), list)
            ):
                raise ValueError
            parts: list[tuple[str, int, str]] = []
            total_bytes = 0
            for index, item in enumerate(manifest["parts"]):
                expected_public_id = f"{public_id}.part-{index:05d}"
                if (
                    not isinstance(item, dict)
                    or item.get("public_id") != expected_public_id
                    or not isinstance(item.get("bytes"), int)
                    or not 0 < item["bytes"] <= _ENCRYPTED_PART_BYTES
                    or not isinstance(item.get("sha256"), str)
                    or len(item["sha256"]) != 64
                ):
                    raise ValueError
                total_bytes += item["bytes"]
                parts.append((expected_public_id, item["bytes"], item["sha256"]))
            if not parts or total_bytes != manifest["bytes"]:
                raise ValueError
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise MediaProviderUnavailableError() from exc
        return parts

    async def delete_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> None:
        if resource_type == "raw":
            try:
                manifest = await self._download_single_asset(
                    public_id=public_id,
                    resource_type="raw",
                    file_format="bin",
                    max_bytes=_ENCRYPTED_MANIFEST_MAX_BYTES,
                )
            except MediaContentTooLargeError:
                manifest = b""
            parts = self._encrypted_manifest_parts(
                manifest,
                public_id=public_id,
                max_bytes=None,
            )
            if parts is not None:
                for part_public_id, _, _ in parts:
                    await self._delete_single_asset(
                        public_id=part_public_id,
                        resource_type="raw",
                    )
        await self._delete_single_asset(
            public_id=public_id,
            resource_type=resource_type,
        )

    async def _delete_single_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> None:
        parameters = {
            "invalidate": "true",
            "public_id": public_id,
            "timestamp": str(int(self._clock())),
            "type": self._DELIVERY_TYPE,
        }
        form = {
            **parameters,
            "api_key": self._api_key,
            "signature": self.sign_parameters(parameters),
        }
        url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{quote(self._cloud_name, safe='')}/{resource_type}/destroy"
        )
        payload = await self._request_json("POST", url, data=form)
        if payload.get("result") not in ("ok", "not found"):
            raise MediaProviderUnavailableError()

    async def create_public_derivative(
        self,
        *,
        source_public_id: str,
        source_resource_type: str,
        source_format: str,
        derivative_public_id: str,
        transformation: str,
    ) -> PublicDerivativeMetadata:
        # The transformed copy receives a distinct public identifier. This prevents
        # an authenticated source identifier from appearing in public HTML.
        timestamp = int(self._clock())
        source_url = self.create_signed_delivery_url(
            public_id=source_public_id,
            resource_type=source_resource_type,
            file_format=source_format,
            expires_at=timestamp + 600,
        )
        parameters = {
            "invalidate": "true",
            "overwrite": "true",
            "public_id": derivative_public_id,
            "timestamp": str(timestamp),
            "transformation": transformation,
            "type": "upload",
        }
        form = {
            "file": source_url,
            **parameters,
            "api_key": self._api_key,
            "signature": self.sign_parameters(parameters),
        }
        target_resource_type = (
            "image" if source_resource_type in {"image", "raw"} else "video"
        )
        url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{quote(self._cloud_name, safe='')}/{target_resource_type}/upload"
        )
        payload = await self._request_json("POST", url, data=form)
        public_id = self._required_str(payload, "public_id")
        secure_url = self._required_str(payload, "secure_url")
        resource_type = self._required_str(payload, "resource_type")
        file_format = self._required_str(payload, "format")
        if (
            public_id != derivative_public_id
            or not secure_url.startswith(
                f"https://res.cloudinary.com/{quote(self._cloud_name, safe='')}/"
            )
            or source_public_id in secure_url
            or quote(source_public_id, safe="") in secure_url
        ):
            raise MediaProviderUnavailableError()
        mime_prefix = "image" if resource_type == "image" else "video"
        duration = self._optional_number(payload, "duration")
        return PublicDerivativeMetadata(
            public_id=public_id,
            url=secure_url,
            mime_type=f"{mime_prefix}/{file_format}",
            bytes=self._required_int(payload, "bytes"),
            width=self._optional_int(payload, "width"),
            height=self._optional_int(payload, "height"),
            duration_ms=round(duration * 1_000) if duration is not None else None,
        )

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        data: Mapping[str, str] | None = None,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
    ) -> dict[str, object]:
        try:
            response = await self._client.request(
                method,
                url,
                data=data,
                files=files,
                auth=(self._api_key, self._api_secret),
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MediaProviderUnavailableError() from exc
        if not isinstance(payload, dict):
            raise MediaProviderUnavailableError()
        return payload

    @staticmethod
    def _required_str(payload: Mapping[str, object], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise MediaProviderUnavailableError()
        return value

    @staticmethod
    def _required_int(payload: Mapping[str, object], field: str) -> int:
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise MediaProviderUnavailableError()
        return value

    @classmethod
    def _optional_int(
        cls,
        payload: Mapping[str, object],
        field: str,
    ) -> int | None:
        if payload.get(field) is None:
            return None
        return cls._required_int(payload, field)

    @staticmethod
    def _optional_number(
        payload: Mapping[str, object],
        field: str,
    ) -> float | None:
        value = payload.get(field)
        if value is None:
            return None
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise MediaProviderUnavailableError()
        return float(value)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
