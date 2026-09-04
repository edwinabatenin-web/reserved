"""Focused tests for the W10-S3D local transactional billing repository."""

from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
import subprocess
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import reserved.billing.contracts as contracts
import reserved.billing.local_billing_repository as subject
import reserved.billing.paid_access_guard as s5d
import reserved.billing.runtime_entitlement_admission as s3c


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
OWNER = "users:17"
ACCOUNT = "billing:17"
SUBSCRIPTION = "subscription:17"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64

FACT_KEYS = (
    "protocol_version",
    "fact_identity",
    "admission_status",
    "authenticated",
    "billing_fact_authority",
    "provider_observation_direct_authority",
    "owner_id",
    "billing_account_id",
    "subscription_id",
    "decision_sequence",
    "predecessor_fact_identity",
    "state",
    "valid_from_inclusive",
    "valid_until_exclusive",
    "transition_effective_at_utc",
    "recovery_deadline_exclusive_at_utc",
    "derivation_kind",
    "withdrawal_attribution",
)


def _repo_obs(**changes):
    values = dict(
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        plan_key="monthly",
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-1",
        source_event_digest=DIGEST_A,
        observation_kind="initial_payment_confirmed",
        effective_date=date(2026, 10, 1),
        paid_through=date(2026, 10, 31),
        evidence_reference="evidence/ref-1",
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="verified_initial_payment",
        withdrawal_attribution="not_applicable",
        expected_predecessor_identity=None,
        expected_sequence=1,
        recorded_at_utc=datetime(2026, 10, 1, 12, tzinfo=UTC),
    )
    values.update(changes)
    return values


def _make_repo(tmp_path, *, name="repo.db"):
    return subject.LocalBillingRepository.create(tmp_path / name)


def _append(repo, **changes):
    return repo.append_observation(**_repo_obs(**changes))


def _append_renewal(
    repo,
    predecessor,
    *,
    source_event_id,
    expected_sequence,
    effective_date,
    transition_effective_at_utc,
    valid_until_exclusive,
    paid_through,
):
    return _append(
        repo,
        source_event_id=source_event_id,
        source_event_digest=DIGEST_B,
        observation_kind="renewal_payment_confirmed",
        effective_date=effective_date,
        paid_through=paid_through,
        valid_until_exclusive=valid_until_exclusive,
        transition_effective_at_utc=transition_effective_at_utc,
        derivation_kind="verified_renewal_payment",
        expected_predecessor_identity=predecessor.content_identity,
        expected_sequence=expected_sequence,
    )


def _fact_identity(values):
    material = (
        values["protocol_version"],
        values["admission_status"],
        values["authenticated"],
        values["billing_fact_authority"],
        values["provider_observation_direct_authority"],
        values["owner_id"],
        values["billing_account_id"],
        values["subscription_id"],
        values["decision_sequence"],
        values["predecessor_fact_identity"],
        values["state"],
        values["valid_from_inclusive"].isoformat(),
        values["valid_until_exclusive"].isoformat(),
        values["transition_effective_at_utc"].isoformat(),
        (
            None
            if values["recovery_deadline_exclusive_at_utc"] is None
            else values["recovery_deadline_exclusive_at_utc"].isoformat()
        ),
        values["derivation_kind"],
        values["withdrawal_attribution"],
    )
    payload = json.dumps(material, ensure_ascii=True, separators=(",", ":"))
    return "billing-fact:sha256-" + hashlib.sha256(payload.encode("ascii")).hexdigest()


def _fact_view(record, *, decision_sequence, predecessor_fact_identity):
    values = {
        "protocol_version": s3c.BILLING_FACT_PROTOCOL_VERSION,
        "fact_identity": "",
        "admission_status": s3c.BILLING_FACT_ADMISSION_STATUS,
        "authenticated": True,
        "billing_fact_authority": True,
        "provider_observation_direct_authority": False,
        "owner_id": record.owner_id,
        "billing_account_id": record.billing_account_id,
        "subscription_id": record.subscription_id,
        "decision_sequence": decision_sequence,
        "predecessor_fact_identity": predecessor_fact_identity,
        "state": record.state,
        "valid_from_inclusive": record.valid_from_inclusive,
        "valid_until_exclusive": record.valid_until_exclusive,
        "transition_effective_at_utc": record.transition_effective_at_utc,
        "recovery_deadline_exclusive_at_utc": record.recovery_deadline_exclusive_at_utc,
        "derivation_kind": record.derivation_kind,
        "withdrawal_attribution": record.withdrawal_attribution,
    }
    values["fact_identity"] = _fact_identity(values)
    return tuple((key, values[key]) for key in FACT_KEYS)


def _test_only_authority():
    """Return a test-only synthetic trusted ingress (never ships in product)."""

    live = set()

    def issue(fact):
        live.add(id(fact))
        return fact

    def validate(value):
        if type(value) is not tuple or id(value) not in live:
            raise ValueError("not an admitted test-only billing fact")
        return value

    def project(value):
        if type(value) is not tuple or id(value) not in live:
            raise ValueError("not an admitted test-only billing fact")
        return value

    return issue, validate, project


def _bind_guard():
    return s5d.bind_paid_access_guard(
        validate_runtime_entitlement=s3c.validate_runtime_entitlement,
        project_runtime_entitlement=s3c.project_runtime_entitlement,
    )


def _s5d_decision(guard, prior, current, *, at):
    decision = s5d.evaluate_paid_access(
        guard,
        endpoint="v2.index",
        authenticated_owner_id=OWNER,
        prior_runtime_entitlement=prior,
        current_runtime_entitlement=current,
        evaluated_at_utc=at,
    )
    return dict(s5d.validate_paid_access_decision(decision))


# --- 1. durability ----------------------------------------------------------

