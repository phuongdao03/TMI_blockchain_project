import hashlib
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

import httpx

from app.modules.media.gateway import CloudinaryMediaGateway


@dataclass(frozen=True, slots=True)
class StoredCertificate:
    public_id: str
    version: int
    bytes: int
    sha256: str


class CertificateStorage(Protocol):
    async def upload_pdf(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredCertificate: ...


class CloudinaryCertificateStorage:
    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not cloud_name or not api_key or not api_secret:
            raise RuntimeError("Cloudinary credentials are not configured.")
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._signer = CloudinaryMediaGateway(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None

    async def upload_pdf(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredCertificate:
        import time

        timestamp = str(int(time.time()))
        parameters = {
            "access_mode": "authenticated",
            "overwrite": "false",
            "public_id": public_id,
            "timestamp": timestamp,
            "type": "authenticated",
        }
        signature = self._signer.sign_parameters(parameters)
        url = (
            f"https://api.cloudinary.com/v1_1/"
            f"{quote(self._cloud_name, safe='')}/raw/upload"
        )
        response = await self._client.post(
            url,
            data={
                **parameters,
                "api_key": self._api_key,
                "signature": signature,
            },
            files={"file": ("certificate.pdf", content, "application/pdf")},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(
            payload.get("version"), int
        ):
            raise RuntimeError("Cloudinary certificate response is invalid.")
        return StoredCertificate(
            public_id=public_id,
            version=int(payload["version"]),
            bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    async def close(self) -> None:
        await self._signer.close()
        if self._owns_client:
            await self._client.aclose()
