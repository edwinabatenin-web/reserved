"""Network-inert validation of already-retrieved QuickBooks source evidence.

This module deliberately has no transport, credential custody, persistence,
logging, canonical accounting, tax, payment, or provider-enablement capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re
from types import MappingProxyType
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
        self.__values = MappingProxyType(dict(values))

    def __getitem__(self, key: str) -> Any:
        return self.__values[key]

    def __iter__(self):
        return iter(self.__values)

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
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise _fail("retrieved_at must be an aware datetime")
    return value


def _freeze(value: Any) -> Any:
    if type(value) is dict:
        return FrozenEvidence({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return FrozenEvidenceSequence([_freeze(item) for item in value])
    return value


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
    if (binding.user_id != user or binding.realm_id != realm
            or binding.credential_reference != credential):
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
    return CompanyInfoObservation(user, realm, credential, entity_id, sync, when,
        _digest(obj), company_name, legal, country, fiscal, started, present,
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
    return InvoiceObservation(user, realm, credential, entity_id, sync, when,
        _digest(obj), tuple(lines), customer_value, transaction_date, due_date,
        total, balance, "CurrencyRef" in obj, tax, "TxnTaxDetail" in obj,
        present, nulls, _freeze(obj))