def test_close_reopen_preserves_journal_head_and_dispositions(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    repo.close()

    reopened = subject.LocalBillingRepository.open(path)
    head = reopened.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert head.sequence == 1
    assert head.head_identity == first.content_identity
    assert head.state == "paid"
    journal = reopened.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert len(journal) == 1
    assert journal[0].content_identity == first.content_identity
    reopened.close()


def test_independent_process_reads_and_writes_same_file(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    repo.close()

    script = (
        "import sys\n"
        "from datetime import date, datetime, timezone\n"
        "from pathlib import Path\n"
        "import reserved.billing.local_billing_repository as r\n"
        "path = Path(sys.argv[1])\n"
        "pred = sys.argv[2] if sys.argv[2] != 'NONE' else None\n"
        "seq = int(sys.argv[3])\n"
        "repo = r.LocalBillingRepository.open(path)\n"
        "repo.append_observation(\n"
        "  owner_id='users:17', billing_account_id='billing:17', subscription_id='subscription:17',\n"
        "  plan_key='monthly', source_namespace='stripe-subscription/test-scope', source_event_id='evt-proc-2',\n"
        "  source_event_digest='sha256:' + 'c'*64,\n"
        "  observation_kind='renewal_payment_confirmed',\n"
        "  effective_date=date(2026,11,1), paid_through=date(2026,11,30),\n"
        "  evidence_reference='evidence/proc-2', state='paid',\n"
        "  valid_from_inclusive=date(2026,10,1), valid_until_exclusive=date(2026,12,1),\n"
        "  transition_effective_at_utc=datetime(2026,11,1,tzinfo=timezone.utc),\n"
        "  recovery_deadline_exclusive_at_utc=None,\n"
        "  derivation_kind='verified_renewal_payment', withdrawal_attribution='not_applicable',\n"
        "  expected_predecessor_identity=pred, expected_sequence=seq,\n"
        "  recorded_at_utc=datetime(2026,11,1,12,tzinfo=timezone.utc),\n"
        ")\n"
        "print(repo.current_head(owner_id='users:17', billing_account_id='billing:17', subscription_id='subscription:17').sequence)\n"
        "repo.close()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(path), first.content_identity, "2"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "2"

    reopened = subject.LocalBillingRepository.open(path)
    journal = reopened.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert [record.sequence for record in journal] == [1, 2]
    reopened.close()


# --- 2. isolation and identifier/type rejection -----------------------------

def test_owner_account_subscription_isolation(tmp_path):
    repo = _make_repo(tmp_path)
    _append(repo)
    _append(
        repo,
        owner_id="users:99",
        billing_account_id="billing:99",
        subscription_id="subscription:99",
        source_event_id="evt-other",
    )
    assert len(
        repo.journal(owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION)
    ) == 1
    assert len(
        repo.journal(
            owner_id="users:99",
            billing_account_id="billing:99",
            subscription_id="subscription:99",
        )
    ) == 1
    assert (
        repo.current_head(
            owner_id="users:99",
            billing_account_id="billing:99",
            subscription_id="subscription:99",
        ).sequence
        == 1
    )


@pytest.mark.parametrize("bad", ["", "not valid!", "x" * 161, "sk_live_123"])
def test_invalid_owner_identifiers_rejected(tmp_path, bad):
    repo = _make_repo(tmp_path)
    with pytest.raises(subject.LocalBillingRepositoryError):
        _append(repo, owner_id=bad)


@pytest.mark.parametrize("bad", ["weekly", "annual", "MONTHLY", "monthly "])
def test_invalid_plan_key_rejected(tmp_path, bad):
    repo = _make_repo(tmp_path)
    with pytest.raises(subject.LocalBillingRepositoryError):
        _append(repo, plan_key=bad)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("source_event_digest", "not-a-digest"),
        ("observation_kind", "provider_says_paid"),
        ("state", "active"),
        ("derivation_kind", "provider_status"),
        ("withdrawal_attribution", "maybe"),
        ("valid_from_inclusive", datetime(2026, 10, 1)),
        ("transition_effective_at_utc", datetime(2026, 10, 1)),
        ("expected_sequence", "1"),
    ),
)
def test_invalid_enum_and_type_values_rejected(tmp_path, field, value):
    repo = _make_repo(tmp_path)
    with pytest.raises(subject.LocalBillingRepositoryError):
        _append(repo, **{field: value})


def test_plan_keys_match_exact_settled_catalogue():
    assert subject.PLAN_KEYS == {key.value for key in contracts.PlanKey}


# --- 3. duplicates, conflicts, stale/out-of-order ---------------------------

def test_exact_duplicate_is_idempotent(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append(repo)
    assert first.content_identity == second.content_identity
    assert len(
        repo.journal(owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION)
    ) == 1
    assert (
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        ).sequence
        == 1
    )


def test_reused_identity_with_different_content_quarantines_and_does_not_advance(tmp_path):
    repo = _make_repo(tmp_path)
    _append(repo)
    with pytest.raises(subject.LocalBillingRepositoryError, match="quarantined"):
        _append(repo, source_event_digest=DIGEST_B)
    assert len(
        repo.journal(owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION)
    ) == 1
    assert (
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        ).sequence
        == 1
    )
    dispositions = repo.reconciliation_dispositions(
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-1",
    )
    assert len(dispositions) == 1
    assert dispositions[0].kind == "quarantined_reused_source_identity"


def test_stale_out_of_order_and_forked_successors_fail_closed(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo)
    with pytest.raises(subject.LocalBillingRepositoryError, match="stale|forked"):
        _append(
            repo,
            source_event_id="evt-2",
            observation_kind="renewal_payment_confirmed",
            effective_date=date(2026, 11, 1),
            paid_through=date(2026, 11, 30),
            valid_until_exclusive=date(2026, 12, 1),
            transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
            derivation_kind="verified_renewal_payment",
            expected_predecessor_identity=first.content_identity,
            expected_sequence=3,
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="stale|forked"):
        _append(
            repo,
            source_event_id="evt-3",
            expected_predecessor_identity="billing-journal:sha256-" + "0" * 64,
            expected_sequence=2,
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="originless"):
        _append(repo, source_event_id="evt-4", expected_sequence=1)
    assert (
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        ).head_identity
        == first.content_identity
    )


# --- 4. two competing processes --------------------------------------------

def test_two_competing_processes_at_most_one_advances_predecessor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    repo.close()

    script = (
        "import sys\n"
        "from datetime import date, datetime, timezone\n"
        "from pathlib import Path\n"
        "import reserved.billing.local_billing_repository as r\n"
        "path = Path(sys.argv[1])\n"
        "pred = sys.argv[2]\n"
        "event_id = sys.argv[3]\n"
        "repo = r.LocalBillingRepository.open(path)\n"
        "try:\n"
        "  repo.append_observation(\n"
        "    owner_id='users:17', billing_account_id='billing:17', subscription_id='subscription:17',\n"
        "    plan_key='monthly', source_namespace='stripe-subscription/test-scope', source_event_id=event_id,\n"
        "    source_event_digest='sha256:' + 'd'*64,\n"
        "    observation_kind='renewal_payment_confirmed',\n"
        "    effective_date=date(2026,11,1), paid_through=date(2026,11,30),\n"
        "    evidence_reference='evidence/' + event_id, state='paid',\n"
        "    valid_from_inclusive=date(2026,10,1), valid_until_exclusive=date(2026,12,1),\n"
        "    transition_effective_at_utc=datetime(2026,11,1,tzinfo=timezone.utc),\n"
        "    recovery_deadline_exclusive_at_utc=None,\n"
        "    derivation_kind='verified_renewal_payment', withdrawal_attribution='not_applicable',\n"
        "    expected_predecessor_identity=pred, expected_sequence=2,\n"
        "    recorded_at_utc=datetime(2026,11,1,12,tzinfo=timezone.utc),\n"
        "  )\n"
        "  print('SUCCESS')\n"
        "except r.LocalBillingRepositoryError:\n"
        "  print('FAIL')\n"
        "finally:\n"
        "  repo.close()\n"
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(path), first.content_identity, f"evt-win-{index}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in (1, 2)
    ]
    outcomes = []
    for proc in procs:
        out, err = proc.communicate(timeout=60)
        assert proc.returncode == 0, err
        outcomes.append(out.strip())
    assert outcomes.count("SUCCESS") == 1
    assert outcomes.count("FAIL") == 1

    reopened = subject.LocalBillingRepository.open(path)
    head = reopened.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert head.sequence == 2
    assert len(
        reopened.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    ) == 2
    reopened.close()


# --- 5. atomic rollback -----------------------------------------------------

def test_mid_transaction_failure_rolls_back_journal_and_head(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    raw = sqlite3.connect(str(path), isolation_level=None)
    raw.execute(
        "CREATE TRIGGER force_head_failure BEFORE INSERT ON subscription_head "
        "BEGIN SELECT RAISE(ABORT, 'forced head failure'); END;"
    )
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError):
        _append(repo)

    assert (
        len(
            repo.journal(
                owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
            )
        )
        == 0
    )
    assert (
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
        is None
    )


# --- 6. schema and lock/transaction errors ----------------------------------

