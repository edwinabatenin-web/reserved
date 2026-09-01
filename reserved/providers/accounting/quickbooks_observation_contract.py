"""Network-inert validation of already-retrieved QuickBooks source evidence.

This module deliberately has no transport, credential custody, persistence,
logging, canonical accounting, tax, payment, or provider-enablement capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re
from typing import Any, Iterator, Mapping, Sequence

from .quickbooks_oauth_contract import RealmBinding


LINE_DETAIL_TYPES = frozenset({
    "SalesItemLineDetail", "DiscountLineDetail", "SubTotalLineDetail",
})
GLOBAL_TAX_CALCULATIONS = frozenset({
    "TaxExcluded", "TaxInclusive", "NotApplicable",
})

_MAX_ID = 512
_MAX_STRING = 4096
_MAX_COMPANY_NAME = 1024
_MAX_LINES = 750
_MAX_DEPTH = 24
_MAX_NODES = 50_000
_MAX_WIDTH = 2_000
_MAX_BYTES = 2_000_000
_MAX_DECIMAL_DIGITS = 38
_MAX_DECIMAL_PLACES = 12
_MAX_ABS_DECIMAL = Decimal("1000000000000000000")
_DECIMAL_TEXT = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_DATE_TEXT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_TIMESTAMP_TEXT = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)


class QuickBooksObservationError(ValueError):
    """Controlled validation failure whose message never includes source data."""


class FrozenEvidence(Mapping[str, Any]):
    """Immutable evidence mapping whose representation cannot disclose values."""

    __slots__ = ("__values",)

    def __init__(self, values: Mapping[str, Any]) -> None:
        self.__values = tuple(dict(values).items())

    def __getitem__(self, key: str) -> Any:
        for stored_key, value in self.__values:
            if stored_key == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _ in self.__values)

    def __len__(self) -> int:
        return len(self.__values)

    def __repr__(self) -> str:
        return "FrozenEvidence([REDACTED])"


class FrozenEvidenceSequence(Sequence[Any]):
    """Immutable evidence array whose representation cannot disclose values."""

    __slots__ = ("__values",)

    def __init__(self, values: Sequence[Any]) -> None:
        self.__values = tuple(values)

    def __getitem__(self, index: Any) -> Any:
        result = self.__values[index]
        if type(index) is slice:
            return FrozenEvidenceSequence(result)
        return result

    def __iter__(self) -> Iterator[Any]:
        return iter(self.__values)

    def __len__(self) -> int:
        return len(self.__values)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FrozenEvidenceSequence):
            return self.__values == other.__values
        if type(other) in (list, tuple):
            return self.__values == tuple(other)
        return NotImplemented

    def __repr__(self) -> str:
        return "FrozenEvidenceSequence([REDACTED])"


def _fail(rule: str) -> QuickBooksObservationError:
    return QuickBooksObservationError(f"QuickBooks observation contract: {rule}")


def _text(value: Any, field: str, maximum: int = _MAX_ID) -> str:
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise _fail(f"{field} must be a bounded non-blank string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise _fail(f"{field} contains invalid Unicode") from None
    if len(encoded) > maximum * 4 or any(ord(char) < 32 for char in value):
        raise _fail(f"{field} must be a bounded safe string")
    return value


def _object(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise _fail(f"{field} must be an object")
    for key in value:
        if type(key) is not str:
            raise _fail(f"{field} keys must be strings")
        _safe_string(key, f"{field} key")
    return value


def _safe_string(value: str, field: str) -> bytes:
    if len(value) > _MAX_STRING:
        raise _fail(f"{field} exceeds the string bound")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise _fail(f"{field} contains invalid Unicode") from None
    if len(encoded) > _MAX_STRING * 4:
        raise _fail(f"{field} exceeds the byte bound")
    return encoded


def _preflight(root: Any) -> None:
    """Bound and validate the complete graph before sorting or digesting it."""
    stack = [(root, 0)]
    nodes = byte_count = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_NODES:
            raise _fail("source exceeds the node bound")
        if depth > _MAX_DEPTH:
            raise _fail("source exceeds the depth bound")
        if value is None or type(value) is bool:
            byte_count += 1
        elif type(value) is str:
            byte_count += len(_safe_string(value, "source string"))
        elif type(value) is int:
            if abs(value) > _MAX_ABS_DECIMAL:
                raise _fail("source contains an excessive integer")
            byte_count += len(str(value))
        elif type(value) is Decimal:
            _bounded_decimal(value, "source decimal", accept_string=False)
            byte_count += len(str(value))
        elif type(value) is dict:
            obj = _object(value, "source object")
            if len(obj) > _MAX_WIDTH:
                raise _fail("source exceeds the container-width bound")
            for key, item in obj.items():
                byte_count += len(_safe_string(key, "source key"))
                stack.append((item, depth + 1))
        elif type(value) is list:
            if len(value) > _MAX_WIDTH:
                raise _fail("source exceeds the container-width bound")
            stack.extend((item, depth + 1) for item in value)
        elif isinstance(value, (bytes, bytearray, memoryview)):
            if len(value) > _MAX_BYTES:
                raise _fail("source exceeds the byte-material bound")
            raise _fail("source contains unsupported byte material")
        else:
            raise _fail("source contains an unsupported value type")
        if byte_count > _MAX_BYTES:
            raise _fail("source exceeds the payload-size bound")


def _bounded_decimal(value: Any, field: str, *, accept_string: bool = True) -> Decimal:
    if type(value) is bool or type(value) is float:
        raise _fail(f"{field} must be an exact decimal")
    if type(value) is str:
        if not accept_string or len(value) > 80 or not _DECIMAL_TEXT.fullmatch(value):
            raise _fail(f"{field} must be an exact decimal")
        material: Any = value
    elif type(value) in (int, Decimal):
        material = value
    else:
        raise _fail(f"{field} must be an exact decimal")
    try:
        result = Decimal(material)
    except (InvalidOperation, ValueError, OverflowError):
        raise _fail(f"{field} must be a finite bounded decimal") from None
    if not result.is_finite():
        raise _fail(f"{field} must be a finite bounded decimal")
    number = result.as_tuple()
    places = max(0, -number.exponent)
    integer_digits = max(1, len(number.digits) + number.exponent)
    if (abs(result) > _MAX_ABS_DECIMAL
            or len(number.digits) > _MAX_DECIMAL_DIGITS
            or places > _MAX_DECIMAL_PLACES
            or integer_digits > _MAX_DECIMAL_DIGITS):
        raise _fail(f"{field} must be a finite bounded decimal")
    return result


def _day(value: Any, field: str) -> date:
    if type(value) is not str or not _DATE_TEXT.fullmatch(value):
        raise _fail(f"{field} must be a strict ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _fail(f"{field} must be a strict ISO date") from None


def _timestamp(value: Any, field: str) -> datetime:
    if type(value) is not str or not _TIMESTAMP_TEXT.fullmatch(value):
        raise _fail(f"{field} must be a strict offset ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise _fail(f"{field} must be a strict offset ISO timestamp") from None
    if parsed.utcoffset() is None:
        raise _fail(f"{field} must be a strict offset ISO timestamp")
    return parsed


def _retrieval_time(value: Any) -> datetime:
    if type(value) is not datetime:
        raise _fail("retrieved_at must be an aware datetime")
    zone = object.__getattribute__(value, "tzinfo")
    # datetime methods dispatch to tzinfo hooks.  Admit only the exact built-in
    # fixed-offset implementation before invoking any of them, then retain one
    # canonical UTC representation for replay and attestation.
    if type(zone) is not timezone:
        raise _fail("retrieved_at must use a fixed-offset timezone")
    return value.astimezone(timezone.utc)


def _freeze(value: Any) -> Any:
    if type(value) is dict:
        return FrozenEvidence({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return FrozenEvidenceSequence([_freeze(item) for item in value])
    return value


def _thaw_retained_evidence(root: Any) -> Any:
    """Validate and iteratively reconstruct an exact retained evidence graph."""
    stack = [(root, 0)]
    containers: list[Any] = []
    seen: set[int] = set()
    nodes = byte_count = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_NODES:
            raise _fail("retained evidence exceeds the node bound")
        if depth > _MAX_DEPTH:
            raise _fail("retained evidence exceeds the depth bound")
        value_type = type(value)
        if value is None or value_type is bool:
            byte_count += 1
        elif value_type is str:
            byte_count += len(_safe_string(value, "retained evidence string"))
        elif value_type is int:
            if abs(value) > _MAX_ABS_DECIMAL:
                raise _fail("retained evidence contains an excessive integer")
            byte_count += len(str(value))
        elif value_type is Decimal:
            _bounded_decimal(value, "retained evidence decimal", accept_string=False)
            byte_count += len(str(value))
        elif value_type is FrozenEvidence:
            identity = id(value)
            if identity in seen:
                raise _fail("retained evidence contains a cycle or alias")
            seen.add(identity)
            values = object.__getattribute__(value, "_FrozenEvidence__values")
            if (type(values) is not tuple
                    or any(type(item) is not tuple or len(item) != 2
                           for item in values)):
                raise _fail("retained evidence container storage is invalid")
            items = values
            if len(items) > _MAX_WIDTH:
                raise _fail("retained evidence exceeds the container-width bound")
            containers.append(value)
            for key, item in items:
                if type(key) is not str:
                    raise _fail("retained evidence keys must be strings")
                byte_count += len(_safe_string(key, "retained evidence key"))
                stack.append((item, depth + 1))
        elif value_type is FrozenEvidenceSequence:
            identity = id(value)
            if identity in seen:
                raise _fail("retained evidence contains a cycle or alias")
            seen.add(identity)
            values = object.__getattribute__(value, "_FrozenEvidenceSequence__values")
            if type(values) is not tuple:
                raise _fail("retained evidence container storage is invalid")
            if len(values) > _MAX_WIDTH:
                raise _fail("retained evidence exceeds the container-width bound")
            containers.append(value)
            stack.extend((item, depth + 1) for item in values)
        elif value_type in (bytes, bytearray, memoryview):
            raise _fail("retained evidence contains unsupported byte material")
        else:
            raise _fail("retained evidence contains an unsupported value type")
        if byte_count > _MAX_BYTES:
            raise _fail("retained evidence exceeds the payload-size bound")

    rebuilt: dict[int, Any] = {}
    for value in reversed(containers):
        if type(value) is FrozenEvidence:
            values = object.__getattribute__(value, "_FrozenEvidence__values")
            rebuilt[id(value)] = {
                key: rebuilt[id(item)] if type(item) in
                (FrozenEvidence, FrozenEvidenceSequence) else item
                for key, item in values
            }
        else:
            values = object.__getattribute__(value, "_FrozenEvidenceSequence__values")
            rebuilt[id(value)] = [
                rebuilt[id(item)] if type(item) in
                (FrozenEvidence, FrozenEvidenceSequence) else item
                for item in values
            ]
    return rebuilt[id(root)] if type(root) in (
        FrozenEvidence, FrozenEvidenceSequence) else root


def _digest(value: Any) -> str:
    output = sha256()

    def write(value: bytes) -> None:
        output.update(str(len(value)).encode("ascii") + b":" + value)

    def emit(item: Any) -> None:
        if item is None:
            write(b"null")
        elif type(item) is bool:
            write(b"bool:1" if item else b"bool:0")
        elif type(item) is int:
            write(b"int:" + str(item).encode("ascii"))
        elif type(item) is Decimal:
            parts = item.as_tuple()
            write(b"decimal:" + str(parts.sign).encode() + b":"
                  + str(parts.exponent).encode() + b":" + bytes(parts.digits))
        elif type(item) is str:
            write(b"string:" + item.encode("utf-8"))
        elif isinstance(item, Mapping):
            write(b"object")
            for key in sorted(item):
                write(key.encode("utf-8")); emit(item[key])
            write(b"end-object")
        else:
            write(b"array")
            for child in item:
                emit(child)
            write(b"end-array")

    emit(value)
    return output.hexdigest()


def observation_attestation(kind: str, source_digest: str, user_id: str,
                            realm_id: str, credential_reference: str,
                            retrieved_at: datetime) -> str:
    """Deterministically bind raw evidence to its Q-S4 retrieval identity."""
    if kind not in {"CompanyInfoObservation", "InvoiceObservation",
                    "PaymentObservation"}:
        raise _fail("observation attestation kind is invalid")
    if (type(source_digest) is not str
            or re.fullmatch(r"[0-9a-f]{64}", source_digest) is None):
        raise _fail("observation attestation source digest is invalid")
    user = _text(user_id, "user_id")
    realm = _text(realm_id, "realm_id")
    credential = _text(credential_reference, "credential_reference")
    when = _retrieval_time(retrieved_at).astimezone(timezone.utc)
    material = {
        "schema": "quickbooks-qbo-qs4-observation-attestation-v1",
        "kind": kind, "source_digest": source_digest, "user_id": user,
        "realm_id": realm, "credential_reference": credential,
        "retrieved_at": when.isoformat(timespec="microseconds"),
    }
    return _digest(material)


def _presence(source: Mapping[str, Any]) -> tuple[frozenset[str], frozenset[str]]:
    return frozenset(source), frozenset(key for key, value in source.items() if value is None)


def _metadata_timestamps(source: Mapping[str, Any]) -> None:
    if "MetaData" not in source or source["MetaData"] is None:
        return
    metadata = _object(source["MetaData"], "MetaData")
    for name in ("CreateTime", "LastUpdatedTime"):
        if name in metadata and metadata[name] is not None:
            _timestamp(metadata[name], f"MetaData.{name}")


def _identity(binding: Any, user_id: Any, realm_id: Any,
              credential_reference: Any) -> tuple[str, str, str]:
    user = _text(user_id, "user_id")
    realm = _text(realm_id, "realm_id")
    credential = _text(credential_reference, "credential_reference")
    if type(binding) is not RealmBinding:
        raise _fail("binding must be a Q-S1 RealmBinding")
    bound_user = object.__getattribute__(binding, "user_id")
    bound_realm = object.__getattribute__(binding, "realm_id")
    bound_credential = object.__getattribute__(binding, "credential_reference")
    if any(type(value) is not str
           for value in (bound_user, bound_realm, bound_credential)):
        raise _fail("realm binding identity is invalid")
    bound_user = _text(bound_user, "binding.user_id")
    bound_realm = _text(bound_realm, "binding.realm_id")
    bound_credential = _text(
        bound_credential, "binding.credential_reference")
    if (bound_user != user or bound_realm != realm
            or bound_credential != credential):
        raise _fail("realm binding identity does not match")
    return user, realm, credential


@dataclass(frozen=True, repr=False)
class CompanyInfoObservation:
    user_id: str
    realm_id: str
    credential_reference: str
    entity_id: str
    sync_token: str
    retrieved_at: datetime
    source_digest: str
    observation_attestation: str
    company_name: str
    legal_name: str | None
    country: str | None
    fiscal_year_start_month: str | None
    company_start_date: date | None
    present_fields: frozenset[str]
    null_fields: frozenset[str]
    source_evidence: Mapping[str, Any]

    def __repr__(self) -> str:
        return "CompanyInfoObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class InvoiceLineObservation:
    detail_type: str
    amount: Decimal | None
    present_fields: frozenset[str]
    null_fields: frozenset[str]
    source_evidence: Mapping[str, Any]

    def __repr__(self) -> str:
        return "InvoiceLineObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class InvoiceObservation:
    user_id: str
    realm_id: str
    credential_reference: str
    entity_id: str
    sync_token: str
    retrieved_at: datetime
    source_digest: str
    observation_attestation: str
    lines: tuple[InvoiceLineObservation, ...]
    customer_reference_value: str
    transaction_date: date | None
    due_date: date | None
    total_amount: Decimal | None
    balance: Decimal | None
    currency_ref_present: bool
    global_tax_calculation: str | None
    transaction_tax_detail_present: bool
    present_fields: frozenset[str]
    null_fields: frozenset[str]
    source_evidence: Mapping[str, Any]

    def __repr__(self) -> str:
        return "InvoiceObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class PaymentLinkObservation:
    transaction_id: str | None
    transaction_type: str | None
    present_fields: frozenset[str]
    null_fields: frozenset[str]
    source_evidence: Mapping[str, Any]

    def __repr__(self) -> str:
        return "PaymentLinkObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class PaymentLineObservation:
    amount: Decimal | None
    links: tuple[PaymentLinkObservation, ...]
    present_fields: frozenset[str]
    null_fields: frozenset[str]
    source_evidence: Mapping[str, Any]

    def __repr__(self) -> str:
        return "PaymentLineObservation([REDACTED])"


@dataclass(frozen=True, repr=False)
class PaymentObservation:
    user_id: str
    realm_id: str
    credential_reference: str
    entity_id: str
    sync_token: str
    retrieved_at: datetime
    source_digest: str
    observation_attestation: str
    lines: tuple[PaymentLineObservation, ...]
    customer_reference_value: str
    transaction_date: date | None
    total_amount: Decimal | None
    unapplied_amount: Decimal | None
    currency_ref_present: bool
    currency_ref_null: bool
    present_fields: frozenset[str]
    null_fields: frozenset[str]
    source_evidence: Mapping[str, Any]

    def __repr__(self) -> str:
        return "PaymentObservation([REDACTED])"


def observe_company_info(source: Any, *, binding: RealmBinding, user_id: str,
                         realm_id: str, credential_reference: str,
                         retrieved_at: datetime) -> CompanyInfoObservation:
    _preflight(source)
    obj = _object(source, "CompanyInfo")
    user, realm, credential = _identity(
        binding, user_id, realm_id, credential_reference)
    entity_id = _text(obj.get("Id"), "Id")
    sync = _text(obj.get("SyncToken"), "SyncToken")
    company_name = _text(obj.get("CompanyName"), "CompanyName", _MAX_COMPANY_NAME)
    when = _retrieval_time(retrieved_at)
    _metadata_timestamps(obj)
    legal = None if obj.get("LegalName") is None else _text(obj["LegalName"], "LegalName", _MAX_STRING)
    country = None if obj.get("Country") is None else _text(obj["Country"], "Country", _MAX_STRING)
    fiscal = None if obj.get("FiscalYearStartMonth") is None else _text(obj["FiscalYearStartMonth"], "FiscalYearStartMonth", 20)
    started = None if obj.get("CompanyStartDate") is None else _day(obj["CompanyStartDate"], "CompanyStartDate")
    present, nulls = _presence(obj)
    digest = _digest(obj)
    attestation = observation_attestation(
        "CompanyInfoObservation", digest, user, realm, credential, when)
    return CompanyInfoObservation(user, realm, credential, entity_id, sync, when,
        digest, attestation, company_name, legal, country, fiscal, started, present,
        nulls, _freeze(obj))


def observe_invoice(source: Any, *, binding: RealmBinding, user_id: str,
                    realm_id: str, credential_reference: str,
                    retrieved_at: datetime) -> InvoiceObservation:
    _preflight(source)
    obj = _object(source, "Invoice")
    user, realm, credential = _identity(
        binding, user_id, realm_id, credential_reference)
    entity_id = _text(obj.get("Id"), "Id")
    sync = _text(obj.get("SyncToken"), "SyncToken")
    when = _retrieval_time(retrieved_at)
    customer = _object(obj.get("CustomerRef"), "CustomerRef")
    customer_value = _text(customer.get("value"), "CustomerRef.value")
    raw_lines = obj.get("Line")
    if type(raw_lines) is not list or not raw_lines or len(raw_lines) > _MAX_LINES:
        raise _fail("Line must contain between 1 and 750 entries")
    lines = []
    for raw in raw_lines:
        line = _object(raw, "Line entry")
        detail = _text(line.get("DetailType"), "Line.DetailType", 64)
        if detail not in LINE_DETAIL_TYPES:
            raise _fail("Line.DetailType is not a documented category")
        detail_members = [key for key in line if key.endswith("LineDetail")]
        if detail_members != [detail] or type(line[detail]) is not dict:
            raise _fail("Line must contain exactly its matching non-null detail object")
        amount = None if "Amount" not in line or line["Amount"] is None else _bounded_decimal(line["Amount"], "Line.Amount")
        line_present, line_nulls = _presence(line)
        lines.append(InvoiceLineObservation(detail, amount, line_present,
                                            line_nulls, _freeze(line)))
    transaction_date = None if obj.get("TxnDate") is None else _day(obj["TxnDate"], "TxnDate")
    due_date = None if obj.get("DueDate") is None else _day(obj["DueDate"], "DueDate")
    total = None if obj.get("TotalAmt") is None else _bounded_decimal(obj["TotalAmt"], "TotalAmt")
    balance = None if obj.get("Balance") is None else _bounded_decimal(obj["Balance"], "Balance")
    tax = obj.get("GlobalTaxCalculation")
    if tax is not None:
        tax = _text(tax, "GlobalTaxCalculation", 32)
        if tax not in GLOBAL_TAX_CALCULATIONS:
            raise _fail("GlobalTaxCalculation is not documented")
    _metadata_timestamps(obj)
    present, nulls = _presence(obj)
    digest = _digest(obj)
    attestation = observation_attestation(
        "InvoiceObservation", digest, user, realm, credential, when)
    return InvoiceObservation(user, realm, credential, entity_id, sync, when,
        digest, attestation, tuple(lines), customer_value, transaction_date, due_date,
        total, balance, "CurrencyRef" in obj, tax, "TxnTaxDetail" in obj,
        present, nulls, _freeze(obj))


def _nonnegative_decimal(value: Any, field: str) -> Decimal:
    result = _bounded_decimal(value, field)
    if result < 0:
        raise _fail(f"{field} must be nonnegative")
    return result


def observe_payment(source: Any, *, binding: RealmBinding, user_id: str,
                    realm_id: str, credential_reference: str,
                    retrieved_at: datetime) -> PaymentObservation:
    """Observe an already-retrieved Payment without interpreting settlement."""
    _preflight(source)
    obj = _object(source, "Payment")
    user, realm, credential = _identity(
        binding, user_id, realm_id, credential_reference)
    entity_id = _text(obj.get("Id"), "Id")
    sync = _text(obj.get("SyncToken"), "SyncToken")
    when = _retrieval_time(retrieved_at)
    customer = _object(obj.get("CustomerRef"), "CustomerRef")
    customer_value = _text(customer.get("value"), "CustomerRef.value")

    lines: list[PaymentLineObservation] = []
    if "Line" in obj:
        raw_lines = obj["Line"]
        if type(raw_lines) is not list or len(raw_lines) > _MAX_LINES:
            raise _fail("Line must be a list of at most 750 entries")
        for raw in raw_lines:
            line = _object(raw, "Line entry")
            amount = None
            if "Amount" in line and line["Amount"] is not None:
                amount = _nonnegative_decimal(line["Amount"], "Line.Amount")
            links: list[PaymentLinkObservation] = []
            if "LinkedTxn" in line:
                raw_links = line["LinkedTxn"]
                if type(raw_links) is not list or len(raw_links) > _MAX_LINES:
                    raise _fail("Line.LinkedTxn must be a list of at most 750 entries")
                for raw_link in raw_links:
                    link = _object(raw_link, "Line.LinkedTxn entry")
                    transaction_id = (_text(link["TxnId"], "LinkedTxn.TxnId")
                                      if "TxnId" in link else None)
                    transaction_type = (_text(link["TxnType"], "LinkedTxn.TxnType", 64)
                                        if "TxnType" in link else None)
                    link_present, link_nulls = _presence(link)
                    links.append(PaymentLinkObservation(
                        transaction_id, transaction_type, link_present,
                        link_nulls, _freeze(link)))
            line_present, line_nulls = _presence(line)
            lines.append(PaymentLineObservation(
                amount, tuple(links), line_present, line_nulls, _freeze(line)))

    transaction_date = (None if obj.get("TxnDate") is None
                        else _day(obj["TxnDate"], "TxnDate"))
    total = (None if obj.get("TotalAmt") is None
             else _nonnegative_decimal(obj["TotalAmt"], "TotalAmt"))
    unapplied = (None if obj.get("UnappliedAmt") is None
                 else _nonnegative_decimal(obj["UnappliedAmt"], "UnappliedAmt"))
    _metadata_timestamps(obj)
    present, nulls = _presence(obj)
    digest = _digest(obj)
    attestation = observation_attestation(
        "PaymentObservation", digest, user, realm, credential, when)
    return PaymentObservation(
        user, realm, credential, entity_id, sync, when, digest, attestation,
        tuple(lines), customer_value, transaction_date, total, unapplied,
        "CurrencyRef" in obj, obj.get("CurrencyRef") is None and "CurrencyRef" in obj,
        present, nulls, _freeze(obj))
