"""Disabled-first, datastore-neutral W9-S3B structural repository contract.

No W9-S3A runtime object is imported or trusted. Only exact built-in primitive
structural candidates are accepted. They are always non-admitted and carry no
persistence, storage, production, migration, deletion or deployment authority.
The pinned S3A commit/hash are design provenance only; a later reviewed adapter
must authenticate genuine S3A output before durable persistence is considered.
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import re as _re
import weakref as _weakref
from datetime import date as _date

CONTRACT_VERSION = "reserved-annual-position-repository/1.0"
STRUCTURAL_CANDIDATE_VERSION = "reserved-annual-position-structural-candidate/1.0"
STRUCTURAL_STATUS = "structural_candidate_not_upstream_admitted"
SOURCE_S3A_COMMIT = "c489c25bab669c64e1c11d28caf29fcde9678fdd"
SOURCE_S3A_SHA256 = "da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469"
SOURCE_S3A_SCHEMA_VERSION = "reserved-annual-position-persistence/1.0"
SOURCE_RECORD_PURPOSE = "annual_cash_position_durable_projection"


class RepositoryContractError(ValueError):
    """Fail-closed structural-contract error."""


def _build():
    T, S, I, B, L, Set = tuple, str, int, bool, list, set
    typ, new, oid = type, object.__new__, id
    E, KE, VE = RepositoryContractError, KeyError, ValueError
    length, enum, any_, zip_ = len, enumerate, any, zip
    sha, dumps, rx = _hashlib.sha256, _json.dumps, _re.compile
    weak_values, weak_ref = _weakref.WeakValueDictionary, _weakref.ref
    parse_date = _date.fromisoformat
    contract, cv, status = CONTRACT_VERSION, STRUCTURAL_CANDIDATE_VERSION, STRUCTURAL_STATUS
    source_commit, source_hash = SOURCE_S3A_COMMIT, SOURCE_S3A_SHA256
    source_schema, purpose = SOURCE_S3A_SCHEMA_VERSION, SOURCE_RECORD_PURPOSE
    envelope_version = "reserved-annual-position-record-envelope/1.0"

    cfields = (
        "candidate_version", "authority_status", "source_schema_version",
        "record_purpose", "record_version", "user_id", "business_id", "tax_year",
        "nation", "annual_cash_identity", "customer_result_identity",
        "evidence_classification", "annual_liability", "obligations", "adjustments",
        "funding", "funding_amount", "evidence_references", "ruleset_version", "as_of",
        "stale_after_days", "customer_result_limitations",
        "customer_result_prohibited_uses", "unresolved_inputs", "deletion_state",
        "account_erasure_eligibility", "predecessor_identity",
        "annual_cash_identity_admitted", "persistence_authority",
    )
    gfields = (
        ("retention_policy_version", "retention:"),
        ("erasure_disposition", "erasure:"),
        ("crypto_key_version", "crypto:"),
        ("target_profile", "target:"),
    )
    rfields = (
        "repository_contract_version", "source_s3a_commit", "source_s3a_sha256",
        "record_identity",
    ) + cfields + tuple(name for name, _ in gfields)
    limitations = (
        "presentation_facts_only", "not_a_current_hmrc_bill", "surplus_not_available_cash",
    )
    prohibited = (
        "no_payment_or_transfer_authority", "self_assessment_filing", "financial_advice",
        "persistence_or_storage", "production_or_provider_activation",
    )
    unresolved = (
        "legal_basis_for_retention_unresolved", "retention_period_unresolved",
        "legal_hold_unresolved", "backup_expiry_unresolved",
        "datastore_selection_unresolved", "encryption_at_rest_unresolved",
        "encryption_key_custody_unresolved", "production_access_unresolved",
        "activation_unresolved",
    )
    nations = ("England", "Wales", "Northern Ireland")
    funding_values = ("gap", "exact", "surplus")
    obligation_kinds = (
        "balancing_payment", "first_payment_on_account", "second_payment_on_account",
    )
    adjustment_kinds = (
        "deductions_and_credits", "prior_payments_on_account", "payments_made",
        "credit_or_refund",
    )
    owner_rx = rx(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    ref_rx = rx(r"^[a-z][a-z0-9_-]{1,31}:[A-Za-z0-9][A-Za-z0-9._/-]{0,95}$")
    source_id_rx = rx(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
    digest_reference_rx = rx(r"^[a-z-]+:sha256-[0-9a-f]{64}$")
    tax_rx = rx(r"^([0-9]{4})/([0-9]{2})$")
    cash_rx = rx(r"^annual-to-cash-position:sha256-[0-9a-f]{64}$")
    result_rx = rx(r"^w8-customer-result:sha256-[0-9a-f]{64}$")
    identity_rx = rx(r"^annual-position-structural:sha256-[0-9a-f]{64}$")
    money_rx = rx(r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$")
    audit_rx = rx(r"^audit:[A-Za-z0-9][A-Za-z0-9._/-]{0,95}$")
    digest_rx = rx(r"^annual-position-record:sha256-[0-9a-f]{64}$")
    placeholders = ("pending", "unknown", "unresolved", "placeholder", "default", "tbd", "tbc")
    secrets = (
        "secret", "token", "password", "credential", "apikey", "api_key",
        "bearer", "private_key", "sk_live", "sk_test", "access_key",
    )

    def pairs(names, values):
        return T(zip_(names, values, strict=True))

    def mapping(value, names, subject):
        if typ(value) is not T or length(value) != length(names):
            raise E(f"invalid {subject} shape")
        out = {}
        for index, pair in enum(value):
            if (typ(pair) is not T or length(pair) != 2 or typ(pair[0]) is not S
                    or pair[0] != names[index] or pair[0] in out):
                raise E(f"invalid {subject} field order")
            out[pair[0]] = pair[1]
        return out

    def clone(value):
        if value is None or typ(value) in (S, I, B):
            return value
        if typ(value) is T:
            return T(clone(item) for item in value)
        raise E("repository contract contains a non-primitive value")

    def owner(value, subject):
        if typ(value) is not S or not owner_rx.fullmatch(value) or any_(x in value.casefold() for x in secrets):
            raise E(f"invalid {subject} reference")

    def gov_ref(value, prefix, subject):
        if typ(value) is not S or not ref_rx.fullmatch(value) or not value.casefold().startswith(prefix):
            raise E(f"invalid {subject} reference")
        lowered = value.casefold()
        if any_(x in lowered for x in placeholders):
            raise E(f"{subject} reference is unresolved")
        if any_(x in lowered for x in secrets):
            raise E(f"{subject} reference appears to contain secret material")

    def audit(value):
        if typ(value) is not S or not audit_rx.fullmatch(value):
            raise E("invalid redacted audit reference")
        if any_(x in value.casefold() for x in placeholders + secrets):
            raise E("audit reference is not safely redacted")
        return value

    def money(value, subject):
        if typ(value) is not S or not money_rx.fullmatch(value):
            raise E(f"invalid exact {subject} money")

    def iso_date(value, subject):
        if typ(value) is not S:
            raise E(f"invalid {subject} date")
        try:
            parsed = parse_date(value)
        except VE as exc:
            raise E(f"invalid {subject} date") from exc
        if parsed.isoformat() != value:
            raise E(f"invalid {subject} date")

    def structural_identity(candidate):
        data = dumps(candidate, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return "annual-position-structural:sha256-" + sha(data).hexdigest()

    def validate_candidate(value):
        candidate = clone(value)
        m = mapping(candidate, cfields, "structural candidate")
        if (m["candidate_version"] != cv or m["authority_status"] != status
                or m["source_schema_version"] != source_schema
                or m["record_purpose"] != purpose
                or m["annual_cash_identity_admitted"] is not False
                or m["persistence_authority"] is not False):
            raise E("structural candidate asserted unavailable upstream authority")
        version = m["record_version"]
        if typ(version) is not I or version < 1:
            raise E("invalid structural record version")
        owner(m["user_id"], "candidate owner")
        owner(m["business_id"], "candidate business")
        if m["user_id"] == m["business_id"]:
            raise E("candidate owner and business must remain distinct")
        tax = m["tax_year"] if typ(m["tax_year"]) is S else ""
        match = tax_rx.fullmatch(tax)
        if match is None or I(match.group(2)) != (I(match.group(1)) + 1) % 100:
            raise E("invalid structural tax year")
        if typ(m["nation"]) is not S or m["nation"] not in nations:
            raise E("invalid structural nation")
        if typ(m["annual_cash_identity"]) is not S or not cash_rx.fullmatch(m["annual_cash_identity"]):
            raise E("invalid detached annual-cash identity")
        if typ(m["customer_result_identity"]) is not S or not result_rx.fullmatch(m["customer_result_identity"]):
            raise E("invalid detached customer-result identity")
        if typ(m["evidence_classification"]) is not S or m["evidence_classification"] != "qualified_local_estimate":
            raise E("structural evidence classification must be a qualified local estimate")
        money(m["annual_liability"], "annual-liability")
        obligations = m["obligations"]
        if typ(obligations) is not T or not obligations:
            raise E("structural obligations are required")
        seen = Set()
        for item in obligations:
            if typ(item) is not T or length(item) != 3 or typ(item[0]) is not S or item[0] not in obligation_kinds or item[0] in seen:
                raise E("invalid structural obligation")
            seen.add(item[0]); money(item[1], "obligation"); iso_date(item[2], "obligation")
        adjustments = m["adjustments"]
        if typ(adjustments) is not T or not adjustments:
            raise E("structural adjustments are required")
        seen = Set()
        for item in adjustments:
            if typ(item) is not T or length(item) != 2 or typ(item[0]) is not S or item[0] not in adjustment_kinds or item[0] in seen:
                raise E("invalid structural adjustment")
            seen.add(item[0]); money(item[1], "adjustment")
        if typ(m["funding"]) is not S or m["funding"] not in funding_values:
            raise E("invalid structural funding classification")
        if m["funding"] == "exact":
            if m["funding_amount"] is not None:
                raise E("exact funding cannot carry a gap or surplus amount")
        else:
            money(m["funding_amount"], "funding")
            if m["funding_amount"] == "0.00":
                raise E("gap or surplus funding amount must be non-zero")
        refs = m["evidence_references"]
        if typ(refs) is not T or not refs or length(Set(refs)) != length(refs):
            raise E("invalid structural evidence references")
        if any_(
            typ(ref) is not S
            or not source_id_rx.fullmatch(ref)
            or digest_reference_rx.fullmatch(ref)
            or any_(marker in ref.casefold() for marker in secrets)
            for ref in refs
        ):
            raise E("invalid structural evidence reference")
        if typ(m["ruleset_version"]) is not S or not owner_rx.fullmatch(m["ruleset_version"]):
            raise E("invalid structural ruleset version")
        iso_date(m["as_of"], "as-of")
        if typ(m["stale_after_days"]) is not I or m["stale_after_days"] < 0:
            raise E("invalid structural staleness horizon")
        if m["customer_result_limitations"] != limitations or m["customer_result_prohibited_uses"] != prohibited:
            raise E("structural customer restrictions changed")
        if m["unresolved_inputs"] != unresolved:
            raise E("structural unresolved inputs changed")
        if m["deletion_state"] != "not_deleted" or m["account_erasure_eligibility"] != "unresolved":
            raise E("structural candidate asserted a deletion or erasure outcome")
        predecessor = m["predecessor_identity"]
        if version == 1:
            if predecessor is not None:
                raise E("initial structural candidate cannot have a predecessor")
        elif typ(predecessor) is not S or not identity_rx.fullmatch(predecessor):
            raise E("successor structural candidate requires a structural predecessor")
        return candidate, m

    def make_structural_candidate(*, record_version, user_id, business_id, tax_year, nation,
            annual_cash_identity, customer_result_identity, evidence_classification,
            annual_liability, obligations, adjustments, funding, funding_amount,
            evidence_references, ruleset_version, as_of, stale_after_days,
            customer_result_limitations=limitations, customer_result_prohibited_uses=prohibited,
            unresolved_inputs=unresolved, deletion_state="not_deleted",
            account_erasure_eligibility="unresolved", predecessor_identity=None):
        values = (
            cv, status, source_schema, purpose, record_version, user_id, business_id, tax_year,
            nation, annual_cash_identity, customer_result_identity, evidence_classification,
            annual_liability, obligations, adjustments, funding, funding_amount,
            evidence_references, ruleset_version, as_of, stale_after_days,
            customer_result_limitations, customer_result_prohibited_uses, unresolved_inputs,
            deletion_state, account_erasure_eligibility, predecessor_identity, False, False,
        )
        return validate_candidate(pairs(cfields, values))[0]

    def structural_candidate_identity(value):
        return structural_identity(validate_candidate(value)[0])

    def governance_gate(*, retention_policy_version=None, erasure_disposition=None,
            crypto_key_version=None, target_profile=None):
        values = (retention_policy_version, erasure_disposition, crypto_key_version, target_profile)
        missing, invalid = [], []
        for (name, prefix), value in zip_(gfields, values, strict=True):
            if value is None or (typ(value) is S and value == ""):
                missing.append(name); continue
            try: gov_ref(value, prefix, name)
            except E: invalid.append(name)
        return (
            ("status", "inputs_complete_contract_only" if not missing and not invalid else "blocked"),
            ("authority_status", status), ("missing", T(missing)), ("invalid", T(invalid)),
            ("persistence_authority", False), ("storage_authority", False),
            ("production_activation_authority", False),
        )

    class GovernanceInputsHandle:
        __slots__ = ("__weakref__",)
        def __new__(cls, token=None):
            if token is not gt: raise E("governance handles are producer-issued only")
            return new(cls)
        def __copy__(self): return copy_governance_inputs(self)
        def __deepcopy__(self, memo): return copy_governance_inputs(self)
        def __reduce__(self): raise E("governance handles are not serialisable")
        def __reduce_ex__(self, protocol): raise E("governance handles are not serialisable")

    class AnnualPositionRecordHandle:
        __slots__ = ("__weakref__",)
        def __new__(cls, token=None):
            if token is not rt: raise E("record handles are producer-issued only")
            return new(cls)
        def __copy__(self): return copy_annual_position_record(self)
        def __deepcopy__(self, memo): return copy_annual_position_record(self)
        def __reduce__(self): raise E("record handles are not serialisable")
        def __reduce_ex__(self, protocol): raise E("record handles are not serialisable")

    class RepositoryOperationPlanHandle:
        __slots__ = ("__weakref__",)
        def __new__(cls, token=None):
            if token is not ot: raise E("operation plans are producer-issued only")
            return new(cls)
        def __copy__(self): return issue_operation(operation_state(self))
        def __deepcopy__(self, memo): return issue_operation(operation_state(self))
        def __reduce__(self): raise E("operation plans are not serialisable")
        def __reduce_ex__(self, protocol): raise E("operation plans are not serialisable")

    class RepositoryReadHandle:
        __slots__ = ("__weakref__",)
        def __new__(cls, token=None):
            if token is not qt: raise E("read results are producer-issued only")
            return new(cls)
        def __copy__(self): return issue_read(read_state(self))
        def __deepcopy__(self, memo): return issue_read(read_state(self))
        def __reduce__(self): raise E("read results are not serialisable")
        def __reduce_ex__(self, protocol): raise E("read results are not serialisable")

    class DeletionPlanHandle:
        __slots__ = ("__weakref__",)
        def __new__(cls, token=None):
            if token is not dt: raise E("deletion plans are producer-issued only")
            return new(cls)
        def __copy__(self): return issue_deletion(deletion_state(self))
        def __deepcopy__(self, memo): return issue_deletion(deletion_state(self))
        def __reduce__(self): raise E("deletion plans are not serialisable")
        def __reduce_ex__(self, protocol): raise E("deletion plans are not serialisable")

    gt, rt, ot, qt, dt = (new(object) for _ in range(5))
    registries = [(dict(), weak_values(), dict()) for _ in range(5)]
    gs, gl, gr = registries[0]; rs, rl, rr = registries[1]
    os, ol, ore = registries[2]; qs, ql, qr = registries[3]; ds, dl, dr = registries[4]

    def issue(handle_type, states, live, refs, state):
        handle, identity = new(handle_type), None
        identity = oid(handle)
        def cleanup(reference):
            if refs.get(identity) is reference and reference() is None:
                refs.pop(identity, None); states.pop(identity, None); live.pop(identity, None)
        reference = weak_ref(handle, cleanup)
        states[identity], live[identity], refs[identity] = clone(state), handle, reference
        return handle

    def state(value, handle_type, states, live, message):
        if typ(value) is not handle_type: raise E(message)
        identity = oid(value)
        try: actual, stored = live[identity], states[identity]
        except KE as exc: raise E(message) from exc
        if actual is not value: raise E(message)
        return clone(stored)

    def issue_governance(value): return issue(GovernanceInputsHandle, gs, gl, gr, value)
    def governance_state(value): return state(value, GovernanceInputsHandle, gs, gl, "repository governance inputs are incomplete or untrusted")
    def bind_governance_inputs(*, retention_policy_version, erasure_disposition, crypto_key_version, target_profile):
        values = (retention_policy_version, erasure_disposition, crypto_key_version, target_profile)
        for (name, prefix), value in zip_(gfields, values, strict=True): gov_ref(value, prefix, name)
        return issue_governance(pairs(T(name for name, _ in gfields), values))
    def project_governance_inputs(value):
        return governance_state(value) + (("authority_status", status), ("persistence_authority", False), ("storage_authority", False), ("production_activation_authority", False))
    def copy_governance_inputs(value): return issue_governance(governance_state(value))
    def governance_map(value): return mapping(governance_state(value), T(name for name, _ in gfields), "governance input")

    def issue_record(value): return issue(AnnualPositionRecordHandle, rs, rl, rr, value)
    def record_state(value):
        value = state(value, AnnualPositionRecordHandle, rs, rl, "record handle is forged, stale or untrusted")
        validate_envelope(value, None); return value
    def copy_annual_position_record(value): return issue_record(record_state(value))

    def payload_digest(row, evidence):
        data = dumps((row, evidence), separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return "annual-position-record:sha256-" + sha(data).hexdigest()
    def envelope(row, evidence): return (envelope_version, payload_digest(row, evidence), row, evidence)

    def candidate_to_row(candidate, governance):
        candidate, cm = validate_candidate(candidate); gm = governance_map(governance)
        identity = structural_identity(candidate)
        values = (contract, source_commit, source_hash, identity)
        values += T(cm[name] for name in cfields) + T(gm[name] for name, _ in gfields)
        evidence = T((identity, n, cm["user_id"], cm["business_id"], ref) for n, ref in enum(cm["evidence_references"]))
        return pairs(rfields, values), evidence

    def validate_envelope(value, governance):
        if typ(value) is not T or length(value) != 4: raise E("invalid logical record envelope")
        version, digest, row, evidence = value
        if version != envelope_version: raise E("unknown logical record envelope schema")
        if typ(digest) is not S or not digest_rx.fullmatch(digest) or digest != payload_digest(row, evidence):
            raise E("logical record envelope was altered")
        rm = mapping(row, rfields, "logical annual-position row")
        if governance is not None:
            gm = governance_map(governance)
            if any_(rm[name] != gm[name] for name, _ in gfields): raise E("record governance profile does not match the supplied profile")
        if (rm["repository_contract_version"] != contract or rm["authority_status"] != status
                or rm["persistence_authority"] is not False or rm["source_s3a_commit"] != source_commit
                or rm["source_s3a_sha256"] != source_hash):
            raise E("record asserted unavailable persistence or provenance authority")
        candidate = pairs(cfields, T(rm[name] for name in cfields)); candidate, cm = validate_candidate(candidate)
        identity = structural_identity(candidate)
        if rm["record_identity"] != identity: raise E("logical record identity does not match exact structural facts")
        refs = []
        if typ(evidence) is not T or not evidence: raise E("logical evidence-reference rows are required")
        for n, item in enum(evidence):
            if (typ(item) is not T or length(item) != 5 or item[0] != identity
                    or typ(item[1]) is not I or item[1] != n or item[2] != cm["user_id"]
                    or item[3] != cm["business_id"] or typ(item[4]) is not S):
                raise E("invalid or cross-boundary evidence-reference row")
            refs.append(item[4])
        if T(refs) != cm["evidence_references"]: raise E("logical evidence rows do not match structural candidate")
        return rm, candidate

    def prepare_annual_position_record(candidate, governance):
        row, evidence = candidate_to_row(candidate, governance); value = envelope(row, evidence)
        validate_envelope(value, governance); return issue_record(value)
    def project_annual_position_record(value): return record_state(value)
    def repository_record_identity(value): return validate_envelope(record_state(value), None)[0]["record_identity"]
    def decode_annual_position_record(value, governance, audit_reference):
        audit(audit_reference); governance_state(governance); value = clone(value)
        validate_envelope(value, governance); return issue_record(value)
    def record_map(value, governance):
        governance_state(governance); env = record_state(value); return validate_envelope(env, governance)[0], env

    def logical_key(rm):
        return T(rm[name] for name in ("user_id", "business_id", "tax_year", "nation", "record_purpose", "record_version"))
    def issue_operation(value): return issue(RepositoryOperationPlanHandle, os, ol, ore, value)
    def operation_state(value): return state(value, RepositoryOperationPlanHandle, os, ol, "operation plan is forged, stale or untrusted")
    def project_operation_plan(value): return operation_state(value)

    def decide_initial_create(existing_records, candidate, governance, audit_reference):
        audit_value = audit(audit_reference); cm, ce = record_map(candidate, governance)
        if cm["record_version"] != 1 or cm["predecessor_identity"] is not None:
            raise E("initial creation requires a first structural candidate")
        if typ(existing_records) not in (T, L): raise E("existing record snapshot must be finite")
        matches, seen = [], Set()
        for existing in existing_records:
            em, ee = record_map(existing, governance); identity = em["record_identity"]
            if identity in seen: raise E("existing record snapshot contains a duplicate identity")
            seen.add(identity)
            if logical_key(em) == logical_key(cm): matches.append((em, ee))
        if length(matches) > 1: raise E("logical record key is not unique")
        if not matches: result = "insert_structural_candidate"
        else:
            em, ee = matches[0]
            if em["record_identity"] != cm["record_identity"]:
                raise E("logical record key conflicts with a different structural identity")
            if ee != ce: raise E("structural identity was reused with different repository metadata")
            result = "idempotent_existing"
        return issue_operation((
            ("authority_status", status), ("persistence_authority", False),
            ("operation", "initial_create"), ("status", result),
            ("logical_key", logical_key(cm)), ("record_identity", cm["record_identity"]),
            ("audit_reference", audit_value), ("database_write_performed", False),
            ("storage_authority", False),
        ))

    def prepare_supersession(current_record, successor_candidate, *, expected_record_version,
            governance, audit_reference):
        audit_value = audit(audit_reference); current, _ = record_map(current_record, governance)
        if typ(expected_record_version) is not I or expected_record_version < 1:
            raise E("invalid optimistic record version")
        if current["record_version"] != expected_record_version:
            raise E("optimistic record version is already stale")
        candidate = prepare_annual_position_record(successor_candidate, governance)
        cm, ce = record_map(candidate, governance)
        boundaries = ("user_id", "business_id", "tax_year", "nation", "record_purpose")
        if any_(cm[name] != current[name] for name in boundaries):
            raise E("supersession crossed an immutable owner or purpose boundary")
        if cm["record_version"] != expected_record_version + 1:
            raise E("supersession version did not advance exactly once")
        if cm["predecessor_identity"] != current["record_identity"]:
            raise E("supersession does not reference the exact current record")
        return issue_operation((
            ("authority_status", status), ("persistence_authority", False),
            ("operation", "supersession_cas"), ("status", "prepared"),
            ("expected_record_identity", current["record_identity"]),
            ("expected_record_version", expected_record_version), ("candidate_record", ce),
            ("audit_reference", audit_value), ("database_write_performed", False),
            ("storage_authority", False),
        ))

    def decide_supersession_cas(observed_current, prepared_plan, governance):
        fields = (
            "authority_status", "persistence_authority", "operation", "status",
            "expected_record_identity", "expected_record_version", "candidate_record",
            "audit_reference", "database_write_performed", "storage_authority",
        )
        current = operation_state(prepared_plan); cm = mapping(current, fields, "supersession plan")
        if (cm["authority_status"] != status or cm["persistence_authority"] is not False
                or cm["operation"] != "supersession_cas" or cm["status"] != "prepared"):
            raise E("CAS decision requires a structural prepared plan")
        observed, _ = record_map(observed_current, governance)
        validate_envelope(cm["candidate_record"], governance)
        result = "cas_apply_contract_only" if (
            observed["record_identity"] == cm["expected_record_identity"]
            and observed["record_version"] == cm["expected_record_version"]
        ) else "cas_conflict"
        return issue_operation(T((name, result if name == "status" else value) for name, value in current))

    def issue_read(value): return issue(RepositoryReadHandle, qs, ql, qr, value)
    def read_state(value): return state(value, RepositoryReadHandle, qs, ql, "read result is forged, stale or untrusted")
    def read_owned_record(records, *, requester_user_id, record_identity, governance, audit_reference):
        owner(requester_user_id, "requesting owner"); audit_value = audit(audit_reference)
        if typ(record_identity) is not S or not identity_rx.fullmatch(record_identity): raise E("record is unavailable")
        if typ(records) not in (T, L): raise E("record snapshot must be finite")
        matches = []
        for record in records:
            rm, env = record_map(record, governance)
            if rm["record_identity"] == record_identity: matches.append((rm, env))
        if length(matches) != 1 or matches[0][0]["user_id"] != requester_user_id: raise E("record is unavailable")
        return issue_read((
            ("authority_status", status), ("persistence_authority", False),
            ("status", "owner_read_contract_only"), ("requester_user_id", requester_user_id),
            ("record", matches[0][1]), ("audit_reference", audit_value),
            ("database_read_performed", False), ("storage_authority", False),
        ))
    def project_read_result(value): return read_state(value)
    def reconstruct_read_structural_candidate(value):
        fields = (
            "authority_status", "persistence_authority", "status", "requester_user_id",
            "record", "audit_reference", "database_read_performed", "storage_authority",
        )
        rm = mapping(read_state(value), fields, "read result")
        _, candidate = validate_envelope(rm["record"], None); cm = mapping(candidate, cfields, "structural candidate")
        if cm["user_id"] != rm["requester_user_id"]: raise E("read result crossed its owner boundary")
        if cm["annual_cash_identity_admitted"] is not False or cm["persistence_authority"] is not False:
            raise E("structural read asserted unavailable authority")
        return candidate

    def issue_deletion(value): return issue(DeletionPlanHandle, ds, dl, dr, value)
    def deletion_state(value): return state(value, DeletionPlanHandle, ds, dl, "deletion plan is forged, stale or untrusted")
    def plan_account_deletion(records, *, requester_user_id, requested_record_identities,
            governance, audit_reference):
        owner(requester_user_id, "requesting owner"); audit_value = audit(audit_reference)
        gm = governance_map(governance)
        if typ(records) not in (T, L): raise E("record snapshot must be finite")
        if typ(requested_record_identities) is not T: raise E("requested deletion identities must be a tuple")
        if length(Set(requested_record_identities)) != length(requested_record_identities):
            raise E("requested deletion identities contain duplicates")
        by_identity = {}
        for record in records:
            rm, env = record_map(record, governance); identity = rm["record_identity"]
            if identity in by_identity: raise E("record snapshot contains a duplicate identity")
            by_identity[identity] = (rm, env)
        selected, evidence_keys = [], []
        for identity in requested_record_identities:
            if typ(identity) is not S or not identity_rx.fullmatch(identity): raise E("record is unavailable for deletion planning")
            match = by_identity.get(identity)
            if match is None or match[0]["user_id"] != requester_user_id: raise E("record is unavailable for deletion planning")
            selected.append(identity)
            evidence_keys.extend((item[0], item[1]) for item in match[1][3])
        return issue_deletion((
            ("authority_status", status), ("persistence_authority", False),
            ("status", "deletion_planned_not_executed"), ("requester_user_id", requester_user_id),
            ("record_identities", T(selected)), ("evidence_row_keys", T(evidence_keys)),
            ("erasure_disposition", gm["erasure_disposition"]), ("audit_reference", audit_value),
            ("deletion_performed", False), ("backup_deletion_claimed", False),
            ("storage_authority", False),
        ))
    def project_deletion_plan(value): return deletion_state(value)

    for cls, name in (
        (GovernanceInputsHandle, "GovernanceInputsHandle"),
        (AnnualPositionRecordHandle, "AnnualPositionRecordHandle"),
        (RepositoryOperationPlanHandle, "RepositoryOperationPlanHandle"),
        (RepositoryReadHandle, "RepositoryReadHandle"),
        (DeletionPlanHandle, "DeletionPlanHandle"),
    ):
        cls.__module__, cls.__qualname__ = __name__, name

    return (
        GovernanceInputsHandle, AnnualPositionRecordHandle, RepositoryOperationPlanHandle,
        RepositoryReadHandle, DeletionPlanHandle, make_structural_candidate,
        structural_candidate_identity, governance_gate, bind_governance_inputs,
        project_governance_inputs, copy_governance_inputs, prepare_annual_position_record,
        project_annual_position_record, copy_annual_position_record,
        decode_annual_position_record, repository_record_identity, decide_initial_create,
        project_operation_plan, prepare_supersession, decide_supersession_cas,
        read_owned_record, project_read_result, reconstruct_read_structural_candidate,
        plan_account_deletion, project_deletion_plan,
    )


(
    GovernanceInputsHandle, AnnualPositionRecordHandle, RepositoryOperationPlanHandle,
    RepositoryReadHandle, DeletionPlanHandle, make_structural_candidate,
    structural_candidate_identity, governance_gate, bind_governance_inputs,
    project_governance_inputs, copy_governance_inputs, prepare_annual_position_record,
    project_annual_position_record, copy_annual_position_record,
    decode_annual_position_record, repository_record_identity, decide_initial_create,
    project_operation_plan, prepare_supersession, decide_supersession_cas,
    read_owned_record, project_read_result, reconstruct_read_structural_candidate,
    plan_account_deletion, project_deletion_plan,
) = _build()
del _build

__all__ = [
    "CONTRACT_VERSION", "STRUCTURAL_CANDIDATE_VERSION", "STRUCTURAL_STATUS",
    "SOURCE_S3A_COMMIT", "SOURCE_S3A_SHA256", "SOURCE_S3A_SCHEMA_VERSION",
    "SOURCE_RECORD_PURPOSE", "RepositoryContractError", "GovernanceInputsHandle",
    "AnnualPositionRecordHandle", "RepositoryOperationPlanHandle", "RepositoryReadHandle",
    "DeletionPlanHandle", "make_structural_candidate", "structural_candidate_identity",
    "governance_gate", "bind_governance_inputs", "project_governance_inputs",
    "copy_governance_inputs", "prepare_annual_position_record",
    "project_annual_position_record", "copy_annual_position_record",
    "decode_annual_position_record", "repository_record_identity", "decide_initial_create",
    "project_operation_plan", "prepare_supersession", "decide_supersession_cas",
    "read_owned_record", "project_read_result", "reconstruct_read_structural_candidate",
    "plan_account_deletion", "project_deletion_plan",
]
