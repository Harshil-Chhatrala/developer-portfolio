"""Production Rule representation and condition evaluation logic."""

from typing import Dict, Any, List
from engine.reasoning import FactBase


class ProductionRule:
    """Encapsulates a single cybersecurity rule precondition and action logic."""

    def __init__(self, rule_data: Dict[str, Any]):
        self.rule_id: str = rule_data["rule_id"]
        self.name: str = rule_data["name"]
        self.priority: int = rule_data.get("priority", 1)
        self.conditions: Dict[str, List[str]] = rule_data["conditions"]
        self.conclusions: List[Dict[str, Any]] = rule_data["conclusions"]
        self.explanation: str = rule_data["explanation"]

    def evaluate(self, fact_base: FactBase) -> bool:
        """Evaluates boolean conditions against current FactBase state."""
        all_of = self.conditions.get("all_of", [])
        any_of = self.conditions.get("any_of", [])
        none_of = self.conditions.get("none_of", [])

        # Check 'all_of' requirement
        for fact in all_of:
            if not fact_base.has_fact(fact):
                return False

        # Check 'none_of' requirement
        for fact in none_of:
            if fact_base.has_fact(fact):
                return False

        # Check 'any_of' requirement if specified
        if any_of:
            has_any = any(fact_base.has_fact(fact) for fact in any_of)
            if not has_any:
                return False

        return True