def test_open_missing_repository_fails_closed(tmp_path):
    with pytest.raises(subject.LocalBillingRepositoryError):
        subject.LocalBillingRepository.open(tmp_path / "missing.db")


def test_open_corrupt_file_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    path.write_bytes(b"this is not a sqlite database at all" * 8)
    with pytest.raises(subject.LocalBillingRepositoryError):
        subject.LocalBillingRepository.open(path)


def test_open_unsupported_schema_version_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute(
        "UPDATE repository_meta SET value = 'future-version' WHERE key = 'schema_version'"
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="unsupported"):
        subject.LocalBillingRepository.open(path)


def test_open_partial_schema_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute("DROP TABLE subscription_head")
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="missing table"):
        subject.LocalBillingRepository.open(path)


def test_open_altered_schema_digest_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute(
        "UPDATE repository_meta SET value = '0' * 64 WHERE key = 'schema_digest'"
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="digest"):
        subject.LocalBillingRepository.open(path)


def test_locked_repository_fails_closed_with_bounded_error(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    repo = subject.LocalBillingRepository.open(path, busy_timeout_seconds=0.2)
    raw = sqlite3.connect(str(path), isolation_level=None)
    raw.execute("BEGIN EXCLUSIVE")
    try:
        with pytest.raises(subject.LocalBillingRepositoryError, match="locked"):
            _append(repo)
    finally:
        raw.execute("ROLLBACK")
        raw.close()
        repo.close()


def test_unsafe_path_forms_and_symlinks_rejected(tmp_path):
    with pytest.raises((TypeError, subject.LocalBillingRepositoryError)):
        subject.LocalBillingRepository.create(123)
    with pytest.raises(subject.LocalBillingRepositoryError):
        subject.LocalBillingRepository.create(":memory:")
    with pytest.raises(subject.LocalBillingRepositoryError):
        subject.LocalBillingRepository.create("file:whatever?mode=ro")
    target = tmp_path / "target.db"
    target.write_bytes(b"x")
    link = tmp_path / "link.db"
    link.symlink_to(target)
    with pytest.raises(subject.LocalBillingRepositoryError):
        subject.LocalBillingRepository.open(link)


# --- 7 & 8. synthetic composition (test-only trusted ingress) ----------------

def test_composition_initial_payment_recovery_and_expiry(tmp_path):
    repo = _make_repo(tmp_path)
    issue, validate, project = _test_only_authority()
    binding = s3c.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
    )
    guard = _bind_guard()

    # Initial payment establishes the first paid decision.
    initial_record = _append(repo)
    initial_fact = _fact_view(
        initial_record, decision_sequence=1, predecessor_fact_identity=None
    )
    initial_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=None,
        admitted_billing_fact=issue(initial_fact),
        evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    decision = _s5d_decision(
        guard, None, initial_runtime, at=datetime(2026, 10, 15, 12, tzinfo=UTC)
    )
    assert decision["allowed"] is True
    assert decision["reason"] == "allowed_initial_payment"

    # A verified renewal failure opens exactly one seven-day recovery window.
    recovery_record = _append(
        repo,
        source_event_id="evt-recovery-failure",
        observation_kind="renewal_payment_failed",
        effective_date=date(2026, 11, 1),
        paid_through=None,
        state="payment_recovery",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 8),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=datetime(2026, 11, 8, tzinfo=UTC),
        derivation_kind="verified_renewal_failure",
        expected_predecessor_identity=initial_record.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 11, 1, 12, tzinfo=UTC),
    )
    recovery_fact = _fact_view(
        recovery_record,
        decision_sequence=2,
        predecessor_fact_identity=dict(initial_fact)["fact_identity"],
    )
    recovery_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=initial_runtime,
        admitted_billing_fact=issue(recovery_fact),
        evaluated_at_utc=datetime(2026, 11, 3, 12, tzinfo=UTC),
    )
    decision = _s5d_decision(
        guard,
        initial_runtime,
        recovery_runtime,
        at=datetime(2026, 11, 3, 12, tzinfo=UTC),
    )
    assert decision["allowed"] is True
    assert decision["reason"] == "allowed_payment_recovery"

    # Expiry at the recovery deadline denies ordinary access (stale fact).
    decision = _s5d_decision(
        guard,
        initial_runtime,
        recovery_runtime,
        at=datetime(2026, 11, 8, 0, tzinfo=UTC),
    )
    assert decision["allowed"] is False
    assert decision["reason"] == "runtime_entitlement_stale"


def test_composition_repeated_failure_cannot_extend_recovery(tmp_path):
    repo = _make_repo(tmp_path)
    issue, validate, project = _test_only_authority()
    binding = s3c.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
    )

    initial_record = _append(repo)
    initial_fact = _fact_view(
        initial_record, decision_sequence=1, predecessor_fact_identity=None
    )
    initial_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=None,
        admitted_billing_fact=issue(initial_fact),
        evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    recovery_record = _append(
        repo,
        source_event_id="evt-recovery-failure",
        observation_kind="renewal_payment_failed",
        effective_date=date(2026, 11, 1),
        paid_through=None,
        state="payment_recovery",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 8),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=datetime(2026, 11, 8, tzinfo=UTC),
        derivation_kind="verified_renewal_failure",
        expected_predecessor_identity=initial_record.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 11, 1, 12, tzinfo=UTC),
    )
    recovery_fact = _fact_view(
        recovery_record,
        decision_sequence=2,
        predecessor_fact_identity=dict(initial_fact)["fact_identity"],
    )
    recovery_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=initial_runtime,
        admitted_billing_fact=issue(recovery_fact),
        evaluated_at_utc=datetime(2026, 11, 3, 12, tzinfo=UTC),
    )

    # A second, distinct failure on a later day must not extend the deadline.
    repeat_record = _append(
        repo,
        source_event_id="evt-repeated-failure",
        observation_kind="renewal_payment_failed",
        effective_date=date(2026, 11, 3),
        paid_through=None,
        state="payment_recovery",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 10),
        transition_effective_at_utc=datetime(2026, 11, 3, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=datetime(2026, 11, 10, tzinfo=UTC),
        derivation_kind="verified_renewal_failure",
        expected_predecessor_identity=recovery_record.content_identity,
        expected_sequence=3,
        recorded_at_utc=datetime(2026, 11, 3, 12, tzinfo=UTC),
    )
    repeat_fact = _fact_view(
        repeat_record,
        decision_sequence=3,
        predecessor_fact_identity=dict(recovery_fact)["fact_identity"],
    )
    with pytest.raises(s3c.RuntimeEntitlementAdmissionError):
        s3c.admit_runtime_entitlement(
            binding,
            authenticated_owner_id=OWNER,
            billing_account_id=ACCOUNT,
            subscription_id=SUBSCRIPTION,
            prior_runtime_entitlement=recovery_runtime,
            admitted_billing_fact=issue(repeat_fact),
            evaluated_at_utc=datetime(2026, 11, 4, 12, tzinfo=UTC),
        )


