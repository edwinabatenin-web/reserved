#!/usr/bin/env python3
"""Render the versioned synthetic W2 customer-language research gallery."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reserved.services.w2_customer_language import (  # noqa: E402
    CONTRACT_VERSION,
    AdjustmentFact,
    AdjustmentKind,
    ClaimToReduceState,
    EvidenceClassification,
    FundingClassification,
    ObligationFact,
    ObligationKind,
    PresentationStatus,
    W2PresentationInput,
    present_w2_customer_language,
)


FIXTURE = ROOT / "docs" / "fixtures" / "W2_CUSTOMER_LANGUAGE_RESEARCH_CASES.json"
FIXTURE_VERSION = "w2-customer-language-research-cases/1.0"
CASE_KEYS = {
    "id", "moderator_label", "status", "evidence", "annual_liability", "obligations",
    "adjustments", "funding", "funding_amount", "claim_to_reduce",
}
QUESTIONS = (
    "What, if anything, does this page tell you?",
    "Would you rely on any of these figures? Why or why not?",
    "What would you do next, if anything?",
    "Is any wording unclear or open to more than one interpretation?",
)


def _decimal(value: object, field: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a decimal string or null")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a decimal") from exc
    if not parsed.is_finite() or parsed < 0 or parsed.as_tuple().exponent != -2:
        raise ValueError(f"{field} must be a non-negative two-decimal amount")
    return parsed


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_fixture() -> dict:
    """Load and validate the sole, repository-versioned synthetic fixture."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    if not isinstance(data, dict):
        raise ValueError("fixture root must be an object")
    if set(data) != {"fixture_version", "synthetic", "production_use", "cases"}:
        raise ValueError("unexpected fixture fields")
    if data["fixture_version"] != FIXTURE_VERSION:
        raise ValueError("unsupported fixture version")
    if data["synthetic"] is not True or data["production_use"] is not False:
        raise ValueError("fixture must be explicitly synthetic and non-production")
    if not isinstance(data["cases"], list) or not data["cases"]:
        raise ValueError("fixture cases must be a non-empty list")
    ids = []
    for case in data["cases"]:
        if not isinstance(case, dict) or set(case) != CASE_KEYS:
            raise ValueError("unexpected case fields")
        if not isinstance(case["id"], str) or not case["id"]:
            raise ValueError("case id must be a non-empty string")
        if not isinstance(case["moderator_label"], str) or not case["moderator_label"]:
            raise ValueError("case moderator_label must be a non-empty string")
        ids.append(case["id"])
        _build_input(case)
    if len(ids) != len(set(ids)):
        raise ValueError("case ids must be unique")
    return data


