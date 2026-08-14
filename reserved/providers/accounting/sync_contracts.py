"""Endpoint-free contracts for safe, complete paginated accounting imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Hashable

from .contracts import SyncPage


class SyncContractError(ValueError):
    """Provider sync failed a safety/completeness invariant."""


@dataclass(frozen=True)
class CompletedSync:
    records: tuple[object, ...]
    page_count: int
    source_watermark: datetime | None


PageFetcher = Callable[[str | None], SyncPage]
IdentityExtractor = Callable[[object], Hashable]


def collect_pages(
    *,
    fetch_page: PageFetcher,
    identity_of: IdentityExtractor,
    max_pages: int = 1000,
) -> CompletedSync:
    """Collect a cursor-based sync while failing closed on ambiguity.

    Provider adapters translate their documented pagination model into
    ``SyncPage``. This collector deliberately knows no provider URLs, page
    sizes or cursor syntax. Duplicate identities are rejected rather than
    silently overwritten because they may indicate unstable pagination or an
    incorrect provider mapping.
    """
    if max_pages <= 0:
        raise SyncContractError("max_pages must be positive")

    cursor: str | None = None
    requested_cursors: set[str] = set()
    identities: set[Hashable] = set()
    records: list[object] = []
    watermark: datetime | None = None

    for page_number in range(1, max_pages + 1):
        page = fetch_page(cursor)
        if not isinstance(page, SyncPage):
            raise SyncContractError("Provider returned an invalid sync page")
        if page.source_watermark is not None:
            if watermark is not None and page.source_watermark < watermark:
                raise SyncContractError("Source watermark moved backwards between pages")
            watermark = page.source_watermark

        for record in page.records:
            identity = identity_of(record)
            if identity is None or identity == "":
                raise SyncContractError("Provider record has no stable external identity")
            try:
                duplicate = identity in identities
            except TypeError as exc:
                raise SyncContractError("Provider record identity must be hashable") from exc
            if duplicate:
                raise SyncContractError("Duplicate provider record identity across sync pages")
            identities.add(identity)
            records.append(record)

        next_cursor = page.next_cursor
        if next_cursor is None:
            return CompletedSync(tuple(records), page_number, watermark)
        if not isinstance(next_cursor, str) or not next_cursor.strip():
            raise SyncContractError("Provider returned an invalid next cursor")
        if next_cursor in requested_cursors or next_cursor == cursor:
            raise SyncContractError("Provider pagination cursor repeated")
        requested_cursors.add(next_cursor)
        cursor = next_cursor

    raise SyncContractError("Provider pagination exceeded the configured page limit")