def test_composition_full_withdrawal_and_only_authorised_restoration(tmp_path):
    repo = _make_repo(tmp_path)
    issue, validate, project = _test_only_authority()
    binding = s3c.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
    )
    guard = _bind_guard()

    initial_record = _append(repo)
    initial_fact = _fact_view(
        initial_record, decision_sequence=1, predecessor_fact_identity=None
    )
    initial_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=None,
        admitted_billing_fact=issue(initial_fact),
        evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )

    withdrawal_record = _append(
        repo,
        source_event_id="evt-withdrawal",
        observation_kind="unknown",
        effective_date=date(2026, 10, 15),
        paid_through=None,
        state="suspended",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 15, tzinfo=UTC),
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
        expected_predecessor_identity=initial_record.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    withdrawal_fact = _fact_view(
        withdrawal_record,
        decision_sequence=2,
        predecessor_fact_identity=dict(initial_fact)["fact_identity"],
    )
    suspended_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=initial_runtime,
        admitted_billing_fact=issue(withdrawal_fact),
        evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    decision = _s5d_decision(
        guard,
        initial_runtime,
        suspended_runtime,
        at=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    assert decision["allowed"] is False
    assert decision["reason"] == "verified_full_current_period_withdrawal"

    # Restoration is admitted only from the verified withdrawal lineage.
    restoration_record = _append(
        repo,
        source_event_id="evt-replacement-payment",
        observation_kind="renewal_payment_confirmed",
        effective_date=date(2026, 10, 16),
        paid_through=date(2026, 10, 31),
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 16, tzinfo=UTC),
        derivation_kind="verified_replacement_payment",
        withdrawal_attribution="not_applicable",
        expected_predecessor_identity=withdrawal_record.content_identity,
        expected_sequence=3,
        recorded_at_utc=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    restoration_fact = _fact_view(
        restoration_record,
        decision_sequence=3,
        predecessor_fact_identity=dict(withdrawal_fact)["fact_identity"],
    )
    restored_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=suspended_runtime,
        admitted_billing_fact=issue(restoration_fact),
        evaluated_at_utc=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    decision = _s5d_decision(
        guard,
        suspended_runtime,
        restored_runtime,
        at=datetime(2026, 10, 16, 12, tzinfo=UTC),
    )
    assert decision["allowed"] is True
    assert decision["reason"] == "allowed_verified_replacement_payment"


def test_composition_ambiguous_withdrawal_preserves_valid_access(tmp_path):
    repo = _make_repo(tmp_path)
    issue, validate, project = _test_only_authority()
    binding = s3c.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
    )
    guard = _bind_guard()

    initial_record = _append(repo)
    initial_fact = _fact_view(
        initial_record, decision_sequence=1, predecessor_fact_identity=None
    )
    initial_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=None,
        admitted_billing_fact=issue(initial_fact),
        evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )

    ambiguous_record = _append(
        repo,
        source_event_id="evt-ambiguous-withdrawal",
        observation_kind="unknown",
        effective_date=date(2026, 10, 15),
        paid_through=None,
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 15, tzinfo=UTC),
        derivation_kind="withdrawal_ambiguous",
        withdrawal_attribution="unknown",
        expected_predecessor_identity=initial_record.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    ambiguous_fact = _fact_view(
        ambiguous_record,
        decision_sequence=2,
        predecessor_fact_identity=dict(initial_fact)["fact_identity"],
    )
    ambiguous_runtime = s3c.admit_runtime_entitlement(
        binding,
        authenticated_owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        prior_runtime_entitlement=initial_runtime,
        admitted_billing_fact=issue(ambiguous_fact),
        evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    decision = _s5d_decision(
        guard,
        initial_runtime,
        ambiguous_runtime,
        at=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    assert decision["allowed"] is True
    assert decision["reason"] == "allowed_preserved_withdrawal_uncertainty"
    # Ambiguous evidence must not create or extend entitlement.
    assert dict(s3c.project_runtime_entitlement(ambiguous_runtime))[
        "valid_until_exclusive"
    ] == date(2026, 11, 1)


def test_rehydrated_structural_rows_alone_fail_runtime_admission(tmp_path):
    repo = _make_repo(tmp_path)
    record = _append(repo)
    # A structural JournalRecord is not a billing fact and cannot be admitted.
    binding = s3c.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=lambda value: value,
        project_admitted_billing_fact=lambda value: value,
    )
    with pytest.raises(s3c.RuntimeEntitlementAdmissionError):
        s3c.admit_runtime_entitlement(
            binding,
            authenticated_owner_id=OWNER,
            billing_account_id=ACCOUNT,
            subscription_id=SUBSCRIPTION,
            prior_runtime_entitlement=None,
            admitted_billing_fact=record,
            evaluated_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
        )


def test_no_raw_payload_or_secret_retention(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    with pytest.raises(subject.LocalBillingRepositoryError):
        _append(repo, source_event_id="sk_live_secret_value")
    repo.close()

    raw = sqlite3.connect(str(path))
    columns = {
        row[1]
        for row in raw.execute("PRAGMA table_info(billing_journal)").fetchall()
    }
    raw.close()
    for forbidden in ("raw_payload", "provider_payload", "signature", "secret", "token"):
        assert not any(forbidden in column for column in columns)


# --- 9. no application mutation / routing / credentials ---------------------

def test_module_has_no_io_provider_route_config_auth_session_or_database_surface():
    tree = ast.parse((ROOT / "reserved/billing/local_billing_repository.py").read_text())
    imports = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imports |= {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {
        "__future__",
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "re",
        "sqlite3",
        "pathlib",
    }
    text = (ROOT / "reserved/billing/local_billing_repository.py").read_text()
    for forbidden in (
        "create_app",
        "register_blueprint",
        "app.route",
        "requests",
        "urllib",
        "DEFAULT_PATH",
        "DATABASE_PATH",
    ):
        assert forbidden not in text
    assert set(subject.__all__) == {
        "CONTRACT_VERSION",
        "DERIVATION_KINDS",
        "FACT_STATES",
        "JournalRecord",
        "LocalBillingRepository",
        "LocalBillingRepositoryError",
        "OBSERVATION_KINDS",
        "PLAN_KEYS",
        "RECONCILIATION_DISPOSITION_KINDS",
        "RECONCILIATION_DISPOSITION_REASONS",
        "RECORD_CLASSIFICATION",
        "REPOSITORY_PURPOSE",
        "SCHEMA_VERSION",
        "SubscriptionHeadRecord",
        "ReconciliationDispositionRecord",
        "WITHDRAWAL_ATTRIBUTIONS",
    }


def test_import_creates_no_default_database_or_files(tmp_path):
    script = "import reserved.billing.local_billing_repository as r; print(r.SCHEMA_VERSION)"
    env = {"PYTHONPATH": str(ROOT)}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(tmp_path),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == subject.SCHEMA_VERSION
    assert list(tmp_path.iterdir()) == []


# --- 10. focused correction regressions (six independent findings) ------------

OWNER2 = "users:99"
ACCOUNT2 = "billing:99"
SUBSCRIPTION2 = "subscription:99"


def _append_disposition(repo, *, disposition_id, owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION, source_namespace="stripe-subscription/test-scope", source_event_id="evt-disposition", kind="pending_reconciliation", evidence_reference="evidence/disposition-ref", reason=None, recorded_at_utc=datetime(2026, 10, 1, 12, tzinfo=UTC)):
    return repo.append_reconciliation_disposition(
        disposition_id=disposition_id,
        owner_id=owner_id,
        billing_account_id=billing_account_id,
        subscription_id=subscription_id,
        source_namespace=source_namespace,
        source_event_id=source_event_id,
        kind=kind,
        evidence_reference=evidence_reference,
        reason=reason,
        recorded_at_utc=recorded_at_utc,
    )


# Finding 1: disposition reason is an exact bounded vocabulary, never free text.
def test_bounded_reason_vocabulary_rejects_arbitrary_and_secret_shaped_text(tmp_path):
    repo = _make_repo(tmp_path)
    for bad in (
        "Bearer synthetic_credential_do_not_retain",
        "free form arbitrary log text",
        "x" * 240,
    ):
        with pytest.raises(subject.LocalBillingRepositoryError, match="reason"):
            _append_disposition(
                repo,
                disposition_id="disposition:users17:bad-reason",
                reason=bad,
            )
    # A valid bounded reason persists exactly across close/reopen.
    rec = _append_disposition(
        repo,
        disposition_id="disposition:users17:valid-reason",
        reason="pending reconciliation",
    )
    assert rec.reason == "pending reconciliation"
    repo.close()
    reopened = subject.LocalBillingRepository.open(tmp_path / "repo.db")
    dispositions = reopened.reconciliation_dispositions(
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-disposition",
    )
    reopened.close()
    assert [d.reason for d in dispositions] == ["pending reconciliation"]


# Finding 2: required index/PK/executable structure is validated, not the digest.
def test_open_with_dropped_unique_index_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute("DROP INDEX billing_journal_source_identity_unique")
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="index"):
        subject.LocalBillingRepository.open(path)


# Finding 2 (residual v2): partial-index flag/predicate is rejected, not ignored.
def test_open_with_partial_unique_index_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute("DROP INDEX billing_journal_source_identity_unique")
    raw.execute(
        "CREATE UNIQUE INDEX billing_journal_source_identity_unique "
        "ON billing_journal (source_namespace, source_event_id) WHERE sequence < 0"
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="index"):
        subject.LocalBillingRepository.open(path)


def test_open_with_partial_unique_index_any_predicate_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute("DROP INDEX billing_journal_source_identity_unique")
    raw.execute(
        "CREATE UNIQUE INDEX billing_journal_source_identity_unique "
        "ON billing_journal (source_namespace, source_event_id) WHERE 1"
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="index"):
        subject.LocalBillingRepository.open(path)


def test_open_after_recreating_identical_non_partial_index_succeeds(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute("DROP INDEX billing_journal_source_identity_unique")
    raw.execute(
        "CREATE UNIQUE INDEX billing_journal_source_identity_unique "
        "ON billing_journal (source_namespace, source_event_id)"
    )
    raw.commit()
    raw.close()
    reopened = subject.LocalBillingRepository.open(path)
    assert reopened.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    ) is None
    reopened.close()


def test_open_with_extra_table_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute("CREATE TABLE unauthorised_extra (id INTEGER PRIMARY KEY)")
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="table"):
        subject.LocalBillingRepository.open(path)


def test_open_with_executable_trigger_fails_closed(tmp_path):
    path = tmp_path / "repo.db"
    _make_repo(tmp_path).close()
    raw = sqlite3.connect(str(path))
    raw.execute(
        "CREATE TRIGGER unauthorised_trigger AFTER INSERT ON billing_journal "
        "BEGIN SELECT 1; END"
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="executable"):
        subject.LocalBillingRepository.open(path)


# Finding 3: bind catalogue/plan and reject temporal regression for successors.
def test_append_rejects_plan_change_without_policy(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo)
    with pytest.raises(subject.LocalBillingRepositoryError, match="plan"):
        _append(
            repo,
            plan_key="yearly",
            source_event_id="evt-yearly",
            source_event_digest=DIGEST_B,
            expected_predecessor_identity=first.content_identity,
            expected_sequence=2,
        )


def test_append_rejects_effective_date_regression(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo)
    with pytest.raises(subject.LocalBillingRepositoryError, match="temporal regression in effective date"):
        _append(
            repo,
            source_event_id="evt-effective-regression",
            source_event_digest=DIGEST_B,
            effective_date=date(2026, 9, 1),
            valid_from_inclusive=date(2026, 9, 1),
            valid_until_exclusive=date(2026, 10, 1),
            expected_predecessor_identity=first.content_identity,
            expected_sequence=2,
        )


def test_append_rejects_transition_instant_regression(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo)
    with pytest.raises(subject.LocalBillingRepositoryError, match="temporal regression in transition"):
        _append(
            repo,
            source_event_id="evt-transition-regression",
            source_event_digest=DIGEST_B,
            transition_effective_at_utc=datetime(2026, 9, 1, tzinfo=UTC),
            expected_predecessor_identity=first.content_identity,
            expected_sequence=2,
        )


# Finding 4: corrupt backing content is detected on head read and advancement.
def test_corrupt_prior_journal_content_fails_head_read_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    raw = sqlite3.connect(str(path))
    raw.execute(
        "UPDATE billing_journal SET evidence_reference = 'evidence/tampered' "
        "WHERE owner_id = ? AND sequence = 1",
        (OWNER,),
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="content identity"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="content identity"):
        _append(
            repo,
            source_event_id="evt-successor-after-corruption",
            source_event_digest=DIGEST_B,
            expected_predecessor_identity=first.content_identity,
            expected_sequence=2,
        )


def test_orphan_head_without_journal_row_fails_read(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    _append(repo)
    raw = sqlite3.connect(str(path))
    raw.execute("DELETE FROM billing_journal WHERE owner_id = ?", (OWNER,))
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="head exists without any journal"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )


def _raw_journal_sequences(path, owner_id):
    raw = sqlite3.connect(str(path))
    try:
        rows = raw.execute(
            "SELECT sequence FROM billing_journal WHERE owner_id = ? ORDER BY sequence",
            (owner_id,),
        ).fetchall()
        return tuple(row[0] for row in rows)
    finally:
        raw.close()


def _raw_head_state(path, owner_id):
    raw = sqlite3.connect(str(path))
    try:
        row = raw.execute(
            "SELECT sequence, state FROM subscription_head WHERE owner_id = ?",
            (owner_id,),
        ).fetchone()
        return None if row is None else (row[0], row[1])
    finally:
        raw.close()


# Finding 4 (residual v2): complete chain/head consistency is validated on reads
# and within the advancement transaction; no silent repair by append.
def test_missing_origin_sequence_fails_reads_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    raw = sqlite3.connect(str(path))
    raw.execute(
        "DELETE FROM billing_journal WHERE owner_id = ? AND sequence = 1", (OWNER,)
    )
    raw.commit()
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError, match="origin"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="origin"):
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )

    before = (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER))
    with pytest.raises(subject.LocalBillingRepositoryError, match="origin"):
        _append_renewal(
            repo,
            second,
            source_event_id="evt-3",
            expected_sequence=3,
            effective_date=date(2026, 12, 1),
            transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
            valid_until_exclusive=date(2027, 1, 1),
            paid_through=date(2026, 12, 31),
        )
    assert (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER)) == before
    assert not repo._connection.in_transaction

    repo.close()
    reopened = subject.LocalBillingRepository.open(path)
    with pytest.raises(subject.LocalBillingRepositoryError, match="origin"):
        reopened.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    reopened.close()


