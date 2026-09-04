"""Pure W9-S3C adapter from admitted S3A projections to S3B candidates.

The adapter validates a live, exact S3A projection at the call boundary, binds
it to explicit current owner/business facts, and copies only the already
minimised fields into an S3B primitive structural candidate.  Upstream
admission is deliberately *not* transferred.  The result is a deterministic
non-authoritative operation tuple; it is not a writer credential, datastore
record, migration, retention decision, or permission to persist anything.
"""

from __future__ import annotations

import types as _types
import re as _re
import hashlib as _hashlib
import json as _json
from datetime import date as _date
from datetime import timedelta as _timedelta
from decimal import Decimal as _Decimal

import reserved.annual_position_persistence_contract as _s3a
import reserved.annual_position_repository_contract as _s3b
from reserved.services.w2_customer_language import (
    AdjustmentFact as _AdjustmentFact,
    AdjustmentKind as _AdjustmentKind,
    EvidenceClassification as _EvidenceClassification,
    FundingClassification as _FundingClassification,
    ObligationFact as _ObligationFact,
    ObligationKind as _ObligationKind,
)
from reserved.services.w8_customer_result import SupportedNation as _SupportedNation


ADAPTER_VERSION = "reserved-annual-position-projection-repository-adapter/1.0"
AUTHORITY_STATUS = "validated_live_projection_detached_without_transferring_admission"
SOURCE_S3A_COMMIT = "c489c25bab669c64e1c11d28caf29fcde9678fdd"
SOURCE_S3A_SHA256 = "da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469"
SOURCE_S3B_COMMIT = "110a90043dfc770c70059482be9d7b7e237749a6"
SOURCE_S3B_SHA256 = "fa033039500b97bab04f3a047c07ad661c14c49d6167d65396d4d9ab0227053e"


class ProjectionRepositoryAdapterError(ValueError):
    """Fail-closed W9-S3C adapter error."""


