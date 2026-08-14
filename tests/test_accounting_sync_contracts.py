"""Synthetic checks for provider-neutral accounting pagination."""

from datetime import datetime, timezone

from reserved.providers.accounting.contracts import SyncPage
from reserved.providers.accounting.sync_contracts import SyncContractError, collect_pages


def record(identity):
    return {"external_id": identity}


def identity_of(item):
    return item.get("external_id")


def test_collects_every_page_in_order_and_reports_final_watermark():
    pages = {
        None: SyncPage((record("a"), record("b")), "page-2", datetime(2026, 8, 1, tzinfo=timezone.utc)),
        "page-2": SyncPage((record("c"),), None, datetime(2026, 8, 2, tzinfo=timezone.utc)),
    }
    requested = []
    result = collect_pages(
        fetch_page=lambda cursor: requested.append(cursor) or pages[cursor],
        identity_of=identity_of,
    )
    assert requested == [None, "page-2"]
    assert [item["external_id"] for item in result.records] == ["a", "b", "c"]
    assert result.page_count == 2
    assert result.source_watermark == datetime(2026, 8, 2, tzinfo=timezone.utc)


def assert_sync_fails(pages, message, *, max_pages=1000):
    try:
        collect_pages(fetch_page=lambda cursor: pages[cursor], identity_of=identity_of, max_pages=max_pages)
    except SyncContractError as exc:
        assert message in str(exc)
    else:
        raise AssertionError("Unsafe sync should have failed")


def test_repeated_cursor_fails_instead_of_looping():
    assert_sync_fails(
        {None: SyncPage((record("a"),), "repeat"), "repeat": SyncPage((record("b"),), "repeat")},
        "cursor repeated",
    )


def test_duplicate_external_identity_across_pages_fails_closed():
    assert_sync_fails(
        {None: SyncPage((record("a"),), "next"), "next": SyncPage((record("a"),), None)},
        "Duplicate provider record identity",
    )


def test_missing_and_unhashable_external_identities_are_rejected():
    for bad in (None, "", ["not", "hashable"]):
        assert_sync_fails({None: SyncPage((record(bad),), None)}, "identity")


def test_backward_source_watermark_is_rejected():
    assert_sync_fails(
        {
            None: SyncPage((record("a"),), "next", datetime(2026, 8, 2, tzinfo=timezone.utc)),
            "next": SyncPage((record("b"),), None, datetime(2026, 8, 1, tzinfo=timezone.utc)),
        },
        "watermark moved backwards",
    )


def test_invalid_cursor_shape_is_rejected():
    for cursor in ("", "   ", 123):
        assert_sync_fails({None: SyncPage((record("a"),), cursor)}, "invalid next cursor")


def test_page_limit_stops_unbounded_provider_pagination():
    pages = {
        None: SyncPage((record("a"),), "two"),
        "two": SyncPage((record("b"),), "three"),
    }
    assert_sync_fails(pages, "exceeded", max_pages=2)


def test_non_sync_page_provider_result_is_rejected():
    try:
        collect_pages(fetch_page=lambda cursor: {"records": []}, identity_of=identity_of)
    except SyncContractError as exc:
        assert "invalid sync page" in str(exc)
    else:
        raise AssertionError("Untyped provider page must be rejected")