def test_missing_interior_sequence_fails_reads_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    third = _append_renewal(
        repo,
        second,
        source_event_id="evt-3",
        expected_sequence=3,
        effective_date=date(2026, 12, 1),
        transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
        valid_until_exclusive=date(2027, 1, 1),
        paid_through=date(2026, 12, 31),
    )
    raw = sqlite3.connect(str(path))
    raw.execute(
        "DELETE FROM billing_journal WHERE owner_id = ? AND sequence = 2", (OWNER,)
    )
    raw.commit()
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError, match="interior"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="interior"):
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )

    before = (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER))
    with pytest.raises(subject.LocalBillingRepositoryError, match="interior"):
        _append_renewal(
            repo,
            third,
            source_event_id="evt-4",
            expected_sequence=4,
            effective_date=date(2027, 1, 1),
            transition_effective_at_utc=datetime(2027, 1, 1, tzinfo=UTC),
            valid_until_exclusive=date(2027, 2, 1),
            paid_through=date(2027, 1, 31),
        )
    assert (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER)) == before
    assert not repo._connection.in_transaction


def test_missing_tail_sequence_fails_reads_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    raw = sqlite3.connect(str(path))
    raw.execute(
        "DELETE FROM billing_journal WHERE owner_id = ? AND sequence = 2", (OWNER,)
    )
    raw.commit()
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError, match="journal tail"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="journal tail"):
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )

    before = (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER))
    with pytest.raises(subject.LocalBillingRepositoryError, match="journal tail"):
        _append_renewal(
            repo,
            second,
            source_event_id="evt-3",
            expected_sequence=3,
            effective_date=date(2026, 12, 1),
            transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
            valid_until_exclusive=date(2027, 1, 1),
            paid_through=date(2026, 12, 31),
        )
    assert (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER)) == before
    assert not repo._connection.in_transaction

    repo.close()
    reopened = subject.LocalBillingRepository.open(path)
    with pytest.raises(subject.LocalBillingRepositoryError, match="journal tail"):
        reopened.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    reopened.close()


