"""C1 regression: HICBC is isolated from all customer-facing surfaces (post-v1).

HICBC must not appear in any customer estimated total, reserve, scenario,
personalised warning or API payload.  The post-v1 HICBC arithmetic may remain
internally, but a supported customer position must never expose it.
"""
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_optimise_template_does_not_surface_a_hicbc_charge():
    t = _text("reserved/templates/v2/optimise.html")
    assert "HICBC estimate" not in t
    assert "r-before-hicbc" not in t
    assert "Income tax + HICBC" not in t
    # The page still discloses Child Benefit as an excluded input.
    assert "Child Benefit" in t


def test_optimise_js_does_not_reference_hicbc():
    js = _text("reserved/static/js/optimise.js").lower()
    assert "hicbc" not in js


def test_optimise_calculate_api_has_no_hicbc_payload_key():
    src = _text("reserved/web/v2.py")
    assert 'opportunity_id == "HICBC"' in src
    assert '"hicbc"' not in src  # no lower-case JSON key is ever emitted


def test_settings_template_removes_customer_child_benefit_inputs():
    s = _text("reserved/templates/v2/settings.html")
    assert "child_benefit_children" not in s
    assert "child_benefit_annual" not in s
    assert "High Income Child Benefit Charge" not in s


def test_internal_hicbc_arithmetic_is_isolated_not_deleted():
    from reserved.engines.optimise import _hicbc

    # One child at ANI £70,000: 50% of the floored £1,383.20 award → £691.
    assert _hicbc(Decimal("70000"), Decimal("1383.20")) == Decimal("691")
