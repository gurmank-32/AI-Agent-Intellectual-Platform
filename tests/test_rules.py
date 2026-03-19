from __future__ import annotations

from core.compliance.parser import Clause
from core.compliance.rules import RuleEngine, RuleResult


def _make_clause(number: int, title: str, content: str) -> Clause:
    return Clause(number=number, title=title, content=content)


engine = RuleEngine()


def test_esa_fee_detected() -> None:
    clause = _make_clause(
        number=1,
        title="Pet Policy",
        content=(
            "Tenants must pay a $150 pet rent per month. "
            "Emotional Support Animals (ESA) are considered pets."
        ),
    )
    result = engine.analyze_clause(
        clause=clause, jurisdiction_id=1, jurisdiction_rules={}
    )
    assert result is not None
    assert isinstance(result, RuleResult)
    assert result.type == "ESA_FEE"
    assert "Fair Housing Act" in result.regulation_applies


def test_esa_exemption_missing() -> None:
    clause = _make_clause(
        number=2,
        title="Pet Fees",
        content=(
            "All tenants with pets must pay a $200 pet deposit and $50 monthly pet rent. "
            "No animals are allowed without prior written approval."
        ),
    )
    result = engine.analyze_clause(
        clause=clause, jurisdiction_id=1, jurisdiction_rules={}
    )
    assert result is not None
    assert isinstance(result, RuleResult)
    assert result.type in ("ESA_FEE", "MISSING_ESA_EXEMPTION")
    assert "Fair Housing Act" in result.regulation_applies


def test_compliant_clause() -> None:
    clause = _make_clause(
        number=3,
        title="Rent Payment",
        content=(
            "Monthly rent of $1,200 is due on the first of each month. "
            "Rent may be paid by check, money order, or electronic transfer."
        ),
    )
    result = engine.analyze_clause(
        clause=clause, jurisdiction_id=1, jurisdiction_rules={}
    )
    assert result is None


def test_deposit_timeline() -> None:
    clause = _make_clause(
        number=4,
        title="Security Deposit",
        content=(
            "The security deposit of $1,000 will be returned within 60 days "
            "after the tenant vacates the premises."
        ),
    )
    result = engine.analyze_clause(
        clause=clause,
        jurisdiction_id=1,
        jurisdiction_rules={"deposit_return_days": 30},
    )
    assert result is not None
    assert isinstance(result, RuleResult)
    assert result.type == "DEPOSIT_RETURN_TIMELINE"
    assert "30 days" in result.what_to_fix
