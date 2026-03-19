from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel

from core.compliance.parser import Clause

_MONEY_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)")
_DAYS_RE = re.compile(r"(\d+)\s+days?", re.IGNORECASE)

_PET_FEE_TERMS = (
    "pet fee",
    "pet rent",
    "pet deposit",
    "animal fee",
)
_ESA_TERMS = (
    "emotional support animal",
    "support animal",
    "service animal",
    "esa",
)
_EXEMPTION_TERMS = (
    "exempt",
    "exemption",
    "waived",
    "no pet fee for service animals",
    "no pet fee for esas",
)


class RuleResult(BaseModel):
    type: str
    regulation_applies: str
    what_to_fix: str
    suggested_revision: Optional[str] = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _extract_money_amounts(text: str) -> list[float]:
    return [float(match) for match in _MONEY_RE.findall(text)]


def _extract_days(text: str) -> list[int]:
    return [int(match) for match in _DAYS_RE.findall(text)]


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _has_pet_fee(text: str) -> bool:
    return _contains_any(text, _PET_FEE_TERMS) or any(
        amount >= 150 for amount in _extract_money_amounts(text)
    )


def _has_esa_reference(text: str) -> bool:
    return _contains_any(text, _ESA_TERMS)


def _has_exemption_language(text: str) -> bool:
    return _contains_any(text, _EXEMPTION_TERMS) or (
        _has_esa_reference(text) and "exempt" in text
    )


class RuleEngine:
    def analyze_clause(
        self, clause: Clause, jurisdiction_id: int, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = jurisdiction_id
        text = _normalize(f"{clause.title}\n{clause.content}")

        for check in (
            self._check_esa_fee_violation,
            self._check_missing_esa_exemption,
            self._check_deposit_return_timeline,
            self._check_unreasonable_late_fee,
            self._check_rent_increase_cap,
            self._check_required_disclosures,
        ):
            result = check(text=text, clause=clause, jurisdiction_rules=jurisdiction_rules)
            if result is not None:
                return result
        return None

    def _check_esa_fee_violation(
        self, text: str, clause: Clause, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = clause, jurisdiction_rules
        pet_fee_present = _has_pet_fee(text)
        esa_mentioned = _has_esa_reference(text)
        exemption_missing = not _has_exemption_language(text)

        if pet_fee_present and (esa_mentioned or exemption_missing):
            return RuleResult(
                type="ESA_FEE",
                regulation_applies="Fair Housing Act + HUD Assistance Animals Guidance",
                what_to_fix=(
                    "Remove all fees for ESAs/service animals. Add explicit exemption language."
                ),
                suggested_revision=(
                    "Emotional Support Animals and Service Animals are not pets and are "
                    "exempt from all pet fees, deposits, and pet rent under the Fair Housing Act."
                ),
            )
        return None

    def _check_missing_esa_exemption(
        self, text: str, clause: Clause, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = clause, jurisdiction_rules
        if _has_pet_fee(text) and not _has_esa_reference(text) and not _has_exemption_language(text):
            return RuleResult(
                type="MISSING_ESA_EXEMPTION",
                regulation_applies="Fair Housing Act + HUD Assistance Animals Guidance",
                what_to_fix=(
                    "Add language explicitly exempting ESAs and Service Animals from all pet fees."
                ),
                suggested_revision=(
                    "Emotional Support Animals and Service Animals are not pets and are "
                    "exempt from pet fees, deposits, and pet rent."
                ),
            )
        return None

    def _check_deposit_return_timeline(
        self, text: str, clause: Clause, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = clause
        if "security deposit" not in text:
            return None

        days = _extract_days(text)
        if not days:
            return None

        required_days_raw = jurisdiction_rules.get("deposit_return_days")
        required_days = int(required_days_raw) if required_days_raw is not None else 30
        stated_days = max(days)

        if stated_days > required_days:
            return RuleResult(
                type="DEPOSIT_RETURN_TIMELINE",
                regulation_applies="State security deposit return law",
                what_to_fix=f"Change return timeline to {required_days} days per state law.",
                suggested_revision=(
                    f"The security deposit will be returned within {required_days} days "
                    "after move-out, subject to lawful deductions."
                ),
            )
        return None

    def _check_unreasonable_late_fee(
        self, text: str, clause: Clause, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = clause, jurisdiction_rules
        if "late fee" not in text:
            return None

        amounts = _extract_money_amounts(text)
        if any(amount >= 100 for amount in amounts):
            return RuleResult(
                type="LATE_FEE",
                regulation_applies="State landlord-tenant law on reasonable late fees",
                what_to_fix="Ensure late fees are reasonable. Many states cap late fees.",
                suggested_revision=(
                    "Late fees must be reasonable and comply with applicable state and local law."
                ),
            )
        return None

    def _check_rent_increase_cap(
        self, text: str, clause: Clause, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = clause
        if "rent increase" not in text and "increase the rent" not in text:
            return None

        cap = jurisdiction_rules.get("rent_increase_cap")
        if cap is None:
            return None

        amounts = _extract_money_amounts(text)
        if len(amounts) < 2:
            return None

        old_rent, new_rent = amounts[0], amounts[1]
        if old_rent <= 0:
            return None

        increase_pct = ((new_rent - old_rent) / old_rent) * 100
        cap_value = float(cap)

        if increase_pct > cap_value:
            return RuleResult(
                type="RENT_INCREASE_CAP",
                regulation_applies="Applicable rent stabilization / rent cap law",
                what_to_fix=(
                    f"Reduce the rent increase so it does not exceed the jurisdictional cap of {cap_value:g}%."
                ),
                suggested_revision=(
                    f"Any rent increase must comply with the jurisdictional cap of {cap_value:g}%."
                ),
            )
        return None

    def _check_required_disclosures(
        self, text: str, clause: Clause, jurisdiction_rules: dict[str, Any]
    ) -> RuleResult | None:
        _ = jurisdiction_rules
        title = _normalize(clause.title)
        if "disclosure" not in title and "notice" not in title:
            return None

        missing: list[str] = []
        required_checks = {
            "repair rights": ("repair rights", "repair and deduct", "repairs"),
            "smoke alarm": ("smoke alarm", "smoke detector"),
            "carbon monoxide": ("carbon monoxide", "co detector", "co alarm"),
        }
        for label, terms in required_checks.items():
            if not any(term in text for term in terms):
                missing.append(label)

        if missing:
            joined = ", ".join(missing)
            return RuleResult(
                type="REQUIRED_DISCLOSURES",
                regulation_applies="State and local required disclosure laws",
                what_to_fix=f"Add missing disclosure topics: {joined}.",
                suggested_revision=(
                    f"This disclosure must also address the following topics: {joined}."
                ),
            )
        return None


rule_engine = RuleEngine()