def _build_adapter():
    # Capture the full acceptance boundary once.  Rebinding public module names,
    # class attributes, builtins, defaults, or helper globals later cannot
    # change which exact S3A/S3B authorities this adapter invokes.
    T, S, I, B, D = tuple, str, int, bool, dict
    typ, raw, length = type, object.__getattribute__, len
    any_fn, enumerate_fn, set_type = any, enumerate, set
    sorted_fn, zip_fn, id_fn = sorted, zip, id
    type_error, value_error = TypeError, ValueError
    function_type = _types.FunctionType
    error = ProjectionRepositoryAdapterError
    date_type, decimal_type, delta_type = _date, _Decimal, _timedelta
    parse_date, compile_rx = _date.fromisoformat, _re.compile
    sha256, json_dumps = _hashlib.sha256, _json.dumps

    adapter_version = ADAPTER_VERSION
    authority_status = AUTHORITY_STATUS
    source_s3a_commit, source_s3a_hash = SOURCE_S3A_COMMIT, SOURCE_S3A_SHA256
    source_s3b_commit, source_s3b_hash = SOURCE_S3B_COMMIT, SOURCE_S3B_SHA256

    projection_type = _s3a.AnnualPositionPersistenceProjection
    projection_identity = _s3a.annual_position_projection_identity
    validate_chain = _s3a.validate_supersession_chain
    make_candidate = _s3b.make_structural_candidate
    candidate_identity = _s3b.structural_candidate_identity

    if (
        typ(_s3a.SCHEMA_VERSION) is not S
        or _s3a.SCHEMA_VERSION != "reserved-annual-position-persistence/1.0"
        or typ(_s3a.RECORD_PURPOSE) is not S
        or _s3a.RECORD_PURPOSE != "annual_cash_position_durable_projection"
        or typ(_s3b.SOURCE_S3A_COMMIT) is not S
        or _s3b.SOURCE_S3A_COMMIT != source_s3a_commit
        or typ(_s3b.SOURCE_S3A_SHA256) is not S
        or _s3b.SOURCE_S3A_SHA256 != source_s3a_hash
        or typ(_s3b.SOURCE_S3A_SCHEMA_VERSION) is not S
        or _s3b.SOURCE_S3A_SCHEMA_VERSION != _s3a.SCHEMA_VERSION
        or typ(_s3b.SOURCE_RECORD_PURPOSE) is not S
        or _s3b.SOURCE_RECORD_PURPOSE != _s3a.RECORD_PURPOSE
    ):
        raise RuntimeError("W9-S3A/S3B source boundary does not match W9-S3C")

    projection_fields = (
        "schema_version", "record_purpose", "record_version", "user_id",
        "business_id", "nation", "tax_year", "annual_cash_identity",
        "customer_result_identity", "evidence_classification",
        "annual_liability", "obligations", "adjustments", "funding",
        "funding_amount", "evidence_references", "ruleset_version", "as_of",
        "stale_after_days", "customer_result_limitations",
        "customer_result_prohibited_uses", "unresolved_inputs",
        "deletion_state", "account_erasure_eligibility",
        "predecessor_identity", "annual_cash_identity_admitted",
    )
    projection_descriptors = T(
        projection_type.__dict__[name] for name in projection_fields
    )

    obligation_type, adjustment_type = _ObligationFact, _AdjustmentFact
    evidence_type, funding_type = _EvidenceClassification, _FundingClassification
    nation_type = _SupportedNation
    obligation_kind_type, adjustment_kind_type = _ObligationKind, _AdjustmentKind
    obligation_values = (
        (_ObligationKind.BALANCING_PAYMENT, "balancing_payment"),
        (_ObligationKind.FIRST_PAYMENT_ON_ACCOUNT, "first_payment_on_account"),
        (_ObligationKind.SECOND_PAYMENT_ON_ACCOUNT, "second_payment_on_account"),
    )
    adjustment_values = (
        (_AdjustmentKind.DEDUCTIONS_AND_CREDITS, "deductions_and_credits"),
        (_AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT, "prior_payments_on_account"),
        (_AdjustmentKind.PAYMENTS_MADE, "payments_made"),
        (_AdjustmentKind.CREDIT_OR_REFUND, "credit_or_refund"),
    )
    funding_values = (
        (_FundingClassification.GAP, "gap"),
        (_FundingClassification.EXACT, "exact"),
        (_FundingClassification.SURPLUS, "surplus"),
    )
    nation_values = (
        (_SupportedNation.ENGLAND, "England"),
        (_SupportedNation.WALES, "Wales"),
        (_SupportedNation.NORTHERN_IRELAND, "Northern Ireland"),
    )
    qualified_estimate = _EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    source_identity_rx = compile_rx(
        r"^annual-position-persistence:sha256-[0-9a-f]{64}$"
    )

    operation_fields = (
        "adapter_version", "authority_status", "source_s3a_commit",
        "source_s3a_sha256", "source_s3b_commit", "source_s3b_sha256",
        "source_projection_identity", "source_predecessor_projection_identity",
        "source_predecessor_structural_candidate",
        "authenticated_user_id", "authenticated_business_id", "evaluated_on",
        "structural_candidate", "structural_candidate_identity",
        "source_admission_transferred", "persistence_authority",
        "storage_authority", "migration_authority", "retention_authority",
        "deletion_authority", "legal_authority", "credential_authority",
        "encryption_or_key_custody_authority", "target_authority",
        "production_activation_authority", "release_authority",
    )
    input_fields = (
        "projection", "authenticated_user_id", "authenticated_business_id",
        "evaluated_on", "previous_projection", "previous_structural_candidate",
    )

    def slot(value, name):
        descriptor = projection_descriptors[projection_fields.index(name)]
        return descriptor.__get__(value, projection_type)

    def function_snapshot(roots):
        seen, stack, rows = set(), list(roots), []
        while stack:
            fn = stack.pop()
            if typ(fn) is not function_type or id_fn(fn) in seen:
                continue
            seen.add(id_fn(fn))
            cells = fn.__closure__ or ()
            contents = []
            for cell in cells:
                try:
                    value = cell.cell_contents
                except ValueError:
                    value = cell
                contents.append((cell, value))
                if typ(value) is function_type:
                    stack.append(value)
            kw = fn.__kwdefaults__
            frozen_kw = None if kw is None else T(sorted_fn(kw.items()))
            rows.append(
                (fn, fn.__code__, fn.__defaults__, kw, frozen_kw, T(contents))
            )
        return T(rows)

    upstream_snapshot = function_snapshot(
        (projection_identity, validate_chain, make_candidate, candidate_identity)
    )

    def require_unchanged_upstream():
        for fn, code, defaults, kw, frozen_kw, contents in upstream_snapshot:
            if fn.__code__ is not code or fn.__defaults__ is not defaults:
                raise error("captured upstream validation authority was altered")
            if fn.__kwdefaults__ is not kw:
                raise error("captured upstream validation defaults were replaced")
            if kw is not None and T(sorted_fn(kw.items())) != frozen_kw:
                raise error("captured upstream validation defaults were altered")
            cells = fn.__closure__ or ()
            if length(cells) != length(contents):
                raise error("captured upstream validation closure was altered")
            for actual, (expected_cell, expected_value) in zip_fn(
                cells, contents, strict=True
            ):
                if actual is not expected_cell:
                    raise error("captured upstream validation closure was replaced")
                try:
                    value = actual.cell_contents
                except value_error:
                    value = actual
                if value is not expected_value:
                    raise error("captured upstream validation closure state was altered")

    def enum_value(value, expected_type, choices, subject):
        if typ(value) is not expected_type:
            raise error(f"invalid {subject} type")
        for member, label in choices:
            if value is member:
                return label
        raise error(f"unsupported {subject}")

    def money(value, subject):
        if typ(value) is not decimal_type:
            raise error(f"invalid {subject} money type")
        return S(value)

    def read_projection(value, authenticated_user_id, authenticated_business_id,
            evaluated_on, *, require_fresh):
        require_unchanged_upstream()
        if typ(value) is not projection_type:
            raise error("projection is not an exact W9-S3A projection")
        before = projection_identity(value)
        if slot(value, "annual_cash_identity_admitted") is not True:
            raise error("projection was not admitted by the live W9-S3A boundary")
        if typ(authenticated_user_id) is not S or typ(authenticated_business_id) is not S:
            raise error("authenticated owner and business must be exact strings")
        if authenticated_user_id != slot(value, "user_id"):
            raise error("projection crossed the authenticated owner boundary")
        if authenticated_business_id != slot(value, "business_id"):
            raise error("projection crossed the authenticated business boundary")
        if typ(evaluated_on) is not date_type:
            raise error("evaluation date must be an exact date")
        as_of = slot(value, "as_of")
        horizon = slot(value, "stale_after_days")
        if evaluated_on < as_of:
            raise error("projection as-of date is in the future")
        if require_fresh and evaluated_on > as_of + delta_type(days=horizon):
            raise error("projection is stale at the adapter boundary")

        obligations = T(
            (
                enum_value(raw(item, "kind"), obligation_kind_type,
                    obligation_values, "obligation kind"),
                money(raw(item, "amount"), "obligation"),
                date_type.isoformat(raw(item, "due_date")),
            )
            for item in slot(value, "obligations")
            if typ(item) is obligation_type
        )
        if length(obligations) != length(slot(value, "obligations")):
            raise error("projection contains a non-exact obligation fact")
        adjustments = T(
            (
                enum_value(raw(item, "kind"), adjustment_kind_type,
                    adjustment_values, "adjustment kind"),
                money(raw(item, "amount"), "adjustment"),
            )
            for item in slot(value, "adjustments")
            if typ(item) is adjustment_type
        )
        if length(adjustments) != length(slot(value, "adjustments")):
            raise error("projection contains a non-exact adjustment fact")
        funding_amount = slot(value, "funding_amount")
        if funding_amount is not None:
            funding_amount = money(funding_amount, "funding")

        fields = {
            "record_version": slot(value, "record_version"),
            "user_id": slot(value, "user_id"),
            "business_id": slot(value, "business_id"),
            "tax_year": slot(value, "tax_year"),
            "nation": enum_value(slot(value, "nation"), nation_type,
                nation_values, "nation"),
            "annual_cash_identity": slot(value, "annual_cash_identity"),
            "customer_result_identity": slot(value, "customer_result_identity"),
            "evidence_classification": enum_value(
                slot(value, "evidence_classification"), evidence_type,
                ((qualified_estimate, "qualified_local_estimate"),),
                "evidence classification",
            ),
            "annual_liability": money(slot(value, "annual_liability"),
                "annual liability"),
            "obligations": obligations,
            "adjustments": adjustments,
            "funding": enum_value(slot(value, "funding"), funding_type,
                funding_values, "funding classification"),
            "funding_amount": funding_amount,
            "evidence_references": slot(value, "evidence_references"),
            "ruleset_version": slot(value, "ruleset_version"),
            "as_of": date_type.isoformat(as_of),
            "stale_after_days": horizon,
            "customer_result_limitations": slot(value,
                "customer_result_limitations"),
            "customer_result_prohibited_uses": slot(value,
                "customer_result_prohibited_uses"),
            "unresolved_inputs": slot(value, "unresolved_inputs"),
            "deletion_state": slot(value, "deletion_state"),
            "account_erasure_eligibility": slot(value,
                "account_erasure_eligibility"),
        }
        after = projection_identity(value)
        if before != after or slot(value, "annual_cash_identity_admitted") is not True:
            raise error("projection changed during adapter validation")
        require_unchanged_upstream()
        return before, fields, slot(value, "predecessor_identity")

    def make_from_fields(fields, predecessor_identity):
        return make_candidate(
            record_version=fields["record_version"],
            user_id=fields["user_id"],
            business_id=fields["business_id"],
            tax_year=fields["tax_year"],
            nation=fields["nation"],
            annual_cash_identity=fields["annual_cash_identity"],
            customer_result_identity=fields["customer_result_identity"],
            evidence_classification=fields["evidence_classification"],
            annual_liability=fields["annual_liability"],
            obligations=fields["obligations"],
            adjustments=fields["adjustments"],
            funding=fields["funding"],
            funding_amount=fields["funding_amount"],
            evidence_references=fields["evidence_references"],
            ruleset_version=fields["ruleset_version"],
            as_of=fields["as_of"],
            stale_after_days=fields["stale_after_days"],
            customer_result_limitations=fields["customer_result_limitations"],
            customer_result_prohibited_uses=fields[
                "customer_result_prohibited_uses"
            ],
            unresolved_inputs=fields["unresolved_inputs"],
            deletion_state=fields["deletion_state"],
            account_erasure_eligibility=fields["account_erasure_eligibility"],
            predecessor_identity=predecessor_identity,
        )

    def candidate_predecessor(candidate):
        candidate_identity(candidate)
        if typ(candidate) is not T or length(candidate) != 29:
            raise error("previous structural candidate has an invalid shape")
        pair = candidate[26]
        if typ(pair) is not T or pair[0] != "predecessor_identity":
            raise error("previous structural candidate predecessor is malformed")
        return pair[1]

    def pairs(values):
        return T(zip_fn(operation_fields, values, strict=True))

    def operation_map(value):
        if typ(value) is not T or length(value) != length(operation_fields):
            raise error("invalid adapter operation shape")
        out = {}
        for index, pair in enumerate_fn(value):
            if (
                typ(pair) is not T
                or length(pair) != 2
                or typ(pair[0]) is not S
                or pair[0] != operation_fields[index]
                or pair[0] in out
            ):
                raise error("invalid adapter operation field order")
            out[pair[0]] = pair[1]
        return out

    def canonical_source_projection_identity(candidate):
        """Reproduce S3A's content identity from the exact S3B primitives.

        S3A content identity excludes the predecessor link and ephemeral
        admission bit.  Everything else is present in the S3B candidate, so
        the provenance reference remains deterministically checkable after
        detachment without pretending that admission itself was transferred.
        """
        def enum(name, value):
            return {"__enum__": name + ":" + value}

        def decimal(value):
            return {"__decimal__": value}

        def day(value):
            return {"__date__": value}

        def obligation(item):
            return {
                "__dataclass__": "ObligationFact",
                "__fields__": {
                    "kind": enum("ObligationKind", item[0]),
                    "amount": decimal(item[1]),
                    "due_date": day(item[2]),
                },
            }

        def adjustment(item):
            return {
                "__dataclass__": "AdjustmentFact",
                "__fields__": {
                    "kind": enum("AdjustmentKind", item[0]),
                    "amount": decimal(item[1]),
                },
            }

        values = T(pair[1] for pair in candidate)
        canonical = (
            values[2],
            values[3],
            values[4],
            values[5],
            values[6],
            enum("SupportedNation", values[8]),
            values[7],
            values[9],
            values[10],
            enum("EvidenceClassification", values[11]),
            decimal(values[12]),
            T(obligation(item) for item in values[13]),
            T(adjustment(item) for item in values[14]),
            enum("FundingClassification", values[15]),
            None if values[16] is None else decimal(values[16]),
            T(values[17]),
            values[18],
            day(values[19]),
            values[20],
            T(values[21]),
            T(values[22]),
            T(values[23]),
            values[24],
            values[25],
        )
        payload = json_dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "annual-position-persistence:sha256-" + sha256(payload).hexdigest()

    def detach_primitive(value):
        """Rebuild an exact primitive graph without retaining caller tuples."""
        if typ(value) is T:
            return T(detach_primitive(item) for item in value)
        if typ(value) in (S, I, B) or value is None:
            return value
        raise error("adapter operation contains a non-exact primitive")

    def validate_projection_repository_adapter_operation(value):
        require_unchanged_upstream()
        m = operation_map(value)
        if (
            typ(m["adapter_version"]) is not S
            or m["adapter_version"] != adapter_version
            or typ(m["authority_status"]) is not S
            or m["authority_status"] != authority_status
            or typ(m["source_s3a_commit"]) is not S
            or m["source_s3a_commit"] != source_s3a_commit
            or typ(m["source_s3a_sha256"]) is not S
            or m["source_s3a_sha256"] != source_s3a_hash
            or typ(m["source_s3b_commit"]) is not S
            or m["source_s3b_commit"] != source_s3b_commit
            or typ(m["source_s3b_sha256"]) is not S
            or m["source_s3b_sha256"] != source_s3b_hash
            or typ(m["authenticated_user_id"]) is not S
            or typ(m["authenticated_business_id"]) is not S
            or typ(m["evaluated_on"]) is not S
        ):
            raise error("adapter operation source or owner boundary changed")
        if (
            typ(m["source_projection_identity"]) is not S
            or source_identity_rx.fullmatch(m["source_projection_identity"]) is None
        ):
            raise error("adapter operation source projection identity changed")
        try:
            parsed_evaluation = parse_date(m["evaluated_on"])
        except value_error as exc:
            raise error("adapter operation evaluation date changed") from exc
        if parsed_evaluation.isoformat() != m["evaluated_on"]:
            raise error("adapter operation evaluation date changed")
        candidate = m["structural_candidate"]
        actual_identity = candidate_identity(candidate)
        expected_source_identity = canonical_source_projection_identity(candidate)
        if m["source_projection_identity"] != expected_source_identity:
            raise error("adapter operation source projection identity is not reproducible")
        if (
            typ(m["structural_candidate_identity"]) is not S
            or typ(actual_identity) is not S
            or actual_identity != m["structural_candidate_identity"]
        ):
            raise error("adapter operation structural identity changed")
        if candidate[5][1] != m["authenticated_user_id"]:
            raise error("adapter operation crossed its owner boundary")
        if candidate[6][1] != m["authenticated_business_id"]:
            raise error("adapter operation crossed its business boundary")
        candidate_as_of = parse_date(candidate[19][1])
        candidate_horizon = candidate[20][1]
        if (
            parsed_evaluation < candidate_as_of
            or parsed_evaluation > candidate_as_of + delta_type(days=candidate_horizon)
        ):
            raise error("adapter operation evaluation is outside candidate freshness")
        record_version = candidate[4][1]
        previous_identity = m["source_predecessor_projection_identity"]
        previous_candidate = m["source_predecessor_structural_candidate"]
        if record_version == 1:
            if previous_identity is not None or previous_candidate is not None:
                raise error("initial adapter operation carried a predecessor")
        else:
            if (
                typ(previous_identity) is not S
                or source_identity_rx.fullmatch(previous_identity) is None
                or typ(previous_candidate) is not T
            ):
                raise error("successor adapter operation lost its source predecessor")
            previous_structural_identity = candidate_identity(previous_candidate)
            expected_previous_source_identity = canonical_source_projection_identity(
                previous_candidate
            )
            if previous_identity != expected_previous_source_identity:
                raise error("successor source predecessor identity is not reproducible")
            if candidate[26][1] != previous_structural_identity:
                raise error("successor structural predecessor identity is not reproducible")
            if previous_candidate[4][1] + 1 != record_version:
                raise error("successor adapter operation broke version progression")
            for index in (3, 5, 6, 7, 8):
                if previous_candidate[index][1] != candidate[index][1]:
                    raise error("successor adapter operation crossed its chain boundary")
        for name in operation_fields[14:]:
            if m[name] is not False:
                raise error("adapter operation asserted unavailable authority")
        require_unchanged_upstream()
        canonical_candidate = detach_primitive(candidate)
        canonical_values = (
            adapter_version,
            authority_status,
            source_s3a_commit,
            source_s3a_hash,
            source_s3b_commit,
            source_s3b_hash,
            expected_source_identity,
            None if previous_identity is None else S(previous_identity),
            None if previous_candidate is None else detach_primitive(previous_candidate),
            S(candidate[5][1]),
            S(candidate[6][1]),
            date_type.isoformat(parsed_evaluation),
            canonical_candidate,
            actual_identity,
            False, False, False, False, False, False, False, False, False,
            False, False, False,
        )
        return pairs(canonical_values)

    def extract_structural_candidate(value):
        m = operation_map(validate_projection_repository_adapter_operation(value))
        # Candidate validation above proves an exact immutable primitive graph.
        return detach_primitive(m["structural_candidate"])

    def adapt_admitted_projection_to_structural_candidate(*args, **kwargs):
        if args or typ(kwargs) is not D or length(kwargs) != length(input_fields):
            raise type_error("W9-S3C inputs must use the exact named call shape")
        if any_fn(typ(key) is not S for key in kwargs) or set_type(kwargs) != set_type(input_fields):
            raise type_error("W9-S3C inputs must use the exact named call shape")
        projection = kwargs["projection"]
        authenticated_user_id = kwargs["authenticated_user_id"]
        authenticated_business_id = kwargs["authenticated_business_id"]
        evaluated_on = kwargs["evaluated_on"]
        previous_projection = kwargs["previous_projection"]
        previous_candidate = kwargs["previous_structural_candidate"]

        identity, fields, source_predecessor = read_projection(
            projection,
            authenticated_user_id,
            authenticated_business_id,
            evaluated_on,
            require_fresh=True,
        )
        previous_identity = None
        structural_predecessor = None
        if fields["record_version"] == 1:
            if (
                source_predecessor is not None
                or previous_projection is not None
                or previous_candidate is not None
            ):
                raise error("initial projection cannot carry predecessor inputs")
        else:
            if previous_projection is None or previous_candidate is None:
                raise error("successor projection requires both predecessor inputs")
            previous_identity, previous_fields, previous_source_predecessor = read_projection(
                previous_projection,
                authenticated_user_id,
                authenticated_business_id,
                evaluated_on,
                require_fresh=False,
            )
            validate_chain(
                (previous_projection, projection),
                external_anchor=previous_source_predecessor,
            )
            expected_previous = make_from_fields(
                previous_fields,
                candidate_predecessor(previous_candidate),
            )
            if expected_previous != previous_candidate:
                raise error("previous S3B candidate does not match the S3A predecessor")
            structural_predecessor = candidate_identity(previous_candidate)
            if source_predecessor != previous_identity:
                raise error("S3A predecessor identity changed during adaptation")

        candidate = make_from_fields(fields, structural_predecessor)
        structural_identity = candidate_identity(candidate)
        values = (
            adapter_version, authority_status, source_s3a_commit, source_s3a_hash,
            source_s3b_commit, source_s3b_hash, identity, previous_identity,
            previous_candidate,
            authenticated_user_id, authenticated_business_id,
            date_type.isoformat(evaluated_on), candidate, structural_identity,
            False, False, False, False, False, False, False, False, False,
            False, False, False,
        )
        operation = pairs(values)
        require_unchanged_upstream()
        return validate_projection_repository_adapter_operation(operation)

    return (
        adapt_admitted_projection_to_structural_candidate,
        validate_projection_repository_adapter_operation,
        extract_structural_candidate,
    )


(
    adapt_admitted_projection_to_structural_candidate,
    validate_projection_repository_adapter_operation,
    extract_structural_candidate,
) = _build_adapter()
del _build_adapter


__all__ = [
    "ADAPTER_VERSION",
    "AUTHORITY_STATUS",
    "SOURCE_S3A_COMMIT",
    "SOURCE_S3A_SHA256",
    "SOURCE_S3B_COMMIT",
    "SOURCE_S3B_SHA256",
    "ProjectionRepositoryAdapterError",
    "adapt_admitted_projection_to_structural_candidate",
    "validate_projection_repository_adapter_operation",
    "extract_structural_candidate",
]
