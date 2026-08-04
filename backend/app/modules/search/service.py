import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.modules.blockchain.models import CertificateStatus
from app.modules.search.errors import (
    SearchFilterInvalidError,
    SearchIndexUnavailableError,
    SearchQueryInvalidError,
    SearchSortInvalidError,
)
from app.modules.search.normalization import (
    NormalizedSearchQuery,
    SearchQueryNormalizer,
)
from app.modules.search.types import (
    AutocompleteSuggestion,
    SearchFacets,
    SearchFilters,
    SearchPage,
    SearchResult,
    SearchSort,
    SearchWorkProjection,
    TagMatchMode,
)


class SearchRepositoryPort(Protocol):
    def search(
        self,
        query: NormalizedSearchQuery,
        *,
        filters: SearchFilters,
        sort: SearchSort,
        cursor: str | None,
        page_size: int,
    ) -> Awaitable[SearchPage]: ...

    def facets(
        self,
        query: NormalizedSearchQuery,
        *,
        filters: SearchFilters,
    ) -> Awaitable[SearchFacets]: ...

    def autocomplete(
        self,
        query: NormalizedSearchQuery,
        *,
        limit: int,
    ) -> Awaitable[tuple[AutocompleteSuggestion, ...]]: ...


class AutocompleteCachePort(Protocol):
    def get(
        self,
        normalized_query: str,
    ) -> Awaitable[tuple[AutocompleteSuggestion, ...] | None]: ...

    def set(
        self,
        normalized_query: str,
        suggestions: tuple[AutocompleteSuggestion, ...],
    ) -> Awaitable[None]: ...


class SearchEventRecorderPort(Protocol):
    def record_search(
        self,
        *,
        request_id: str,
        normalized_query: str,
        category_slug: str | None,
        result_count: int,
        duration_ms: int,
    ) -> Awaitable[bool]: ...


class SearchResultCachePort(Protocol):
    def get(self, key: str) -> Awaitable[str | None]: ...
    def set(self, key: str, value: str) -> Awaitable[None]: ...
    def reserve(self, key: str, *, seconds: int = 3) -> Awaitable[bool]: ...
    def release(self, key: str) -> Awaitable[None]: ...