def test_head_state_tamper_fails_reads_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    raw = sqlite3.connect(str(path))
    raw.execute(
        "UPDATE subscription_head SET state = 'suspended' WHERE owner_id = ?",
        (OWNER,),
    )
    raw.commit()
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError, match="head state"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="head state"):
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )

    before = (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER))
    with pytest.raises(subject.LocalBillingRepositoryError, match="head state"):
        _append_renewal(
            repo,
            second,
            source_event_id="evt-3",
            expected_sequence=3,
            effective_date=date(2026, 12, 1),
            transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
            valid_until_exclusive=date(2027, 1, 1),
            paid_through=date(2026, 12, 31),
        )
    assert (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER)) == before
    assert not repo._connection.in_transaction

    repo.close()
    reopened = subject.LocalBillingRepository.open(path)
    with pytest.raises(subject.LocalBillingRepositoryError, match="head state"):
        reopened.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    reopened.close()


def test_head_identity_tamper_fails_reads_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    raw = sqlite3.connect(str(path))
    raw.execute(
        "UPDATE subscription_head SET head_identity = 'sha256:tampered' "
        "WHERE owner_id = ?",
        (OWNER,),
    )
    raw.commit()
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError, match="head identity"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="head identity"):
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )

    before = (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER))
    with pytest.raises(subject.LocalBillingRepositoryError, match="head identity"):
        _append_renewal(
            repo,
            second,
            source_event_id="evt-3",
            expected_sequence=3,
            effective_date=date(2026, 12, 1),
            transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
            valid_until_exclusive=date(2027, 1, 1),
            paid_through=date(2026, 12, 31),
        )
    assert (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER)) == before
    assert not repo._connection.in_transaction


def test_orphan_journal_without_head_fails_reads_and_successor(tmp_path):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    raw = sqlite3.connect(str(path))
    raw.execute("DELETE FROM subscription_head WHERE owner_id = ?", (OWNER,))
    raw.commit()
    raw.close()

    with pytest.raises(subject.LocalBillingRepositoryError, match="without a current head"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="without a current head"):
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )

    before = (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER))
    with pytest.raises(subject.LocalBillingRepositoryError, match="without a current head"):
        _append_renewal(
            repo,
            second,
            source_event_id="evt-3",
            expected_sequence=3,
            effective_date=date(2026, 12, 1),
            transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
            valid_until_exclusive=date(2027, 1, 1),
            paid_through=date(2026, 12, 31),
        )
    assert (_raw_journal_sequences(path, OWNER), _raw_head_state(path, OWNER)) == before
    assert not repo._connection.in_transaction


def test_intact_chain_reads_and_successor_succeed(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo)
    second = _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )
    head = repo.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert head.sequence == 2
    assert head.head_identity == second.content_identity
    assert [r.sequence for r in repo.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )] == [1, 2]

    third = _append_renewal(
        repo,
        second,
        source_event_id="evt-3",
        expected_sequence=3,
        effective_date=date(2026, 12, 1),
        transition_effective_at_utc=datetime(2026, 12, 1, tzinfo=UTC),
        valid_until_exclusive=date(2027, 1, 1),
        paid_through=date(2026, 12, 31),
    )
    assert third.sequence == 3
    assert [r.sequence for r in repo.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )] == [1, 2, 3]


