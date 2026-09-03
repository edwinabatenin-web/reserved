"""Bounded 2026/27 annual tax-position calculation.

This module is deliberately isolated from the incremental invoice estimator and
from PAYE reconciliation.  It calculates only the independently validated
annual families below and reports excluded or fact-incomplete families at the
same boundary.  In particular, a pre-credit or pre-finance-cost-reduction
amount is never presented as a complete tax position.
"""

from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
import hashlib
import hmac
import json
import threading
from typing import Any
import weakref

from .tax_config import get_config


PENNY = Decimal("0.01")
ZERO = Decimal("0")

# Geography admission is bounded to the authoritative October nations. Each
# alias is recognised independently; absence (including a None value) carries
# no geography fact and is never treated as positive launch evidence.
_GEOGRAPHY_ALIASES = (
    "jurisdiction",
    "country",
    "country_code",
    "territory",
    "tax_regime",
)

# Canonical supported-nation vocabulary. Accepted spellings/codes are kept
# deliberately small: the nation name plus its ISO 3166-2 GB subdivision code.
# Umbrella labels such as "UK", "GB" or "United Kingdom" are not evidence of a
# supported nation and are rejected (fail closed) rather than inferred.
def _make_geography_admission():
    aliases = _GEOGRAPHY_ALIASES
    nation_aliases = {
        "england": "England",
        "gb-eng": "England",
        "wales": "Wales",
        "gb-wls": "Wales",
        "northern ireland": "Northern Ireland",
        "gb-nir": "Northern Ireland",
    }
    instance_check = isinstance
    string_type = str
    set_type = set
    length = len
    split_text = string_type.split
    lower_text = string_type.lower
    join_text = " ".join
    error_type = ValueError
    unsupported = "Unsupported geography for the annual tax position"
    conflicting = "Conflicting geography facts for the annual tax position"

    def normalise(raw: Any) -> str:
        if not instance_check(raw, string_type):
            raise error_type(unsupported)
        # Call captured built-in ``str`` operations directly. A hostile
        # subclass must not redefine ``split``/``lower`` to turn unsupported
        # source text into an admitted nation.
        text = lower_text(join_text(split_text(raw)))
        nation = nation_aliases.get(text)
        if nation is None:
            raise error_type(unsupported)
        return nation

    def enforce(facts: dict[str, Any]) -> str | None:
        nations = [
            normalise(facts[alias])
            for alias in aliases
            if facts.get(alias) is not None
        ]
        if length(set_type(nations)) > 1:
            raise error_type(conflicting)
        return nations[0] if nations else None

    return normalise, enforce


_normalise_geography, _enforce_geography_admission = _make_geography_admission()
del _make_geography_admission


