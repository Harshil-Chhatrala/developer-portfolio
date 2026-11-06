"""Working memory and fact structure for inference process."""

from typing import Set, Dict, Any, List


class FactBase:
    """Maintains active working memory facts and aggregated evidence during reasoning."""

    def __init__(self, initial_observations: List[str]):
        self.facts: Set[str] = set(initial_observations)
        self.evidence_scores: Dict[str, float] = {}

    def add_fact(self, fact_id: str) -> bool:
        """Asserts a new fact into working memory. Returns True if fact was new."""
        if fact_id not in self.facts:
            self.facts.add(fact_id)
            return True
        return False

    def has_fact(self, fact_id: str) -> bool:
        return fact_id in self.facts

    def add_evidence(self, attack_id: str, weight: float) -> None:
        """Accumulates evidence weight using asymptotic probability formula: C = 1 - (1 - C_old)*(1 - w)."""
        current = self.evidence_scores.get(attack_id, 0.0)
        updated = 1.0 - ((1.0 - current) * (1.0 - weight))
        self.evidence_scores[attack_id] = round(updated, 4)

    def get_all_facts(self) -> Set[str]:
        return set(self.facts)

    def get_evidence_scores(self) -> Dict[str, float]:
        return dict(self.evidence_scores)