# Finding 5: dispositions are owner-scoped and reads never cross owners.
def test_disposition_chain_is_owner_scoped_and_reads_do_not_leak(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append_disposition(
        repo,
        disposition_id="disposition:users17:evt-disp:1",
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        source_event_id="evt-disp",
    )
    assert first.disposition_sequence == 1
    assert first.predecessor_disposition_identity is None

    second = _append_disposition(
        repo,
        disposition_id="disposition:users99:evt-disp:1",
        owner_id=OWNER2,
        billing_account_id=ACCOUNT2,
        subscription_id=SUBSCRIPTION2,
        source_event_id="evt-disp",
    )
    # Same namespace/event but a different owner is an independent chain.
    assert second.disposition_sequence == 1
    assert second.predecessor_disposition_identity is None

    third = _append_disposition(
        repo,
        disposition_id="disposition:users17:evt-disp:2",
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        source_event_id="evt-disp",
    )
    assert third.disposition_sequence == 2
    assert third.predecessor_disposition_identity == first.disposition_identity

    d17 = repo.reconciliation_dispositions(
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-disp",
    )
    d99 = repo.reconciliation_dispositions(
        owner_id=OWNER2,
        billing_account_id=ACCOUNT2,
        subscription_id=SUBSCRIPTION2,
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-disp",
    )
    assert [d.disposition_sequence for d in d17] == [1, 2]
    assert [d.disposition_sequence for d in d99] == [1]
    # A third owner observes nothing: no cross-owner read disclosure.
    nobody = repo.reconciliation_dispositions(
        owner_id="users:55",
        billing_account_id="billing:55",
        subscription_id="subscription:55",
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-disp",
    )
    assert nobody == ()


# Finding 6: any non-sqlite, non-domain exception rolls back the whole write.
def test_runtime_error_at_head_upsert_rolls_back_and_reopens_clean(tmp_path, monkeypatch):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    original_upsert = repo._upsert_head_row

    def explode(connection, values):
        raise RuntimeError("injected at head upsert")

    monkeypatch.setattr(repo, "_upsert_head_row", explode)
    with pytest.raises(RuntimeError, match="injected at head upsert"):
        _append(repo)

    raw = sqlite3.connect(str(path))
    assert raw.execute("SELECT COUNT(*) FROM billing_journal").fetchone()[0] == 0
    assert raw.execute("SELECT COUNT(*) FROM subscription_head").fetchone()[0] == 0
    raw.close()
    assert not repo._connection.in_transaction

    # The original repository remains usable after the failed write.
    monkeypatch.setattr(repo, "_upsert_head_row", original_upsert)
    record = _append(repo)
    assert record.sequence == 1


def test_runtime_error_at_disposition_insert_rolls_back(tmp_path, monkeypatch):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    original = repo._insert_disposition_row

    def explode(connection, values, disposition_identity):
        original(connection, values, disposition_identity)
        raise RuntimeError("injected after disposition insert")

    monkeypatch.setattr(repo, "_insert_disposition_row", explode)
    with pytest.raises(RuntimeError, match="injected after disposition insert"):
        _append_disposition(repo, disposition_id="disposition:users17:rollback")

    raw = sqlite3.connect(str(path))
    assert (
        raw.execute("SELECT COUNT(*) FROM reconciliation_disposition").fetchone()[0]
        == 0
    )
    raw.close()
    assert not repo._connection.in_transaction


def test_create_rolls_back_when_schema_ddl_fails(tmp_path, monkeypatch):
    path = tmp_path / "repo.db"
    monkeypatch.setattr(
        subject, "_SCHEMA_DDL", subject._SCHEMA_DDL + ("THIS IS NOT VALID SQL;",)
    )
    with pytest.raises(sqlite3.OperationalError):
        subject.LocalBillingRepository.create(path)
    raw = sqlite3.connect(str(path))
    tables = [
        row[0]
        for row in raw.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    ]
    raw.close()
    assert tables == []


# --- 11. correction v3 regressions (three independently reproduced defects) ---


def _create_repo_with_modified_ddl(path, replacements):
    """Build a fresh DB from ``subject._SCHEMA_DDL`` with string replacements
    applied while preserving the legitimate ``repository_meta`` (original
    ``schema_version`` and ``schema_digest``).  Only live schema semantics can
    then reject the file; a digest-only check cannot."""
    ddl = []
    for statement in subject._SCHEMA_DDL:
        for old, new in replacements:
            statement = statement.replace(old, new)
        ddl.append(statement)
    raw = sqlite3.connect(str(path), isolation_level=None)
    raw.execute("PRAGMA foreign_keys = ON")
    for statement in ddl:
        raw.execute(statement)
    raw.execute(
        "INSERT INTO repository_meta (key, value) VALUES ('schema_version', ?)",
        (subject.SCHEMA_VERSION,),
    )
    raw.execute(
        "INSERT INTO repository_meta (key, value) VALUES ('schema_digest', ?)",
        (subject._SCHEMA_DIGEST,),
    )
    raw.execute(
        "INSERT INTO repository_meta (key, value) VALUES ('repository_purpose', ?)",
        (subject.REPOSITORY_PURPOSE,),
    )
    raw.execute(
        "INSERT INTO repository_meta (key, value) VALUES ('created_at_utc', ?)",
        ("2026-10-01T00:00:00+00:00",),
    )
    raw.close()


# v3 defect 1: actual column semantics (type/nullability/default) and declared
# table constraints are validated, not only names/PK/index/digest.
def test_open_rejects_dropped_not_null_constraint(tmp_path):
    path = tmp_path / "repo.db"
    _create_repo_with_modified_ddl(
        path, [("source_event_id TEXT NOT NULL", "source_event_id TEXT")]
    )
    with pytest.raises(subject.LocalBillingRepositoryError, match="column semantics"):
        subject.LocalBillingRepository.open(path)


@pytest.mark.parametrize(
    "replacements, message",
    [
        (
            [("source_event_id TEXT NOT NULL", "source_event_id INTEGER NOT NULL")],
            "column semantics",
        ),
        (
            [
                (
                    "source_event_id TEXT NOT NULL",
                    "source_event_id TEXT NOT NULL DEFAULT 'x'",
                )
            ],
            "column semantics",
        ),
        (
            [
                (
                    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, sequence))",
                    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, "
                    "sequence), CHECK (sequence > 0))",
                )
            ],
            "check constraint",
        ),
        (
            [
                (
                    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, sequence))",
                    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, "
                    "sequence), UNIQUE (source_namespace, source_event_id))",
                )
            ],
            "unique constraint",
        ),
        (
            [
                (
                    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, sequence))",
                    "PRIMARY KEY (owner_id, billing_account_id, subscription_id, "
                    "sequence), FOREIGN KEY (owner_id) REFERENCES repository_meta (key))",
                )
            ],
            "foreign key",
        ),
    ],
)
def test_open_rejects_altered_column_or_constraint_semantics(
    tmp_path, replacements, message
):
    path = tmp_path / "repo.db"
    _create_repo_with_modified_ddl(path, replacements)
    with pytest.raises(subject.LocalBillingRepositoryError, match=message):
        subject.LocalBillingRepository.open(path)


def test_open_preserves_identical_legitimate_schema(tmp_path):
    path = tmp_path / "repo.db"
    _create_repo_with_modified_ddl(path, [])
    reopened = subject.LocalBillingRepository.open(path)
    assert reopened.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    ) is None
    reopened.close()


# v3 defect 2: multi-query reads return one internally consistent snapshot.
def test_concurrent_writer_cannot_tear_read_snapshot(tmp_path, monkeypatch):
    path = tmp_path / "repo.db"
    repo = _make_repo(tmp_path)
    first = _append(repo)
    repo.close()

    def open_cross_thread():
        connection = sqlite3.connect(
            str(path), isolation_level=None, timeout=10, check_same_thread=False
        )
        connection.execute("PRAGMA foreign_keys = ON")
        return subject.LocalBillingRepository(connection, path)

    reader = open_cross_thread()
    writer = open_cross_thread()

    reader_paused = threading.Event()
    release_reader = threading.Event()
    writer_wrote_head = threading.Event()
    writer_finished = threading.Event()
    results = []
    writer_errors = []

    original_verify = reader._verify_chain_and_head

    def pausing_verify(connection, owner, account, subscription):
        reader_paused.set()
        release_reader.wait(timeout=10)
        return original_verify(connection, owner, account, subscription)

    monkeypatch.setattr(reader, "_verify_chain_and_head", pausing_verify)

    original_upsert = writer._upsert_head_row

    def signal_upsert(connection, values):
        result = original_upsert(connection, values)
        writer_wrote_head.set()
        return result

    monkeypatch.setattr(writer, "_upsert_head_row", signal_upsert)

    def do_read():
        results.append(
            reader.current_head(
                owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
            )
        )

    def do_write():
        try:
            writer.append_observation(
                **_repo_obs(
                    source_event_id="evt-snapshot-successor",
                    source_event_digest=DIGEST_B,
                    observation_kind="renewal_payment_confirmed",
                    effective_date=date(2026, 11, 1),
                    paid_through=date(2026, 11, 30),
                    valid_until_exclusive=date(2026, 12, 1),
                    transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
                    derivation_kind="verified_renewal_payment",
                    expected_predecessor_identity=first.content_identity,
                    expected_sequence=2,
                )
            )
            writer_finished.set()
        except Exception as exc:  # pragma: no cover - failure path
            writer_errors.append(exc)

    reader_thread = threading.Thread(target=do_read)
    writer_thread = threading.Thread(target=do_write)

    reader_thread.start()
    assert reader_paused.wait(timeout=10)

    writer_thread.start()
    assert writer_wrote_head.wait(timeout=10)

    # The reader still holds its snapshot (shared lock), so the writer's commit
    # is blocked and the reader cannot observe a torn journal/head state.
    assert not writer_finished.is_set()

    release_reader.set()
    reader_thread.join(timeout=10)
    writer_thread.join(timeout=10)

    assert not writer_errors
    assert writer_finished.is_set()
    assert results[0].sequence == 1

    reader.close()
    writer.close()

    reopened = subject.LocalBillingRepository.open(path)
    assert reopened.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    ).sequence == 2
    reopened.close()


