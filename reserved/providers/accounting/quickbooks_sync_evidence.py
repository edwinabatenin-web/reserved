"""Network-inert QuickBooks query and CDC evidence classification.

This module validates already-retrieved provider responses.  It performs no
HTTP, credential access, persistence, canonical adaptation, or provider
activation.  Valid mechanics never imply a stable QuickBooks snapshot,
continuous CDC coverage, or fitness for canonical ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import re
from typing import Any
from unicodedata import category

from reserved.providers.import_evidence import FitnessStatus

from .contracts import CompletenessState, ResourceCompleteness
from .quickbooks_oauth_contract import RealmBinding
from .quickbooks_observation_contract import (
    InvoiceObservation,
    PaymentObservation,
    _digest,
    _bounded_decimal,
    _text,
    observe_invoice,
    observe_payment,
)


MINOR_VERSION = 75
MAX_QUERY_RESULTS = 1000
MAX_CDC_OBJECTS = 1000
MAX_CDC_LOOKBACK = timedelta(days=30)
MAX_QUERY_PAGES = 1000
MAX_QUERY_RECORDS = 100_000
_MAX_AGGREGATE_DEPTH = 24
_MAX_AGGREGATE_NODES = 250_000
_MAX_AGGREGATE_WIDTH = 2_000
_MAX_AGGREGATE_BYTES = 8_000_000
_MAX_STRING = 4096
_MAX_INTEGER = 1_000_000_000_000_000_000
_OPAQUE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,159}\Z")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


class QuickBooksSyncEvidenceError(ValueError):
    """Controlled fail-closed rejection which never includes source values."""


class QueryEntity(str, Enum):
    INVOICE = "Invoice"
    PAYMENT = "Payment"


def _fail(rule: str) -> QuickBooksSyncEvidenceError:
    return QuickBooksSyncEvidenceError(f"QuickBooks Q-S5B sync evidence: {rule}")


def _exact_int(value: Any, field: str, *, minimum: int = 0,
               maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (
        maximum is not None and value > maximum
    ):
        raise _fail(f"{field} is outside the exact integer boundary")
    return value


def _aware(value: Any, field: str) -> datetime:
    if type(value) is not datetime:
        raise _fail(f"{field} must be an aware fixed-offset datetime")
    zone = object.__getattribute__(value, "tzinfo")
    if type(zone) is not timezone:
        raise _fail(f"{field} must be an aware fixed-offset datetime")
    return value.astimezone(timezone.utc)


def _opaque_identity(value: Any) -> str:
    if type(value) is not str or _OPAQUE_ID.fullmatch(value) is None:
        raise _fail("request identity must be an opaque bounded reference")
    return value


def _aggregate_preflight(root: Any, *, query_run: bool) -> None:
    """Validate and bound the complete source graph before field protocols."""
    if query_run:
        if type(root) is not tuple or not root or len(root) > MAX_QUERY_PAGES:
            raise _fail("query run page count is outside the aggregate boundary")
    elif type(root) is not dict:
        raise _fail("CDC response must be an exact object")

    stack = [(root, 0, True)]
    seen: set[int] = set()
    nodes = byte_count = 0
    while stack:
        value, depth, is_root = stack.pop()
        nodes += 1
        if nodes > _MAX_AGGREGATE_NODES:
            raise _fail("response exceeds the aggregate node boundary")
        if depth > _MAX_AGGREGATE_DEPTH:
            raise _fail("response exceeds the aggregate depth boundary")
        value_type = type(value)
        if value is None or value_type is bool:
            byte_count += 1
        elif value_type is str:
            if len(value) > _MAX_STRING or any(
                category(character).startswith("C") for character in value
            ):
                raise _fail("response contains an unsafe string")
            try:
                encoded = value.encode("utf-8")
            except UnicodeEncodeError:
                raise _fail("response contains invalid Unicode") from None
            if len(encoded) > _MAX_STRING * 4:
                raise _fail("response string exceeds the byte boundary")
            byte_count += len(encoded)
        elif value_type is int:
            if abs(value) > _MAX_INTEGER:
                raise _fail("response integer exceeds the numeric boundary")
            byte_count += len(str(value))
        elif value_type is Decimal:
            try:
                _bounded_decimal(value, "response decimal", accept_string=False)
            except Exception:
                raise _fail("response decimal exceeds the numeric boundary") from None
            byte_count += len(str(value))
        elif value_type in (dict, list) or (query_run and is_root and value_type is tuple):
            identity = id(value)
            if identity in seen:
                raise _fail("response contains a container alias or cycle")
            seen.add(identity)
            if len(value) > _MAX_AGGREGATE_WIDTH and not (
                query_run and is_root and value_type is tuple
            ):
                raise _fail("response exceeds the aggregate container boundary")
            if value_type is dict:
                for key, child in value.items():
                    if type(key) is not str:
                        raise _fail("response object keys must be exact strings")
                    if len(key) > _MAX_STRING or any(
                        category(character).startswith("C") for character in key
                    ):
                        raise _fail("response contains an unsafe object key")
                    try:
                        encoded_key = key.encode("utf-8")
                    except UnicodeEncodeError:
                        raise _fail("response contains invalid Unicode") from None
                    byte_count += len(encoded_key)
                    stack.append((child, depth + 1, False))
            else:
                stack.extend((child, depth + 1, False) for child in value)
        else:
            raise _fail("response contains a non-JSON value or container")
        if byte_count > _MAX_AGGREGATE_BYTES:
            raise _fail("response exceeds the aggregate byte boundary")


def _exact_binding(value: Any, *, user_id: Any, realm_id: Any,
                   credential_reference: Any) -> RealmBinding:
    if type(value) is not RealmBinding:
        raise _fail("binding must be the exact Q-S1 RealmBinding")
    try:
        represented = tuple(
            _text(item, field)
            for item, field in zip(
                (user_id, realm_id, credential_reference),
                ("user_id", "realm_id", "credential_reference"),
                strict=True,
            )
        )
        bound = tuple(
            _text(object.__getattribute__(value, field), f"binding.{field}")
            for field in ("user_id", "realm_id", "credential_reference")
        )
    except Exception:
        raise _fail("realm binding identity is invalid") from None
    if any(type(object.__getattribute__(value, field)) is not str
           for field in ("user_id", "realm_id", "credential_reference")):
        raise _fail("realm binding identity is invalid")
    if bound != represented:
        raise _fail("re-presented realm binding identity does not match")
    return value


def _observe(entity: QueryEntity, source: dict[str, Any], *, binding: RealmBinding,
             user_id: str, realm_id: str, credential_reference: str,
             retrieved_at: datetime) -> InvoiceObservation | PaymentObservation:
    observer = observe_invoice if entity is QueryEntity.INVOICE else observe_payment
    try:
        return observer(
            source,
            binding=binding,
            user_id=user_id,
            realm_id=realm_id,
            credential_reference=credential_reference,
            retrieved_at=retrieved_at,
        )
    except Exception:
        raise _fail("entity did not pass the exact Q-S4 observation boundary") from None


@dataclass(frozen=True, repr=False)
class QueryPageEvidence:
    request_identity: str
    start_position: int
    returned_count: int
    retrieved_at: datetime
    observations: tuple[InvoiceObservation | PaymentObservation, ...]

    def __repr__(self) -> str:
        return "QueryPageEvidence([REDACTED])"


@dataclass(frozen=True, repr=False)
class QueryRunEvidence:
    request_identity: str
    entity: QueryEntity
    minor_version: int
    requested_page_size: int
    pages: tuple[QueryPageEvidence, ...]
    observations: tuple[InvoiceObservation | PaymentObservation, ...]
    source_total_count: int | None
    run_mechanics: CompletenessState
    resource_completeness: ResourceCompleteness
    canonical_ingestion_fitness: FitnessStatus
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]

    def __repr__(self) -> str:
        return "QueryRunEvidence([REDACTED])"


_PROHIBITED = (
    "canonical_ingestion", "snapshot_completeness", "provider_activation",
    "http_or_credentials", "tax_or_settlement_decisions",
)


def validate_query_run(
    responses: Any,
    *,
    entity: QueryEntity,
    request_identity: str,
    requested_page_size: int,
    retrieved_at: Any,
    binding: RealmBinding,
    user_id: str,
    realm_id: str,
    credential_reference: str,
    minor_version: int = MINOR_VERSION,
    source_total_count: int | None = None,
) -> QueryRunEvidence:
    """Validate one positional query run without claiming snapshot isolation."""
    if type(entity) is not QueryEntity:
        raise _fail("entity must be an exact QueryEntity")
    request_identity = _opaque_identity(request_identity)
    _exact_int(minor_version, "minor_version", minimum=MINOR_VERSION,
               maximum=MINOR_VERSION)
    page_size = _exact_int(requested_page_size, "requested_page_size", minimum=1,
                           maximum=MAX_QUERY_RESULTS)
    binding = _exact_binding(
        binding, user_id=user_id, realm_id=realm_id,
        credential_reference=credential_reference,
    )
    if type(responses) is not tuple or not responses:
        raise _fail("responses must be a non-empty exact tuple")
    _aggregate_preflight(responses, query_run=True)
    if type(retrieved_at) is not tuple or len(retrieved_at) != len(responses):
        raise _fail("retrieval evidence must match every page")
    if source_total_count is not None:
        source_total_count = _exact_int(source_total_count, "source_total_count")

    expected_start = 1
    prior_time: datetime | None = None
    terminal_seen = False
    seen: set[str] = set()
    page_results: list[QueryPageEvidence] = []
    observations: list[InvoiceObservation | PaymentObservation] = []
    expected_keys = {"requestIdentity", "startPosition", "maxResults", entity.value}
    aggregate_record_count = sum(
        len(response[entity.value])
        for response in responses
        if type(response) is dict and set(response) == expected_keys
        and type(response[entity.value]) is list
    )
    if aggregate_record_count > MAX_QUERY_RECORDS:
        raise _fail("query run exceeds the aggregate record boundary")

    for index, response in enumerate(responses):
        if type(response) is not dict or set(response) != expected_keys:
            raise _fail("query response shape or entity is invalid")
        if response["requestIdentity"] != request_identity:
            raise _fail("query page request identity does not match the run")
        if terminal_seen:
            raise _fail("query supplied pages after terminal evidence")
        start = _exact_int(response["startPosition"], "startPosition", minimum=1)
        if start != expected_start:
            raise _fail("query positions are not contiguous from one")
        records = response[entity.value]
        if type(records) is not list or len(records) > page_size:
            raise _fail("query entity collection exceeds the requested page")
        returned = _exact_int(response["maxResults"], "maxResults", maximum=page_size)
        if returned != len(records):
            raise _fail("query response count does not match its entity collection")
        when = _aware(retrieved_at[index], "retrieved_at")
        if prior_time is not None and when < prior_time:
            raise _fail("query retrieval times moved backwards")
        prior_time = when
        current: list[InvoiceObservation | PaymentObservation] = []
        for record in records:
            if type(record) is not dict:
                raise _fail("query entity must be an exact object")
            observation = _observe(
                entity, record, binding=binding, user_id=user_id,
                realm_id=realm_id, credential_reference=credential_reference,
                retrieved_at=when,
            )
            identity = object.__getattribute__(observation, "entity_id")
            if identity in seen:
                raise _fail("duplicate entity identity across query pages")
            seen.add(identity)
            current.append(observation)
            observations.append(observation)
        terminal_seen = returned < page_size
        expected_start += returned
        page_results.append(QueryPageEvidence(
            request_identity, start, returned, when, tuple(current)))

    if not terminal_seen:
        raise _fail("query terminal-page evidence is missing")
    if source_total_count is not None and source_total_count != len(observations):
        raise _fail("separate source total contradicts fetched query identities")

    completeness = ResourceCompleteness(
        resource=entity.value,
        pagination=CompletenessState.UNKNOWN,
        terminal_page_evidence=CompletenessState.COMPLETE,
        independent_source_totals=CompletenessState.UNKNOWN,
        incremental_watermark_or_revision=CompletenessState.UNKNOWN,
        deletion_tombstone_detection=CompletenessState.NOT_APPLICABLE,
        webhook_coverage=CompletenessState.UNKNOWN,
        polling_or_full_refresh=CompletenessState.UNKNOWN,
        known_exclusions=CompletenessState.UNKNOWN,
        freshness_limitations=CompletenessState.UNKNOWN,
        reason="separate QuickBooks query calls do not prove snapshot isolation",
    )
    return QueryRunEvidence(
        request_identity, entity, minor_version, page_size, tuple(page_results),
        tuple(observations), source_total_count, CompletenessState.COMPLETE,
        completeness, FitnessStatus.UNVERIFIED,
        ("provider ordering is not established", "query snapshot is not established",
         "a matching separate count is not snapshot proof"), _PROHIBITED,
    )


@dataclass(frozen=True, repr=False)
class DeletedInvoiceEvidence:
    entity_id: str
    last_updated_at: datetime
    retrieved_at: datetime
    source_digest: str
    user_id: str
    realm_id: str
    credential_reference: str

    def __repr__(self) -> str:
        return "DeletedInvoiceEvidence([REDACTED])"


@dataclass(frozen=True, repr=False)
class CdcWindowEvidence:
    minor_version: int
    changed_since: datetime
    retrieved_at: datetime
    events: tuple[InvoiceObservation | DeletedInvoiceEvidence, ...]
    live_observations: tuple[InvoiceObservation, ...]
    tombstones: tuple[DeletedInvoiceEvidence, ...]
    saturated: bool
    resource_completeness: ResourceCompleteness
    canonical_ingestion_fitness: FitnessStatus
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]

    def __repr__(self) -> str:
        return "CdcWindowEvidence([REDACTED])"


def _timestamp(value: Any) -> datetime:
    if type(value) is not str or _TIMESTAMP.fullmatch(value) is None:
        raise _fail("CDC metadata timestamp is invalid")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise _fail("CDC metadata timestamp is invalid") from None
    if type(object.__getattribute__(result, "tzinfo")) is not timezone:
        raise _fail("CDC metadata timestamp must use a fixed offset")
    return result.astimezone(timezone.utc)


def _metadata_time(record: dict[str, Any], *, changed_since: datetime,
                   retrieved_at: datetime) -> datetime:
    metadata = record.get("MetaData")
    if (type(metadata) is not dict or "LastUpdatedTime" not in metadata
            or not set(metadata) <= {"CreateTime", "LastUpdatedTime"}):
        raise _fail("CDC entity requires exact LastUpdatedTime metadata")
    updated = _timestamp(metadata["LastUpdatedTime"])
    if "CreateTime" in metadata:
        created = _timestamp(metadata["CreateTime"])
        if created > updated:
            raise _fail("CDC metadata timestamps are inconsistent")
    if updated < changed_since or updated > retrieved_at:
        raise _fail("CDC entity timestamp falls outside the evidenced window")
    return updated


def _safe_tombstone_id(value: Any) -> str:
    if (type(value) is not str or not value.strip() or len(value) > 512
            or any(ord(character) < 32 for character in value)):
        raise _fail("CDC tombstone identity is invalid")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise _fail("CDC tombstone identity is invalid") from None
    return value


def validate_invoice_cdc_window(
    response: Any,
    *,
    changed_since: datetime,
    retrieved_at: datetime,
    binding: RealmBinding,
    user_id: str,
    realm_id: str,
    credential_reference: str,
    minor_version: int = MINOR_VERSION,
) -> CdcWindowEvidence:
    """Validate one bounded Invoice CDC response; never claim a continuous chain."""
    _exact_int(minor_version, "minor_version", minimum=MINOR_VERSION,
               maximum=MINOR_VERSION)
    binding = _exact_binding(
        binding, user_id=user_id, realm_id=realm_id,
        credential_reference=credential_reference,
    )
    start = _aware(changed_since, "changed_since")
    end = _aware(retrieved_at, "retrieved_at")
    if start > end or end - start > MAX_CDC_LOOKBACK:
        raise _fail("CDC window is reversed or exceeds thirty days")
    _aggregate_preflight(response, query_run=False)
    if type(response) is not dict or set(response) != {"CDCResponse"}:
        raise _fail("CDC response root is invalid")
    groups = response["CDCResponse"]
    if type(groups) is not list or len(groups) != 1 or type(groups[0]) is not dict:
        raise _fail("CDC response group is invalid")
    group = groups[0]
    if set(group) != {"QueryResponse"} or type(group["QueryResponse"]) is not list:
        raise _fail("CDC QueryResponse is invalid")
    query_responses = group["QueryResponse"]
    if len(query_responses) > 1:
        raise _fail("only the bounded Invoice CDC entity group is supported")
    records: list[Any] = []
    if query_responses:
        query = query_responses[0]
        if type(query) is not dict or set(query) != {"Invoice"}:
            raise _fail("CDC response contains an unsupported entity group")
        records = query["Invoice"]
        if type(records) is not list:
            raise _fail("CDC Invoice group must be an exact list")
    if len(records) > MAX_CDC_OBJECTS:
        raise _fail("CDC response exceeds the documented object cap")

    seen: set[str] = set()
    events: list[InvoiceObservation | DeletedInvoiceEvidence] = []
    live: list[InvoiceObservation] = []
    deleted: list[DeletedInvoiceEvidence] = []
    for record in records:
        if type(record) is not dict:
            raise _fail("CDC entity must be an exact object")
        updated = _metadata_time(record, changed_since=start, retrieved_at=end)
        if "status" in record:
            if set(record) != {"Id", "status", "MetaData"} or record["status"] != "Deleted":
                raise _fail("CDC tombstone shape is invalid")
            identity = _safe_tombstone_id(record["Id"])
            tombstone = DeletedInvoiceEvidence(
                identity, updated, end, _digest(record),
                user_id, realm_id, credential_reference,
            )
            event: InvoiceObservation | DeletedInvoiceEvidence = tombstone
            deleted.append(tombstone)
        else:
            observation = _observe(
                QueryEntity.INVOICE, record, binding=binding, user_id=user_id,
                realm_id=realm_id, credential_reference=credential_reference,
                retrieved_at=end,
            )
            identity = object.__getattribute__(observation, "entity_id")
            event = observation
            live.append(observation)
        if identity in seen:
            raise _fail("duplicate or live/tombstone-conflicting CDC identity")
        seen.add(identity)
        events.append(event)

    saturated = len(records) == MAX_CDC_OBJECTS
    completeness = ResourceCompleteness(
        resource="Invoice",
        pagination=CompletenessState.NOT_APPLICABLE,
        terminal_page_evidence=CompletenessState.NOT_APPLICABLE,
        independent_source_totals=CompletenessState.UNKNOWN,
        incremental_watermark_or_revision=CompletenessState.UNKNOWN,
        deletion_tombstone_detection=CompletenessState.UNKNOWN,
        webhook_coverage=CompletenessState.UNKNOWN,
        polling_or_full_refresh=CompletenessState.UNKNOWN,
        known_exclusions=CompletenessState.UNKNOWN,
        freshness_limitations=(CompletenessState.INCOMPLETE if saturated
                               else CompletenessState.UNKNOWN),
        reason=("CDC object cap reached; truncation cannot be excluded" if saturated
                else "bounded CDC response validated without continuous-chain proof"),
    )
    return CdcWindowEvidence(
        minor_version, start, end, tuple(events), tuple(live), tuple(deleted),
        saturated, completeness, FitnessStatus.UNVERIFIED,
        ("CDC boundary inclusivity is not established",
         "no provider-issued next watermark is available",
         "continuous coverage and historical completeness are not established"),
        _PROHIBITED,
    )