def _decimal(value: Any, name: str, *, default: str = "0") -> Decimal:
    if value is None:
        value = default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be monetary, not boolean")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not result.is_finite() or result < ZERO:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _signed_decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be monetary, not boolean")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _money(value: Decimal) -> Decimal:
    return value.quantize(PENNY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class AnnualPositionResult:
    """Internal engine result aligned to the WP7U estimate-envelope boundary.

    ``total_liability`` is populated only when every applicable liability
    family included in the request is supported and sufficiently evidenced.
    ``income_tax_before_limitations`` remains useful for review when a named
    downstream limitation (currently FTCR or residential finance costs) is
    unresolved.

    ``personal_allowance`` is the tapered ordinary Personal Allowance only.
    ``blind_persons_allowance`` is the separately established usable Blind
    Person's Allowance (``None`` when the required BPA fact group is absent or
    incomplete; a non-negative amount otherwise) and is never folded into
    ``personal_allowance``.
    """

    contract_version: str
    tax_year: str
    nation: str | None
    ruleset_version: str
    calculation_status: str
    adjusted_net_income: Decimal
    personal_allowance: Decimal
    blind_persons_allowance: Decimal | None
    non_savings_tax: Decimal
    savings_tax: Decimal
    dividend_tax: Decimal
    income_tax_before_limitations: Decimal | None
    class_4_ni: Decimal
    hicbc: Decimal | None
    hicbc_household_charge: Decimal | None
    hicbc_charge_percentage: int | None
    child_benefit_amount: Decimal | None
    hicbc_liable_person: str | None
    total_liability: Decimal | None
    personal_savings_allowance: Decimal
    dividend_allowance: Decimal
    uk_property_profit: Decimal
    uk_property_loss_to_carry_forward: Decimal
    foreign_property_profit: Decimal | None
    foreign_tax_paid_recorded: Decimal
    included_families: tuple[str, ...]
    unsupported_families: tuple[str, ...]
    limitations: tuple[str, ...]


def _make_annual_position_issuance():
    """Bind admitted geography to the exact live annual result.

    The annual result predates this W8 boundary and remains a normal internal
    dataclass.  This capability gives downstream customer-facing composition a
    process-local way to prove that its geography came from the calculation
    entry point rather than from ``replace``/copy/reconstruction or a later
    caller.  It is mutation detection, not provider authentication.
    """
    dc_fields = fields
    decimal_type = Decimal
    annual_type = AnnualPositionResult
    sha256 = hashlib.sha256
    dumps = json.dumps
    compare = hmac.compare_digest
    make_ref = weakref.ref
    lock = threading.RLock()
    exact_type = type
    raw = object.__getattribute__
    identity = id
    list_type = list
    tuple_type = tuple
    string_type = str
    integer_type = int
    failures = (AttributeError, TypeError, ValueError, ArithmeticError)
    error_type = ValueError
    registry: dict[int, tuple[weakref.ReferenceType[AnnualPositionResult], str]] = {}
    failure = "annual position is not a live geography-bound producer result"

    def canonical(value: object) -> object:
        value_type = exact_type(value)
        if value_type is annual_type:
            return {
                "type": "AnnualPositionResult",
                "fields": {
                    item.name: canonical(raw(value, item.name))
                    for item in dc_fields(annual_type)
                },
            }
        if value_type is decimal_type:
            parts = value.as_tuple()
            return {
                "decimal": {
                    "sign": parts.sign,
                    "digits": list_type(parts.digits),
                    "exponent": parts.exponent,
                }
            }
        if value_type is tuple_type:
            return {"tuple": [canonical(item) for item in value]}
        if value is None or value_type in (string_type, integer_type):
            return value
        raise error_type(failure)

    def digest(value: AnnualPositionResult) -> str:
        try:
            payload = dumps(
                canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        except failures:
            raise error_type(failure) from None
        return sha256(payload).hexdigest()

    def issue(value: AnnualPositionResult) -> AnnualPositionResult:
        value_digest = digest(value)
        key = identity(value)

        def cleanup(ref, *, registry=registry, key=key, lock=lock):
            with lock:
                current = registry.get(key)
                if current is not None and current[0] is ref:
                    registry.pop(key, None)

        ref = make_ref(value, cleanup)
        with lock:
            registry[key] = (ref, value_digest)
        return value

    def geography(value: object) -> str | None:
        if exact_type(value) is not annual_type:
            raise error_type(failure)
        with lock:
            retained = registry.get(identity(value))
        if retained is None or retained[0]() is not value:
            raise error_type(failure)
        current_digest = digest(value)
        if not compare(retained[1], current_digest):
            raise error_type(failure)
        nation = raw(value, "nation")
        if nation is not None and (
            exact_type(nation) is not string_type
            or nation not in ("England", "Wales", "Northern Ireland")
        ):
            raise error_type(failure)
        return nation

    return issue, geography


_issue_annual_position, annual_position_geography = _make_annual_position_issuance()
del _make_annual_position_issuance


def _personal_allowance(ani: Decimal, cfg: dict) -> Decimal:
    if ani <= cfg["PERSONAL_ALLOWANCE_TAPER_START"]:
        return cfg["PERSONAL_ALLOWANCE"]
    reduction = (ani - cfg["PERSONAL_ALLOWANCE_TAPER_START"]) / Decimal("2")
    return max(ZERO, cfg["PERSONAL_ALLOWANCE"] - reduction)


def _blind_persons_allowance(facts: dict, cfg: dict) -> tuple[Decimal | None, bool]:
    """Derive usable Blind Person's Allowance from explicit, user-supplied facts.

    Returns ``(usable, incomplete)``.  The BPA fact group is the entitlement
    fact plus both transfer directions; a wholly absent or partially supplied
    group is ``incomplete`` (the caller must then withhold the complete annual
    position rather than assume zero or full entitlement).  When all three
    members are present the determination is all-or-nothing: malformed or
    materially contradictory values raise ``ValueError`` so the caller fails
    closed.
    """
    bpa_keys = (
        "blind_persons_allowance_entitled",
        "blind_persons_allowance_transferred_in",
        "blind_persons_allowance_transferred_out",
    )
    if not all(key in facts and facts[key] is not None for key in bpa_keys):
        return None, True

    entitled = _tri_bool(facts[bpa_keys[0]], bpa_keys[0])
    transferred_in = _decimal(facts[bpa_keys[1]], bpa_keys[1])
    transferred_out = _decimal(facts[bpa_keys[2]], bpa_keys[2])
    full = cfg["BLIND_PERSONS_ALLOWANCE"]

    if transferred_out > ZERO and not entitled:
        raise ValueError(
            "Blind Person's Allowance cannot be transferred out without own entitlement"
        )
    if transferred_in > ZERO and transferred_out > ZERO:
        raise ValueError(
            "Blind Person's Allowance cannot be both transferred in and transferred out"
        )
    if transferred_in > full or transferred_out > full:
        raise ValueError(
            "Blind Person's Allowance transfer amount exceeds the statutory allowance"
        )

    own = full if entitled else ZERO
    usable = own + transferred_in - transferred_out
    if usable < ZERO:
        raise ValueError(
            "Blind Person's Allowance facts produce an impossible negative usable allowance"
        )
    return usable, False


def _ordinary_tax(
    amount: Decimal, cursor: Decimal, basic_limit: Decimal, higher_rate_limit: Decimal, cfg: dict
) -> Decimal:
    """Tax ``amount`` stacked from taxable-income ``cursor``.

    ``basic_limit`` and ``higher_rate_limit`` are the (possibly
    Relief-at-Source-extended) basic-rate limit and the higher-rate limit at
    which the additional rate begins (HMRC Pensions Tax Manual PTM056120).
    """
    tax = ZERO
    end = cursor + amount
    bands = (
        (basic_limit, cfg["INCOME_TAX_RATES"]["basic"]),
        (higher_rate_limit, cfg["INCOME_TAX_RATES"]["higher"]),
        (Decimal("Infinity"), cfg["INCOME_TAX_RATES"]["additional"]),
    )
    for ceiling, rate in bands:
        taxable = max(ZERO, min(end, ceiling) - cursor)
        if taxable:
            tax += taxable * rate
            cursor += taxable
        if cursor >= end:
            break
    return tax


def _dividend_tax(
    amount: Decimal, cursor: Decimal, basic_limit: Decimal, higher_rate_limit: Decimal, cfg: dict
) -> Decimal:
    tax = ZERO
    end = cursor + amount
    bands = (
        (basic_limit, cfg["DIVIDEND_TAX_RATES"]["basic"]),
        (higher_rate_limit, cfg["DIVIDEND_TAX_RATES"]["higher"]),
        (Decimal("Infinity"), cfg["DIVIDEND_TAX_RATES"]["additional"]),
    )
    for ceiling, rate in bands:
        taxable = max(ZERO, min(end, ceiling) - cursor)
        if taxable:
            tax += taxable * rate
            cursor += taxable
        if cursor >= end:
            break
    return tax


def _class_4(profit: Decimal, cfg: dict) -> Decimal:
    rules = cfg["CLASS_4_NI"]
    main = max(ZERO, min(profit, rules["upper_profits_limit"]) - rules["lower_profits_limit"])
    upper = max(ZERO, profit - rules["upper_profits_limit"])
    return _money(main * rules["main_rate"] + upper * rules["upper_rate"])


def _tri_bool(value: Any, name: str) -> bool | None:
    """Parse a tri-state boolean fact (True/False/None), failing closed on malformed."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return value == 1
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "y"):
            return True
        if text in ("0", "false", "no", "n"):
            return False
    raise ValueError(f"{name} must be a boolean (true/false) or null")


def _weeks(value: Any) -> int:
    """Parse a whole-number entitlement-weeks fact in the inclusive range 0..53."""
    if isinstance(value, bool):
        raise ValueError("weeks_entitled must be a whole number, not boolean")
    text = str(value).strip()
    if "." in text:
        raise ValueError("weeks_entitled must be a whole number from 0 to 53")
    try:
        weeks = int(text)
    except (ValueError, TypeError):
        raise ValueError("weeks_entitled must be a whole number from 0 to 53") from None
    if not 0 <= weeks <= 53:
        raise ValueError("weeks_entitled must be between 0 and 53")
    return weeks


def _child_benefit(facts: dict, cfg: dict) -> tuple[Decimal | None, str | None]:
    # ``child_benefit_payments_received`` records the actual payments received for
    # the charge period (zero when the claimant opted not to receive payments);
    # its amount is already period-bound and needs no separate weeks derivation.
    if "child_benefit_payments_received" in facts:
        return _decimal(facts["child_benefit_payments_received"], "child_benefit_payments_received"), None
    for key in ("annual_child_benefit", "annual_child_benefit_received_by_person"):
        if key in facts:
            # An explicit annual amount may be used without deriving weeks only
            # when the supplied facts establish it is the relevant amount for the
            # whole charge period; a theoretical full-year award must not be
            # relabelled as actual relevant payments.
            if facts.get("payments_received_for_full_charge_period") is not True:
                return None, "hicbc_facts_incomplete"
            return _decimal(facts[key], key), None
    if "eldest_or_only_children" in facts or "additional_children" in facts:
        eldest = int(facts.get("eldest_or_only_children", 0))
        additional = int(facts.get("additional_children", 0))
        if eldest not in (0, 1) or additional < 0:
            raise ValueError("Child Benefit child counts are invalid")
        if "weeks_entitled" not in facts:
            # Omitted entitlement weeks remain unknown; they must never silently
            # become a 52-week full-year amount.
            return None, "hicbc_facts_incomplete"
        weeks = _weeks(facts["weeks_entitled"])
        weekly = eldest * cfg["CHILD_BENEFIT"]["eldest_weekly"] + additional * cfg["CHILD_BENEFIT"]["additional_weekly"]
        return _money(weekly * weeks), None
    if facts.get("child_benefit_applicable") is True:
        return None, "hicbc_facts_incomplete"
    return None, None


def _hicbc(ani: Decimal, benefit: Decimal, cfg: dict) -> tuple[int, Decimal]:
    rules = cfg["HICBC"]
    points = int(max(ZERO, ani - rules["lower_threshold"]) // rules["income_per_percentage_point"])
    percentage = min(100, points)
    # Statutory staging: round the relevant Child Benefit down to whole pounds,
    # apply the whole complete-£200 percentage, then round the charge down.
    whole_pound_benefit = benefit.to_integral_value(rounding=ROUND_FLOOR)
    charge = (whole_pound_benefit * Decimal(percentage) / Decimal("100")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    return percentage, _money(charge)


def _calculate_annual_position_impl(
    facts: dict[str, Any],
    tax_year: str = "2026/27",
    *,
    _geography_admitter,
    _issuer,
) -> AnnualPositionResult:
    """Calculate a bounded annual position from explicit, synthetic-safe facts.

    The function does not read fixtures, providers, persistence, PAYE records or
    student-loan data. Negative property results are carried forward within the
    UK property business and never offset against employment or trade income.
    """
    if tax_year != "2026/27":
        raise ValueError("The integrated annual-position tranche supports 2026/27 only")
    admitted_nation = _geography_admitter(facts)
    cfg = get_config(tax_year)
    joint_total_present = "joint_property_total_profit" in facts
    joint_share_present = "taxpayer_share_percentage" in facts
    property_modes = sum((
        "uk_property_results" in facts,
        "uk_property_receipts" in facts or "uk_property_allowable_expenses" in facts,
        joint_total_present,
        "rental_income" in facts or "non_finance_allowable_expenses" in facts,
        "uk_property_profit" in facts,
    ))
    if property_modes > 1:
        raise ValueError("UK property must use exactly one input representation")
    if joint_total_present != joint_share_present:
        raise ValueError(
            "joint_property_total_profit and taxpayer_share_percentage must be supplied together"
        )
    if ("foreign_property_profit" in facts) and (
        "foreign_property_gross_receipts" in facts or "foreign_property_allowable_expenses" in facts
    ):
        raise ValueError("Foreign property must use profit or receipts/expenses, not both")
    benefit_modes = sum((
        "child_benefit_payments_received" in facts,
        "annual_child_benefit" in facts,
        "annual_child_benefit_received_by_person" in facts,
        "eldest_or_only_children" in facts or "additional_children" in facts,
    ))
    if benefit_modes > 1:
        raise ValueError("Child Benefit must use exactly one amount representation")
    if "person_adjusted_net_income" in facts and "adjusted_net_income" in facts:
        if _decimal(facts["person_adjusted_net_income"], "person_adjusted_net_income") != _decimal(
            facts["adjusted_net_income"], "adjusted_net_income"
        ):
            raise ValueError("Person and supplied adjusted net income facts contradict")
    if "partner_adjusted_net_income" in facts and not (
        "person_adjusted_net_income" in facts or "adjusted_net_income" in facts
    ):
        raise ValueError("Partner ANI requires the person's explicit ANI for responsibility comparison")
    employment = _decimal(facts.get("employment_income"), "employment_income")
    trade = _decimal(facts.get("sole_trade_profit"), "sole_trade_profit")
    savings = _decimal(facts.get("savings_interest"), "savings_interest")
    dividends = _decimal(facts.get("dividends"), "dividends")
    pension = _decimal(facts.get("gross_ras_pension"), "gross_ras_pension")
    if "income_before_ras_pension" in facts and "adjusted_net_income" in facts:
        derived_ani = max(
            ZERO,
            _decimal(facts["income_before_ras_pension"], "income_before_ras_pension") - pension,
        )
        if derived_ani != _decimal(facts["adjusted_net_income"], "adjusted_net_income"):
            raise ValueError("Adjusted net income contradicts income before the supplied gross pension")

    # Property inputs may be a precomputed result, component results, or
    # explicit receipts/expenses. The engine never infers ownership shares.
    property_loss = ZERO
    if "uk_property_results" in facts:
        raw_result = sum(
            (_signed_decimal(value, "uk_property_results item") for value in facts["uk_property_results"]),
            ZERO,
        )
    elif "uk_property_receipts" in facts or "uk_property_allowable_expenses" in facts:
        raw_result = _decimal(facts.get("uk_property_receipts"), "uk_property_receipts") - _decimal(
            facts.get("uk_property_allowable_expenses"), "uk_property_allowable_expenses"
        )
    elif "joint_property_total_profit" in facts:
        share = _decimal(facts.get("taxpayer_share_percentage"), "taxpayer_share_percentage")
        if share > 100:
            raise ValueError("taxpayer_share_percentage must not exceed 100")
        raw_result = _decimal(facts["joint_property_total_profit"], "joint_property_total_profit") * share / 100
    elif "rental_income" in facts or "non_finance_allowable_expenses" in facts:
        raw_result = _decimal(facts.get("rental_income"), "rental_income") - _decimal(
            facts.get("non_finance_allowable_expenses"), "non_finance_allowable_expenses"
        )
    else:
        raw_result = _signed_decimal(facts.get("uk_property_profit", "0"), "uk_property_profit")
    brought_forward = _decimal(facts.get("brought_forward_uk_property_loss"), "brought_forward_uk_property_loss")
    if raw_result < ZERO:
        property_profit = ZERO
        property_loss = brought_forward + abs(raw_result)
    else:
        property_profit = max(ZERO, raw_result - brought_forward)
        property_loss = max(ZERO, brought_forward - raw_result)

    unsupported: list[str] = []
    limitations: list[str] = ["paye_reconciliation_not_performed", "student_loan_not_calculated"]
    residential_finance_costs = _decimal(
        facts.get("residential_finance_costs"), "residential_finance_costs"
    )
    if residential_finance_costs > ZERO and not (
        facts.get("individual_landlord") is True and facts.get("residential_property") is True
    ):
        raise ValueError(
            "Residential finance costs require explicit individual-landlord and residential-property facts"
        )
    if residential_finance_costs > ZERO:
        unsupported.append("residential_finance_cost_reduction")
        limitations.append("income_tax_is_before_residential_finance_cost_reduction")

    foreign_tax = _decimal(facts.get("foreign_tax_paid"), "foreign_tax_paid")
    foreign_profit: Decimal | None = ZERO
    if "foreign_property_gross_receipts" in facts or "foreign_property_allowable_expenses" in facts:
        foreign_profit = _decimal(facts.get("foreign_property_gross_receipts"), "foreign_property_gross_receipts") - _decimal(
            facts.get("foreign_property_allowable_expenses"), "foreign_property_allowable_expenses"
        )
    else:
        foreign_profit = _decimal(facts.get("foreign_property_profit"), "foreign_property_profit")
    if foreign_profit < ZERO:
        unsupported.append("foreign_property_loss_treatment")
        limitations.append("foreign_property_loss_relief_not_supported")
        foreign_included = ZERO
    elif foreign_profit and facts.get("uk_resident") is not True:
        status = "residence_facts_incomplete" if facts.get("uk_resident") is None else "outside_supported_uk_resident_case"
        unsupported.append("foreign_property_residence")
        limitations.append(status)
        foreign_included = ZERO
    else:
        foreign_included = foreign_profit
    if foreign_tax > ZERO:
        unsupported.append("foreign_tax_credit_relief")
        limitations.append("income_tax_is_before_foreign_tax_credit_relief")

    gross_non_savings = employment + trade + property_profit + foreign_included
    gross_total = gross_non_savings + savings + dividends
    ani = max(ZERO, gross_total - pension)
    personal_allowance = _personal_allowance(ani, cfg)
    blind_persons_allowance, bpa_incomplete = _blind_persons_allowance(facts, cfg)
    if bpa_incomplete:
        limitations.append("blind_persons_allowance_facts_incomplete")
    allowance = personal_allowance + (blind_persons_allowance if blind_persons_allowance is not None else ZERO)
    pa_left = allowance
    taxable_ns = max(ZERO, gross_non_savings - pa_left)
    pa_left = max(ZERO, pa_left - gross_non_savings)
    taxable_savings = max(ZERO, savings - pa_left)
    pa_left = max(ZERO, pa_left - savings)
    taxable_dividends = max(ZERO, dividends - pa_left)

    basic_limit = cfg["BASIC_RATE_BAND"] + pension
    higher_rate_limit = cfg["ADDITIONAL_RATE_THRESHOLD"] + pension
    non_savings_tax = _money(_ordinary_tax(taxable_ns, ZERO, basic_limit, higher_rate_limit, cfg))
    cursor = taxable_ns

    starting_rate = min(taxable_savings, max(ZERO, cfg["SAVINGS"]["starting_rate_limit"] - taxable_ns))
    savings_after_starting = taxable_savings - starting_rate
    cursor += starting_rate
    total_taxable = taxable_ns + taxable_savings + taxable_dividends
    if total_taxable > higher_rate_limit:
        psa = cfg["SAVINGS"]["personal_savings_allowance_additional"]
    elif total_taxable > basic_limit:
        psa = cfg["SAVINGS"]["personal_savings_allowance_higher"]
    else:
        psa = cfg["SAVINGS"]["personal_savings_allowance_basic"]
    psa_used = min(psa, savings_after_starting)
    cursor += psa_used
    taxable_savings_after_allowances = savings_after_starting - psa_used
    savings_tax = _money(_ordinary_tax(taxable_savings_after_allowances, cursor, basic_limit, higher_rate_limit, cfg))
    cursor += taxable_savings_after_allowances

    dividend_allowance = min(cfg["DIVIDEND_ALLOWANCE"], taxable_dividends)
    cursor += dividend_allowance
    dividend_tax = _money(_dividend_tax(taxable_dividends - dividend_allowance, cursor, basic_limit, higher_rate_limit, cfg))
    income_tax = _money(non_savings_tax + savings_tax + dividend_tax)
    class_4 = _class_4(trade, cfg)

    benefit, hicbc_fact_status = _child_benefit(facts, cfg)
    hicbc: Decimal | None = None
    household_hicbc: Decimal | None = None
    hicbc_percentage: int | None = None
    liable_person: str | None = None
    if hicbc_fact_status:
        unsupported.append("hicbc")
        limitations.append(hicbc_fact_status)
    elif benefit is not None:
        explicit_ani = facts.get("adjusted_net_income")
        if explicit_ani is None and "income_before_ras_pension" in facts:
            explicit_ani = max(
                ZERO,
                _decimal(facts["income_before_ras_pension"], "income_before_ras_pension") - pension,
            )
        person_ani = _decimal(facts.get("person_adjusted_net_income", explicit_ani if explicit_ani is not None else ani), "adjusted_net_income")
        partner_raw = facts.get("partner_adjusted_net_income")
        has_relevant_partner = _tri_bool(facts.get("has_relevant_partner"), "has_relevant_partner")
        taxpayer_is_higher = _tri_bool(facts.get("taxpayer_is_higher_ani_partner"), "taxpayer_is_higher_ani_partner")

        # Claimant identity breaks an equal-ANI tie only (ITEPA 2003 s.681B); it
        # never establishes the absence of a higher-ANI partner.
        claimant_raw = facts.get("child_benefit_claimant")
        if claimant_raw is not None:
            claimant = str(claimant_raw).strip().lower()
            if claimant not in ("person", "partner"):
                raise ValueError(f"Unknown child_benefit_claimant: {claimant_raw!r}")
        elif "annual_child_benefit_received_by_person" in facts:
            claimant = "person"
        else:
            claimant = None

        # Reconcile the supplied responsibility facts for consistency.  A partner
        # ANI or a positive higher-ANI declaration implies a relevant partner; a
        # contradictory "no partner" fact must not be silently preferred.
        contradictory = False
        if partner_raw is not None:
            if has_relevant_partner is False:
                contradictory = True
            else:
                has_relevant_partner = True
        if taxpayer_is_higher is True:
            if has_relevant_partner is False:
                contradictory = True
            else:
                has_relevant_partner = True
        if claimant == "partner" and has_relevant_partner is False:
            contradictory = True

        if contradictory:
            unsupported.append("hicbc")
            limitations.append("hicbc_responsibility_facts_ambiguous")
        elif partner_raw is not None:
            partner_ani = _decimal(partner_raw, "partner_adjusted_net_income")
            if taxpayer_is_higher is True and partner_ani > person_ani:
                # Declares the user is the higher-ANI partner, but the supplied
                # partner ANI is higher: contradictory responsibility facts.
                unsupported.append("hicbc")
                limitations.append("hicbc_responsibility_facts_ambiguous")
            elif taxpayer_is_higher is False and partner_ani < person_ani:
                # Declares the user is not the higher-ANI partner, but the
                # supplied partner ANI is lower: contradictory responsibility facts.
                unsupported.append("hicbc")
                limitations.append("hicbc_responsibility_facts_ambiguous")
            elif partner_ani > person_ani:
                hicbc_percentage, household_hicbc = _hicbc(partner_ani, benefit, cfg)
                liable_person = "partner"
                limitations.append("hicbc_liability_belongs_to_higher_ani_partner")
                hicbc = ZERO
            elif partner_ani < person_ani:
                hicbc_percentage, hicbc = _hicbc(person_ani, benefit, cfg)
                household_hicbc = hicbc
                liable_person = "person"
            elif claimant == "person":
                # Equal ANI, person is claimant: condition A (s.681B(2)) is met.
                hicbc_percentage, hicbc = _hicbc(person_ani, benefit, cfg)
                household_hicbc = hicbc
                liable_person = "person"
            elif claimant == "partner":
                # Equal ANI, partner is claimant: condition B (s.681B(3)) is not met.
                hicbc_percentage, household_hicbc = _hicbc(partner_ani, benefit, cfg)
                liable_person = "partner"
                limitations.append("hicbc_liability_belongs_to_child_benefit_claimant")
                hicbc = ZERO
            else:
                # Equal ANI and claimant unknown: do not invent a tie-break.
                unsupported.append("hicbc")
                limitations.append("hicbc_responsibility_facts_ambiguous")
        elif has_relevant_partner is False:
            # Explicit absence of a relevant partner for the charge period.
            hicbc_percentage, hicbc = _hicbc(person_ani, benefit, cfg)
            household_hicbc = hicbc
            liable_person = "person"
        elif taxpayer_is_higher is True:
            # Explicit responsibility fact: the user is the higher-ANI partner.
            hicbc_percentage, hicbc = _hicbc(person_ani, benefit, cfg)
            household_hicbc = hicbc
            liable_person = "person"
        else:
            # Unknown partner status, a negative higher-ANI signal, or missing
            # partner ANI: never default to personal liability.
            unsupported.append("hicbc")
            limitations.append("hicbc_responsibility_facts_ambiguous")

        if (
            benefit == ZERO
            and facts.get("child_benefit_entitlement_retained") is True
            and "child_benefit_payments_received" in facts
        ):
            limitations.append("no_child_benefit_payments_to_charge")

    reported_ani = ani
    if "adjusted_net_income" in facts:
        reported_ani = _decimal(facts["adjusted_net_income"], "adjusted_net_income")
    elif "person_adjusted_net_income" in facts:
        reported_ani = _decimal(facts["person_adjusted_net_income"], "person_adjusted_net_income")
    elif "income_before_ras_pension" in facts:
        reported_ani = max(
            ZERO,
            _decimal(facts["income_before_ras_pension"], "income_before_ras_pension") - pension,
        )

    complete = (not unsupported) and (not bpa_incomplete)
    total = _money(income_tax + class_4 + (hicbc or ZERO)) if complete else None
    if complete:
        status = "calculated"
    elif any(family in unsupported for family in (
        "foreign_tax_credit_relief",
        "foreign_property_loss_treatment",
        "residential_finance_cost_reduction",
    )) or "outside_supported_uk_resident_case" in limitations:
        status = "unsupported_rule"
    else:
        status = "insufficient_facts"
    included = ["income_tax", "class_4_ni"]
    if benefit is not None and "hicbc" not in unsupported:
        included.append("hicbc")
    return _issuer(AnnualPositionResult(
        contract_version="reserved-estimate-envelope/1.1-internal",
        tax_year=tax_year,
        nation=admitted_nation,
        ruleset_version=cfg["rules_version"],
        calculation_status=status,
        adjusted_net_income=_money(reported_ani),
        personal_allowance=_money(personal_allowance),
        blind_persons_allowance=(
            _money(blind_persons_allowance) if blind_persons_allowance is not None else None
        ),
        non_savings_tax=non_savings_tax,
        savings_tax=savings_tax,
        dividend_tax=dividend_tax,
        income_tax_before_limitations=income_tax if gross_non_savings or savings or dividends else ZERO,
        class_4_ni=class_4,
        hicbc=hicbc,
        hicbc_household_charge=household_hicbc,
        hicbc_charge_percentage=hicbc_percentage,
        child_benefit_amount=_money(benefit) if benefit is not None else None,
        hicbc_liable_person=liable_person,
        total_liability=total,
        personal_savings_allowance=_money(psa),
        dividend_allowance=_money(dividend_allowance),
        uk_property_profit=_money(property_profit),
        uk_property_loss_to_carry_forward=_money(property_loss),
        foreign_property_profit=_money(foreign_profit) if foreign_profit is not None else None,
        foreign_tax_paid_recorded=_money(foreign_tax),
        included_families=tuple(included),
        unsupported_families=tuple(dict.fromkeys(unsupported)),
        limitations=tuple(limitations),
    ))


def _bind_annual_position_calculator(implementation, geography_admitter, issuer):
    def calculate_annual_position(
        facts: dict[str, Any], tax_year: str = "2026/27"
    ) -> AnnualPositionResult:
        return implementation(
            facts,
            tax_year,
            _geography_admitter=geography_admitter,
            _issuer=issuer,
        )

    return calculate_annual_position


calculate_annual_position = _bind_annual_position_calculator(
    _calculate_annual_position_impl,
    _enforce_geography_admission,
    _issue_annual_position,
)
del _bind_annual_position_calculator
del _calculate_annual_position_impl