def _build_input(case: dict) -> W2PresentationInput:
    if not isinstance(case["obligations"], list) or not isinstance(case["adjustments"], list):
        raise ValueError(f"invalid case {case.get('id', '<unknown>')}: facts must be lists")
    if any(
        not isinstance(item, dict) or set(item) != {"kind", "amount", "due_date"}
        for item in case["obligations"]
    ):
        raise ValueError(f"invalid case {case.get('id', '<unknown>')}: unexpected obligation fields")
    if any(
        not isinstance(item, dict) or set(item) != {"kind", "amount"}
        for item in case["adjustments"]
    ):
        raise ValueError(f"invalid case {case.get('id', '<unknown>')}: unexpected adjustment fields")
    try:
        status = PresentationStatus(case["status"])
        evidence = None if case["evidence"] is None else EvidenceClassification(case["evidence"])
        funding = None if case["funding"] is None else FundingClassification(case["funding"])
        claim = None if case["claim_to_reduce"] is None else ClaimToReduceState(case["claim_to_reduce"])
        due_dates = []
        for item in case["obligations"]:
            raw_due_date = item["due_date"]
            if not isinstance(raw_due_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_due_date):
                raise ValueError("due date must be an exact YYYY-MM-DD string")
            parsed_due_date = date.fromisoformat(raw_due_date)
            if parsed_due_date.isoformat() != raw_due_date:
                raise ValueError("due date must be a canonical YYYY-MM-DD string")
            due_dates.append(parsed_due_date)
        obligations = tuple(
            ObligationFact(
                ObligationKind(item["kind"]),
                _decimal(item["amount"], "obligation amount"),
                due_date,
            )
            for item, due_date in zip(case["obligations"], due_dates, strict=True)
        )
        adjustments = tuple(
            AdjustmentFact(
                AdjustmentKind(item["kind"]),
                _decimal(item["amount"], "adjustment amount"),
            )
            for item in case["adjustments"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid case {case.get('id', '<unknown>')}: {exc}") from exc
    presentation_input = W2PresentationInput(
        CONTRACT_VERSION, status, evidence, _decimal(case["annual_liability"], "annual liability"),
        obligations, adjustments, funding, _decimal(case["funding_amount"], "funding amount"), claim,
    )
    if status is PresentationStatus.READY and not present_w2_customer_language(presentation_input).safe_to_present:
        raise ValueError(f"invalid case {case['id']}: ready facts fail the presentation contract")
    return presentation_input


def _output_path(value: str | Path) -> Path:
    output = Path(value).expanduser().resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("output must be outside the repository")
    if output.exists():
        raise ValueError("output path must not already exist")
    if not output.parent.is_dir():
        raise ValueError("output parent directory must already exist")
    return output


def _select_cases(fixture: dict, case_ids: list[str] | tuple[str, ...]) -> list[tuple[str, dict]]:
    if not isinstance(case_ids, (list, tuple)) or not case_ids:
        raise ValueError("at least one explicit case id is required")
    if any(not isinstance(case_id, str) or not case_id for case_id in case_ids):
        raise ValueError("case ids must be non-empty strings")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("case ids must not be duplicated")
    by_id = {case["id"]: (index, case) for index, case in enumerate(fixture["cases"])}
    unknown = [case_id for case_id in case_ids if case_id not in by_id]
    if unknown:
        raise ValueError(f"unknown case id: {unknown[0]}")
    if len(case_ids) == len(by_id) and set(case_ids) != set(by_id):
        raise ValueError("full-gallery order must contain every case exactly once")
    if len(case_ids) > len(by_id):
        raise ValueError("too many case ids")
    return [(f"Case {chr(ord('A') + by_id[case_id][0])}", by_id[case_id][1]) for case_id in case_ids]


def render_gallery(output_path: str | Path, case_ids: list[str] | tuple[str, ...]) -> Path:
    """Render deterministically to an explicit path outside the repository."""
    output = _output_path(output_path)
    fixture = load_fixture()
    selected_cases = _select_cases(fixture, case_ids)
    environment = Environment(
        loader=FileSystemLoader(ROOT / "reserved" / "templates"),
        autoescape=select_autoescape(("html",)),
    )
    fragment = environment.get_template("v2/_w2_cash_obligations.html")
    cards = []
    for participant_label, case in selected_cases:
        body = fragment.render(model=present_w2_customer_language(_build_input(case)))
        neutral_id = participant_label.lower().replace(" ", "-")
        heading_id = f"w2-cash-heading-{neutral_id}"
        body = body.replace('aria-labelledby="w2-cash-heading"', f'aria-labelledby="{heading_id}"', 1)
        body = body.replace('id="w2-cash-heading"', f'id="{heading_id}"', 1)
        questions = "".join(f"<li>{escape(question)}</li>" for question in QUESTIONS)
        cards.append(
            f'<article data-case="{neutral_id}">'
            f'<p class="lab-label">Synthetic research case · Non-production</p>'
            f'<h2>{participant_label}</h2>{body}'
            f'<h3>Research questions</h3><ol>{questions}</ol></article>'
        )
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>W2 customer-language synthetic research gallery</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:76rem;margin:auto;padding:1rem}article{border:2px solid #555;border-radius:.5rem;margin:2rem 0;padding:1.25rem}.lab-label{font-weight:700;background:#ffed99;padding:.5rem}section{border-top:1px solid #aaa;margin-top:1rem}li{margin:.4rem 0}:focus{outline:3px solid #165dff}</style>
""" + f'</head><body data-selected-order="{",".join(label.lower().replace(" ", "-") for label, _ in selected_cases)}"><header><h1>W2 customer-language research gallery</h1><p><strong>Synthetic · Non-production · Research use only</strong></p><p>No case represents a real person, tax record or completed research session.</p></header>\n' + """
""" + "\n".join(cards) + "\n</body></html>\n"
    output.write_text(html, encoding="utf-8", newline="\n")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="HTML output path outside the repository")
    parser.add_argument("--case", dest="case_ids", action="append", required=True,
                        help="case id to render; repeat in the moderated presentation order")
    args = parser.parse_args(argv)
    try:
        render_gallery(args.output, args.case_ids)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
