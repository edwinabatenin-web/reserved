"""Adversarial tests for bounded QuickBooks Q-S5B sync evidence."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import ast
import builtins
from pathlib import Path
import socket

import pytest

from reserved.providers.import_evidence import FitnessStatus
from reserved.providers.accounting.contracts import CompletenessState
from reserved.providers.accounting.quickbooks_oauth_contract import RealmBinding
from reserved.providers.accounting.quickbooks_sync_evidence import (
    DeletedInvoiceEvidence,
    QueryEntity,
    QuickBooksSyncEvidenceError,
    validate_invoice_cdc_window,
    validate_query_run,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
BINDING = RealmBinding("user-1", "realm-1", "opaque-reference-1")


def invoice(identity="invoice-1", sync="1", updated="2026-09-01T10:00:00Z"):
    return {
        "Id": identity,
        "SyncToken": sync,
        "CustomerRef": {"value": "customer-1"},
        "TxnDate": "2026-09-01",
        "CurrencyRef": {"value": "GBP"},
        "Line": [{
            "Id": "1", "DetailType": "SalesItemLineDetail",
            "Amount": Decimal("10.00"),
            "SalesItemLineDetail": {"ItemRef": {"value": "item-1"}},
        }],
        "TotalAmt": Decimal("10.00"),
        "Balance": Decimal("10.00"),
        "MetaData": {"LastUpdatedTime": updated},
    }


def payment(identity="payment-1"):
    return {
        "Id": identity,
        "SyncToken": "1",
        "CustomerRef": {"value": "customer-1"},
        "TxnDate": "2026-09-01",
        "CurrencyRef": {"value": "GBP"},
        "TotalAmt": Decimal("10.00"),
        "UnappliedAmt": Decimal("0.00"),
        "Line": [{"Amount": Decimal("10.00"), "LinkedTxn": [{
            "TxnId": "invoice-1", "TxnType": "Invoice",
        }]}],
    }


def page(entity, start, values, request_identity="query-run-001"):
    return {"requestIdentity": request_identity, "startPosition": start,
            "maxResults": len(values), entity.value: values}


def query(responses, *, entity=QueryEntity.INVOICE, page_size=2,
          times=None, source_total=None, binding=BINDING, minor=75,
          request_identity="query-run-001"):
    if times is None:
        times = tuple(NOW + timedelta(seconds=index) for index in range(len(responses)))
    return validate_query_run(
        tuple(responses), entity=entity, request_identity=request_identity,
        requested_page_size=page_size,
        retrieved_at=times, binding=binding, user_id="user-1", realm_id="realm-1",
        credential_reference="opaque-reference-1", minor_version=minor,
        source_total_count=source_total,
    )


def cdc_records(records):
    query_response = [] if records is None else [{"Invoice": records}]
    return {"CDCResponse": [{"QueryResponse": query_response}]}


def cdc(response, *, start=NOW - timedelta(days=1), end=NOW,
        binding=BINDING, minor=75):
    return validate_invoice_cdc_window(
        response, changed_since=start, retrieved_at=end,
        binding=binding, user_id="user-1", realm_id="realm-1",
        credential_reference="opaque-reference-1", minor_version=minor,
    )


def tombstone(identity="invoice-deleted-1", updated="2026-09-01T10:30:00Z"):
    return {"Id": identity, "status": "Deleted",
            "MetaData": {"LastUpdatedTime": updated}}


def test_query_validates_contiguous_pages_and_preserves_provider_order():
    records = [invoice("invoice-1"), invoice("invoice-2")]
    result = query([
        page(QueryEntity.INVOICE, 1, records),
        page(QueryEntity.INVOICE, 3, []),
    ], source_total=2)
    assert [item.entity_id for item in result.observations] == ["invoice-1", "invoice-2"]
    assert [item.start_position for item in result.pages] == [1, 3]
    assert result.resource_completeness.pagination is CompletenessState.UNKNOWN
    assert result.resource_completeness.independent_source_totals is CompletenessState.UNKNOWN
    assert result.canonical_ingestion_fitness is FitnessStatus.UNVERIFIED
    assert result.run_mechanics is CompletenessState.COMPLETE
    assert result.request_identity == "query-run-001"
    assert all(item.request_identity == result.request_identity for item in result.pages)
    assert result.resource_completeness.known_exclusions is CompletenessState.UNKNOWN
    assert "snapshot_completeness" in result.prohibited_uses
    assert "snapshot" not in repr(result).lower()


def test_query_accepts_short_terminal_page_but_never_claims_snapshot_fitness():
    result = query([page(QueryEntity.INVOICE, 1, [invoice()])])
    assert len(result.observations) == 1
    assert result.resource_completeness.independent_source_totals is CompletenessState.UNKNOWN
    assert result.canonical_ingestion_fitness is FitnessStatus.UNVERIFIED


def test_payment_query_uses_exact_qs4_observer():
    result = query([page(QueryEntity.PAYMENT, 1, [payment()])],
                   entity=QueryEntity.PAYMENT)
    assert result.entity is QueryEntity.PAYMENT
    assert result.observations[0].entity_id == "payment-1"


@pytest.mark.parametrize("bad", [True, 75.0, "75", 74, 76])
def test_minor_version_requires_exact_integer_75(bad):
    with pytest.raises(QuickBooksSyncEvidenceError):
        query([page(QueryEntity.INVOICE, 1, [])], minor=bad)


@pytest.mark.parametrize("bad", [True, 1.0, "1", 0, 1001])
def test_requested_page_size_is_strict_and_bounded(bad):
    with pytest.raises(QuickBooksSyncEvidenceError):
        query([page(QueryEntity.INVOICE, 1, [])], page_size=bad)


def test_query_rejects_position_gap_overlap_and_nonterminal_end():
    for responses in (
        [page(QueryEntity.INVOICE, 2, [])],
        [page(QueryEntity.INVOICE, 1, [invoice("a"), invoice("b")])],
        [page(QueryEntity.INVOICE, 1, [invoice("a"), invoice("b")]),
         page(QueryEntity.INVOICE, 2, [])],
    ):
        with pytest.raises(QuickBooksSyncEvidenceError):
            query(responses)


def test_query_rejects_wrong_entity_shape_count_and_post_terminal_page():
    wrong_entity = {"requestIdentity": "query-run-001", "startPosition": 1,
                    "maxResults": 0, "Payment": []}
    wrong_count = {"requestIdentity": "query-run-001", "startPosition": 1,
                   "maxResults": 1, "Invoice": []}
    for responses in ([wrong_entity], [wrong_count], [page(QueryEntity.INVOICE, 1, []),
                                                      page(QueryEntity.INVOICE, 1, [])]):
        with pytest.raises(QuickBooksSyncEvidenceError):
            query(responses)


def test_query_rejects_duplicate_identity_even_with_different_revision():
    with pytest.raises(QuickBooksSyncEvidenceError, match="duplicate"):
        query([page(QueryEntity.INVOICE, 1, [
            invoice("same", "1"), invoice("same", "2"),
        ])])


def test_query_rejects_count_contradiction_and_backwards_retrieval_time():
    responses = [page(QueryEntity.INVOICE, 1, [invoice()])]
    with pytest.raises(QuickBooksSyncEvidenceError, match="contradicts"):
        query(responses, source_total=2)
    pages = [page(QueryEntity.INVOICE, 1, [invoice("a"), invoice("b")]),
             page(QueryEntity.INVOICE, 3, [])]
    with pytest.raises(QuickBooksSyncEvidenceError, match="backwards"):
        query(pages, times=(NOW, NOW - timedelta(seconds=1)))


def test_query_rejects_binding_substitution_and_forged_entity_enum():
    with pytest.raises(QuickBooksSyncEvidenceError):
        query([page(QueryEntity.INVOICE, 1, [])],
              binding=RealmBinding("other", "realm-1", "opaque-reference-1"))
    with pytest.raises(QuickBooksSyncEvidenceError):
        validate_query_run(
            (page(QueryEntity.INVOICE, 1, []),), entity="Invoice",
            request_identity="query-run-001",
            requested_page_size=2, retrieved_at=(NOW,), binding=BINDING,
            user_id="user-1", realm_id="realm-1",
            credential_reference="opaque-reference-1",
        )


def test_query_rejects_custom_containers_cycles_controls_and_does_not_echo_values():
    class Hostile(dict):
        pass

    secret = "source-secret-value"
    hostile_control = page(QueryEntity.INVOICE, 1, [invoice()])
    hostile_control["Invoice"][0]["Memo"] = secret + "\x00"
    with pytest.raises(QuickBooksSyncEvidenceError) as caught:
        query((hostile_control,))
    assert secret not in str(caught.value)
    with pytest.raises(QuickBooksSyncEvidenceError):
        query((Hostile(page(QueryEntity.INVOICE, 1, [])),))
    cycle = page(QueryEntity.INVOICE, 1, [])
    cycle["extra"] = cycle
    with pytest.raises(QuickBooksSyncEvidenceError):
        query((cycle,))


def test_query_rejects_page_splicing_and_unsafe_request_identity():
    pages = [
        page(QueryEntity.INVOICE, 1, [invoice("a"), invoice("b")]),
        page(QueryEntity.INVOICE, 3, [], request_identity="different-run"),
    ]
    with pytest.raises(QuickBooksSyncEvidenceError, match="request identity"):
        query(pages)
    for bad in ("", "has space", "https://query", "a" * 161):
        with pytest.raises(QuickBooksSyncEvidenceError):
            query([page(QueryEntity.INVOICE, 1, [])], request_identity=bad)


def test_query_whole_run_preflight_rejects_aliased_containers():
    shared_line = invoice()["Line"][0]
    first = invoice("a"); second = invoice("b")
    first["Line"] = [shared_line]; second["Line"] = [shared_line]
    with pytest.raises(QuickBooksSyncEvidenceError, match="alias"):
        query([page(QueryEntity.INVOICE, 1, [first, second])])


def test_query_whole_run_record_and_byte_bounds_apply_before_observation():
    over_records = []
    for page_index in range(101):
        values = [{} for _ in range(1000)]
        over_records.append(page(
            QueryEntity.INVOICE, page_index * 1000 + 1, values))
    with pytest.raises(QuickBooksSyncEvidenceError, match="record boundary"):
        query(over_records, page_size=1000,
              times=tuple(NOW for _ in over_records))

    large_text = "x" * 4096
    values = [{"Memo": large_text, "sequence": index} for index in range(1000)]
    second_values = [
        {"Memo": large_text, "sequence": index + 1000} for index in range(1000)
    ]
    byte_pages = [
        page(QueryEntity.INVOICE, 1, values),
        page(QueryEntity.INVOICE, 1001, second_values),
        page(QueryEntity.INVOICE, 2001, []),
    ]
    with pytest.raises(QuickBooksSyncEvidenceError, match="byte boundary"):
        query(byte_pages, page_size=1000,
              times=(NOW, NOW, NOW))


def test_cdc_preserves_live_tombstone_event_order_and_stays_unverified():
    result = cdc(cdc_records([invoice(), tombstone()]))
    assert [type(item) for item in result.events] == [
        type(result.live_observations[0]), DeletedInvoiceEvidence,
    ]
    assert len(result.live_observations) == len(result.tombstones) == 1
    assert result.tombstones[0].entity_id == "invoice-deleted-1"
    assert result.resource_completeness.deletion_tombstone_detection is CompletenessState.UNKNOWN
    assert result.resource_completeness.known_exclusions is CompletenessState.UNKNOWN
    assert result.canonical_ingestion_fitness is FitnessStatus.UNVERIFIED
    assert not result.saturated
    assert "continuous" not in repr(result).lower()


def test_empty_cdc_response_is_valid_bounded_evidence_not_historical_completeness():
    result = cdc(cdc_records(None))
    assert result.events == ()
    assert result.canonical_ingestion_fitness is FitnessStatus.UNVERIFIED
    assert "historical completeness are not established" in result.limitations[-1]


def test_cdc_exact_cap_is_saturated_and_over_cap_fails():
    at_cap = [tombstone(f"deleted-{index}") for index in range(1000)]
    result = cdc(cdc_records(at_cap))
    assert result.saturated
    assert result.resource_completeness.freshness_limitations is CompletenessState.INCOMPLETE
    with pytest.raises(QuickBooksSyncEvidenceError, match="object cap"):
        cdc(cdc_records(at_cap + [tombstone("one-too-many")]))


def test_cdc_window_is_strict_aware_nonfuture_and_at_most_thirty_days():
    response = cdc_records(None)
    for start, end in (
        (NOW, NOW - timedelta(seconds=1)),
        (NOW - timedelta(days=30, seconds=1), NOW),
        (datetime(2026, 9, 1), NOW),
    ):
        with pytest.raises(QuickBooksSyncEvidenceError):
            cdc(response, start=start, end=end)
    assert cdc(response, start=NOW - timedelta(days=30), end=NOW).events == ()


def test_cdc_rejects_duplicate_or_live_tombstone_conflict():
    with pytest.raises(QuickBooksSyncEvidenceError, match="conflicting"):
        cdc(cdc_records([invoice("same"), tombstone("same")]))


@pytest.mark.parametrize("mutate", [
    lambda value: value["CDCResponse"].append({"QueryResponse": []}),
    lambda value: value["CDCResponse"][0]["QueryResponse"].append({"Payment": []}),
    lambda value: value["CDCResponse"][0]["QueryResponse"][0].__setitem__("Payment", []),
    lambda value: value["CDCResponse"][0]["QueryResponse"][0]["Invoice"][0].__setitem__("status", "Removed"),
    lambda value: value["CDCResponse"][0]["QueryResponse"][0]["Invoice"][1].__setitem__("extra", True),
])
def test_cdc_rejects_unsupported_groups_statuses_and_tombstone_shape(mutate):
    value = cdc_records([invoice(), tombstone()])
    mutate(value)
    with pytest.raises(QuickBooksSyncEvidenceError):
        cdc(value)


def test_cdc_rejects_entity_metadata_outside_window_and_invalid_timestamp():
    for updated in ("2026-08-30T10:00:00Z", "2026-09-02T10:00:00Z", "not-a-time"):
        with pytest.raises(QuickBooksSyncEvidenceError):
            cdc(cdc_records([tombstone(updated=updated)]))


def test_cdc_accepts_documented_create_time_but_rejects_unknown_metadata():
    value = cdc_records([invoice()])
    metadata = value["CDCResponse"][0]["QueryResponse"][0]["Invoice"][0]["MetaData"]
    metadata["CreateTime"] = "2026-08-31T10:00:00Z"
    assert len(cdc(value).live_observations) == 1
    metadata["unsupported"] = "synthetic"
    with pytest.raises(QuickBooksSyncEvidenceError):
        cdc(value)


def test_cdc_rejects_create_time_after_last_update():
    value = cdc_records([invoice()])
    value["CDCResponse"][0]["QueryResponse"][0]["Invoice"][0]["MetaData"][
        "CreateTime"
    ] = "2026-09-01T11:00:00Z"
    with pytest.raises(QuickBooksSyncEvidenceError, match="inconsistent"):
        cdc(value)


def test_cdc_rejects_payment_group_and_binding_substitution():
    with pytest.raises(QuickBooksSyncEvidenceError):
        cdc({"CDCResponse": [{"QueryResponse": [{"Payment": [payment()]}]}]})
    with pytest.raises(QuickBooksSyncEvidenceError):
        cdc(cdc_records(None), binding=RealmBinding("user-1", "other", "opaque-reference-1"))


def test_outputs_are_frozen_and_redacted():
    result = query([page(QueryEntity.INVOICE, 1, [])])
    with pytest.raises(FrozenInstanceError):
        result.requested_page_size = 999
    assert "opaque-reference-1" not in repr(result)


def test_module_has_no_network_file_configuration_or_activation_capability(monkeypatch):
    module_path = Path(__file__).parents[1] / "reserved/providers/accounting/quickbooks_sync_evidence.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint({"requests", "httpx", "urllib", "socket", "ssl", "os",
                               "subprocess", "logging", "sqlite3", "pathlib"})
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(AssertionError("file")))
    assert query([page(QueryEntity.INVOICE, 1, [])]).canonical_ingestion_fitness is FitnessStatus.UNVERIFIED


def test_inputs_are_not_mutated():
    response = cdc_records([invoice(), tombstone()])
    original = deepcopy(response)
    cdc(response)
    assert response == original