class PublicSearchService:
    def __init__(
        self,
        repository: SearchRepositoryPort,
        *,
        normalizer: SearchQueryNormalizer | None = None,
        autocomplete_cache: AutocompleteCachePort | None = None,
        event_recorder: SearchEventRecorderPort | None = None,
        result_cache: SearchResultCachePort | None = None,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._repository = repository
        self._normalizer = normalizer or SearchQueryNormalizer()
        self._autocomplete_cache = autocomplete_cache
        self._event_recorder = event_recorder
        self._result_cache = result_cache
        self._clock = clock

    async def search(
        self,
        *,
        query: str | None,
        category: str | None = None,
        tags: str | None = None,
        tags_mode: str = "any",
        organization: str | None = None,
        published_from: str | None = None,
        published_to: str | None = None,
        has_blockchain_proof: str | None = None,
        certificate_status: str | None = None,
        sort: str | None = None,
        cursor: str | None = None,
        page_size: int = 20,
        request_id: str | None = None,
    ) -> SearchResult:
        normalized = self._normalizer.normalize(query)
        resolved_sort = self._parse_sort(sort, is_empty=normalized.is_empty)
        filters = self._parse_filters(
            category=category,
            tags=tags,
            tags_mode=tags_mode,
            organization=organization,
            published_from=published_from,
            published_to=published_to,
            has_blockchain_proof=has_blockchain_proof,
            certificate_status=certificate_status,
        )
        if not 1 <= page_size <= 100:
            raise SearchQueryInvalidError("invalid_page_size", limit=100)
        started_at = self._clock()
        cache_key = self._result_cache_key(
            normalized=normalized,
            filters=filters,
            sort=resolved_sort,
            cursor=cursor,
            page_size=page_size,
        )
        cache_owner = False
        try:
            page = await self._get_cached_page(cache_key)
            if page is None and self._result_cache is not None:
                cache_owner = await self._result_cache.reserve(cache_key)
                if not cache_owner:
                    for _ in range(3):
                        await asyncio.sleep(0.025)
                        page = await self._get_cached_page(cache_key)
                        if page is not None:
                            break
            if page is None:
                page = await self._repository.search(
                    normalized,
                    filters=filters,
                    sort=resolved_sort,
                    cursor=cursor,
                    page_size=page_size,
                )
                if self._result_cache is not None and cache_owner:
                    await self._result_cache.set(cache_key, self._encode_page(page))
        except SQLAlchemyError as error:
            raise SearchIndexUnavailableError() from error
        finally:
            if self._result_cache is not None and cache_owner:
                await self._result_cache.release(cache_key)
        duration_ms = max(0, round((self._clock() - started_at) * 1_000))
        if self._event_recorder is not None and request_id is not None:
            await self._event_recorder.record_search(
                request_id=request_id,
                normalized_query=normalized.normalized,
                category_slug=filters.category_slug,
                result_count=len(page.items),
                duration_ms=duration_ms,
            )
        return SearchResult(page=page, duration_ms=duration_ms)

    async def _get_cached_page(self, key: str) -> SearchPage | None:
        if self._result_cache is None:
            return None
        payload = await self._result_cache.get(key)
        if payload is None:
            return None
        try:
            data = json.loads(payload)
            return SearchPage(
                items=tuple(
                    SearchWorkProjection(
                        id=UUID(item["id"]),
                        slug=item["slug"],
                        title=item["title"],
                        short_description=item["short_description"],
                        author_display_name=item["author_display_name"],
                        category_name=item["category_name"],
                        category_slug=item["category_slug"],
                        certificate_number=item["certificate_number"],
                        certificate_status=(
                            CertificateStatus(item["certificate_status"])
                            if item["certificate_status"]
                            else None
                        ),
                        published_at=datetime.fromisoformat(item["published_at"]),
                    )
                    for item in data["items"]
                ),
                next_cursor=data["next_cursor"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _encode_page(page: SearchPage) -> str:
        return json.dumps(
            {
                "items": [
                    {
                        "id": str(item.id),
                        "slug": item.slug,
                        "title": item.title,
                        "short_description": item.short_description,
                        "author_display_name": item.author_display_name,
                        "category_name": item.category_name,
                        "category_slug": item.category_slug,
                        "certificate_number": item.certificate_number,
                        "certificate_status": (
                            item.certificate_status.value
                            if item.certificate_status
                            else None
                        ),
                        "published_at": item.published_at.isoformat(),
                    }
                    for item in page.items
                ],
                "next_cursor": page.next_cursor,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _result_cache_key(
        *,
        normalized: NormalizedSearchQuery,
        filters: SearchFilters,
        sort: SearchSort,
        cursor: str | None,
        page_size: int,
    ) -> str:
        canonical = json.dumps(
            {
                "scope": "published-public",
                "query": normalized.unaccented,
                "filters": asdict(filters),
                "sort": sort.value,
                "cursor": cursor,
                "page_size": page_size,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return f"result:{hashlib.sha256(canonical.encode()).hexdigest()}"

    async def facets(
        self,
        *,
        query: str | None,
        category: str | None = None,
        tags: str | None = None,
        tags_mode: str = "any",
        organization: str | None = None,
        published_from: str | None = None,
        published_to: str | None = None,
        has_blockchain_proof: str | None = None,
        certificate_status: str | None = None,
    ) -> SearchFacets:
        normalized = self._normalizer.normalize(query)
        filters = self._parse_filters(
            category=category,
            tags=tags,
            tags_mode=tags_mode,
            organization=organization,
            published_from=published_from,
            published_to=published_to,
            has_blockchain_proof=has_blockchain_proof,
            certificate_status=certificate_status,
        )
        try:
            return await self._repository.facets(normalized, filters=filters)
        except SQLAlchemyError as error:
            raise SearchIndexUnavailableError() from error

    async def autocomplete(
        self,
        *,
        query: str | None,
        limit: int = 8,
    ) -> tuple[AutocompleteSuggestion, ...]:
        normalized = self._normalizer.normalize(query)
        if normalized.is_empty:
            raise SearchQueryInvalidError("too_short", limit=2)
        if not 1 <= limit <= 12:
            raise SearchQueryInvalidError("invalid_autocomplete_limit", limit=12)
        cache_key = normalized.unaccented
        if self._autocomplete_cache is not None:
            cached = await self._autocomplete_cache.get(cache_key)
            if cached is not None:
                return cached
        try:
            suggestions = await self._repository.autocomplete(
                normalized,
                limit=limit,
            )
        except SQLAlchemyError as error:
            raise SearchIndexUnavailableError() from error
        if self._autocomplete_cache is not None:
            await self._autocomplete_cache.set(cache_key, suggestions)
        return suggestions

    @staticmethod
    def _parse_sort(value: str | None, *, is_empty: bool) -> SearchSort:
        candidate = value or (SearchSort.NEWEST if is_empty else SearchSort.RELEVANCE)
        try:
            resolved = SearchSort(candidate)
        except ValueError as error:
            raise SearchSortInvalidError() from error
        if is_empty and resolved is SearchSort.RELEVANCE:
            raise SearchSortInvalidError("relevance_requires_query")
        return resolved

    @classmethod
    def _parse_filters(
        cls,
        *,
        category: str | None,
        tags: str | None,
        tags_mode: str,
        organization: str | None,
        published_from: str | None,
        published_to: str | None,
        has_blockchain_proof: str | None,
        certificate_status: str | None,
    ) -> SearchFilters:
        category_slug = cls._slug(category, "category")
        organization_code = cls._slug(organization, "organization")
        parsed_tags: list[str] = []
        for value in (tags or "").split(","):
            if not value.strip():
                continue
            parsed = cls._slug(value, "tags")
            if parsed is not None and parsed not in parsed_tags:
                parsed_tags.append(parsed)
        tag_slugs = tuple(parsed_tags)
        if len(tag_slugs) > 10:
            raise SearchFilterInvalidError("too_many_tags")
        try:
            tag_match = TagMatchMode(tags_mode)
        except ValueError as error:
            raise SearchFilterInvalidError("invalid_tags_mode") from error
        start = cls._datetime(published_from, "published_from")
        end = cls._datetime(published_to, "published_to")
        if start is not None and end is not None and start > end:
            raise SearchFilterInvalidError("invalid_publication_range")
        proof = cls._boolean(has_blockchain_proof)
        status = None
        if certificate_status:
            try:
                status = CertificateStatus(certificate_status.upper())
            except ValueError as error:
                raise SearchFilterInvalidError("invalid_certificate_status") from error
        return SearchFilters(
            category_slug=category_slug,
            tag_slugs=tag_slugs,
            tag_match=tag_match,
            organization_code=organization_code,
            published_from=start,
            published_to=end,
            has_blockchain_proof=proof,
            certificate_status=status,
        )

    @staticmethod
    def _slug(value: str | None, name: str) -> str | None:
        if value is None:
            return None
        candidate = value.strip().casefold()
        if not candidate or len(candidate) > 160:
            raise SearchFilterInvalidError(f"invalid_{name}")
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-_")
        if any(character not in allowed for character in candidate):
            raise SearchFilterInvalidError(f"invalid_{name}")
        return candidate

    @staticmethod
    def _datetime(value: str | None, name: str) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise SearchFilterInvalidError(f"invalid_{name}") from error
        if parsed.tzinfo is None:
            raise SearchFilterInvalidError(f"invalid_{name}")
        return parsed.astimezone(UTC)

    @staticmethod
    def _boolean(value: str | None) -> bool | None:
        if value is None:
            return None
        if value == "true":
            return True
        if value == "false":
            return False
        raise SearchFilterInvalidError("invalid_has_blockchain_proof")
