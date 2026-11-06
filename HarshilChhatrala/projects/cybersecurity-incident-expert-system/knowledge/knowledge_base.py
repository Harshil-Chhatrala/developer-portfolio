"""Knowledge Base loader and manager interface."""

import json
from pathlib import Path
from typing import Dict, List, Any


class KnowledgeBase:
    """Manages cybersecurity indicators, attack definitions, rules, and recommendations."""

    def __init__(self, base_path: Path = None):
        if base_path is None:
            base_path = Path(__file__).parent
        self.base_path = base_path
        self.indicators: Dict[str, Any] = {}
        self.attacks: Dict[str, Any] = {}
        self.recommendations: Dict[str, List[str]] = {}
        self.rules: List[Dict[str, Any]] = []
        self.load_all()

    def load_all(self) -> None:
        """Loads all JSON knowledge files into memory."""
        with open(self.base_path / "indicators.json", "r", encoding="utf-8") as f:
            self.indicators = json.load(f)

        with open(self.base_path / "attacks.json", "r", encoding="utf-8") as f:
            self.attacks = json.load(f)

        with open(self.base_path / "recommendations.json", "r", encoding="utf-8") as f:
            self.recommendations = json.load(f)

        with open(self.base_path / "rules.json", "r", encoding="utf-8") as f:
            self.rules = json.load(f)

    def get_indicator_categories(self) -> Dict[str, List[Dict[str, str]]]:
        return self.indicators.get("categories", {})

    def get_all_indicator_ids(self) -> List[str]:
        ids = []
        for cat, items in self.get_indicator_categories().items():
            for item in items:
                ids.append(item["id"])
        return ids

    def get_attack(self, attack_id: str) -> Dict[str, Any]:
        return self.attacks.get(attack_id, {})

    def get_recommendations(self, attack_id: str) -> List[str]:
        return self.recommendations.get(attack_id, [
            "Initiate standard incident response triage protocol.",
            "Isolate host and perform forensic memory analysis."
        ])