def test_read_snapshot_rolls_back_and_leaves_connection_usable(tmp_path):
    repo = _make_repo(tmp_path)
    _append(repo)

    head = repo.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert head.sequence == 1
    assert not repo._connection.in_transaction

    journal = repo.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert len(journal) == 1
    assert not repo._connection.in_transaction

    # A read that detects corruption also rolls back and stays usable.
    raw = sqlite3.connect(str(tmp_path / "repo.db"))
    raw.execute(
        "UPDATE billing_journal SET evidence_reference = 'evidence/tampered' "
        "WHERE owner_id = ? AND sequence = 1",
        (OWNER,),
    )
    raw.commit()
    raw.close()
    with pytest.raises(subject.LocalBillingRepositoryError, match="content identity"):
        repo.current_head(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    assert not repo._connection.in_transaction


# v3 defect 3: generated quarantine disposition ids are bound to source identity.
def test_distinct_events_same_supplied_digest_get_distinct_quarantine_dispositions(
    tmp_path,
):
    repo = _make_repo(tmp_path)
    first = _append(repo, source_event_id="evt-1")
    _append_renewal(
        repo,
        first,
        source_event_id="evt-2",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )

    conflict_digest = "sha256:" + "c" * 64
    with pytest.raises(subject.LocalBillingRepositoryError, match="quarantined"):
        _append(
            repo,
            source_event_id="evt-1",
            source_event_digest=conflict_digest,
            evidence_reference="evidence/conflict-1",
        )
    with pytest.raises(subject.LocalBillingRepositoryError, match="quarantined"):
        _append(
            repo,
            source_event_id="evt-2",
            source_event_digest=conflict_digest,
            evidence_reference="evidence/conflict-2",
        )

    # Neither conflict advanced or rewrote the journal/head.
    assert len(
        repo.journal(
            owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
    ) == 2
    assert repo.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    ).sequence == 2

    def dispositions_for(event_id):
        return repo.reconciliation_dispositions(
            owner_id=OWNER,
            billing_account_id=ACCOUNT,
            subscription_id=SUBSCRIPTION,
            source_namespace="stripe-subscription/test-scope",
            source_event_id=event_id,
        )

    first_dispositions = dispositions_for("evt-1")
    second_dispositions = dispositions_for("evt-2")
    assert len(first_dispositions) == 1
    assert len(second_dispositions) == 1
    assert first_dispositions[0].kind == "quarantined_reused_source_identity"
    assert second_dispositions[0].kind == "quarantined_reused_source_identity"
    assert first_dispositions[0].disposition_id != second_dispositions[0].disposition_id

    # The generated ids expose no raw payloads, digests or cross-owner material.
    for disposition in (first_dispositions[0], second_dispositions[0]):
        assert OWNER not in disposition.disposition_id
        assert "evt-1" not in disposition.disposition_id
        assert "evt-2" not in disposition.disposition_id
        assert conflict_digest not in disposition.disposition_id

    # Same-event sequencing and reopen remain correct.
    repo.close()
    reopened = subject.LocalBillingRepository.open(tmp_path / "repo.db")
    reopened_ids = [
        d.disposition_id
        for d in reopened.reconciliation_dispositions(
            owner_id=OWNER,
            billing_account_id=ACCOUNT,
            subscription_id=SUBSCRIPTION,
            source_namespace="stripe-subscription/test-scope",
            source_event_id="evt-1",
        )
    ]
    reopened.close()
    assert reopened_ids == [first_dispositions[0].disposition_id]


# --- 12. correction v4 regressions (approved-schema comparison/conflict semantics) ---


@pytest.mark.parametrize(
    "replacements",
    [
        [("owner_id TEXT NOT NULL", "owner_id TEXT NOT NULL COLLATE NOCASE")],
        [
            (
                "source_event_id TEXT NOT NULL",
                "source_event_id TEXT NOT NULL COLLATE NOCASE",
            )
        ],
        [
            (
                "ON billing_journal (source_namespace, source_event_id)",
                "ON billing_journal (source_namespace, source_event_id COLLATE NOCASE)",
            )
        ],
        [
            (
                "PRIMARY KEY (owner_id, billing_account_id, subscription_id, sequence))",
                "PRIMARY KEY (owner_id, billing_account_id, subscription_id, "
                "sequence) ON CONFLICT REPLACE)",
            )
        ],
    ],
)
def test_open_rejects_altered_comparison_or_conflict_semantics(tmp_path, replacements):
    path = tmp_path / "repo.db"
    _create_repo_with_modified_ddl(path, replacements)
    with pytest.raises(subject.LocalBillingRepositoryError, match="declaration"):
        subject.LocalBillingRepository.open(path)


def test_ordinary_schema_keeps_exact_case_owner_isolation(tmp_path):
    repo = _make_repo(tmp_path)
    _append(repo)
    assert (
        repo.current_head(
            owner_id="USERS:17", billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
        is None
    )
    assert (
        repo.journal(
            owner_id="USERS:17", billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
        )
        == ()
    )
    repo.close()


def test_ordinary_schema_treats_distinct_case_event_ids_as_distinct(tmp_path):
    repo = _make_repo(tmp_path)
    first = _append(repo, source_event_id="evt-1")
    _append_renewal(
        repo,
        first,
        source_event_id="EVT-1",
        expected_sequence=2,
        effective_date=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        valid_until_exclusive=date(2026, 12, 1),
        paid_through=date(2026, 11, 30),
    )

    journal = repo.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    assert [record.sequence for record in journal] == [1, 2]
    assert [record.source_event_id for record in journal] == ["evt-1", "EVT-1"]
    assert repo.current_head(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    ).sequence == 2
    assert (
        repo.reconciliation_dispositions(
            owner_id=OWNER,
            billing_account_id=ACCOUNT,
            subscription_id=SUBSCRIPTION,
            source_namespace="stripe-subscription/test-scope",
            source_event_id="evt-1",
        )
        == ()
    )
    assert (
        repo.reconciliation_dispositions(
            owner_id=OWNER,
            billing_account_id=ACCOUNT,
            subscription_id=SUBSCRIPTION,
            source_namespace="stripe-subscription/test-scope",
            source_event_id="EVT-1",
        )
        == ()
    )
    repo.close()


def test_rejected_open_leaves_underlying_data_unchanged(tmp_path):
    path = tmp_path / "repo.db"
    _create_repo_with_modified_ddl(
        path, [("owner_id TEXT NOT NULL", "owner_id TEXT NOT NULL COLLATE NOCASE")]
    )
    raw = sqlite3.connect(str(path), isolation_level=None)
    raw.execute("INSERT INTO repository_meta (key, value) VALUES ('marker', 'kept')")
    raw.close()

    before = path.read_bytes()
    with pytest.raises(subject.LocalBillingRepositoryError, match="declaration"):
        subject.LocalBillingRepository.open(path)
    assert path.read_bytes() == before

    raw = sqlite3.connect(str(path))
    try:
        marker = raw.execute(
            "SELECT value FROM repository_meta WHERE key = 'marker'"
        ).fetchone()
        tables = raw.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    finally:
        raw.close()
    assert marker == ("kept",)
    assert tables == [
        ("billing_journal",),
        ("reconciliation_disposition",),
        ("repository_meta",),
        ("subscription_head",),
    ]

