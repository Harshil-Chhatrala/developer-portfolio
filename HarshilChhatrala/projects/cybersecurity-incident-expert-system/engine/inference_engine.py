"""Forward-chaining inference engine execution controller."""

from typing import Dict, Any, List
from knowledge.knowledge_base import KnowledgeBase
from engine.reasoning import FactBase
from engine.rule_engine import ProductionRule


class InferenceEngine:
    """Executes forward chaining, asserts facts, tallies evidence, and builds explanation trace."""

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.rules = [ProductionRule(r) for r in kb.rules]
        # Sort rules by priority high to low
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def run(self, initial_observations: List[str]) -> Dict[str, Any]:
        fact_base = FactBase(initial_observations)
        explanation_trace: List[Dict[str, Any]] = []
        fired_rules: List[str] = []

        changed = True
        iterations = 0
        max_iterations = 20  # Prevent infinite loops in rule recursion

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            for rule in self.rules:
                if rule.rule_id in fired_rules:
                    continue

                if rule.evaluate(fact_base):
                    # Fire Rule
                    fired_rules.append(rule.rule_id)
                    changed = True

                    trace_entry = {
                        "iteration": iterations,
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "explanation": rule.explanation,
                        "asserted_facts": [],
                        "evidence_added": []
                    }

                    for conclusion in rule.conclusions:
                        c_type = conclusion.get("type")
                        if c_type == "ASSERT_FACT":
                            new_fact = conclusion["fact"]
                            if fact_base.add_fact(new_fact):
                                trace_entry["asserted_facts"].append(new_fact)

                        elif c_type == "HYPOTHESIS_EVIDENCE":
                            attack_id = conclusion["attack_id"]
                            weight = conclusion["weight"]
                            fact_base.add_evidence(attack_id, weight)
                            trace_entry["evidence_added"].append({
                                "attack_id": attack_id,
                                "weight": weight,
                                "total_confidence": fact_base.get_evidence_scores()[attack_id]
                            })

                    explanation_trace.append(trace_entry)

        # Structure Diagnostic Conclusions
        raw_evidence = fact_base.get_evidence_scores()
        diagnoses = []

        for attack_id, conf in raw_evidence.items():
            attack_info = self.kb.get_attack(attack_id)
            if not attack_info:
                continue

            base_sev = attack_info.get("base_severity", 0.5)
            # Dynamic Risk Calculation
            risk_score = round(conf * base_sev, 4)

            if risk_score >= 0.81:
                severity_label = "CRITICAL"
            elif risk_score >= 0.56:
                severity_label = "HIGH"
            elif risk_score >= 0.31:
                severity_label = "MEDIUM"
            else:
                severity_label = "LOW"

            diagnoses.append({
                "attack_id": attack_id,
                "name": attack_info.get("name", attack_id),
                "category": attack_info.get("category", "General"),
                "confidence": conf,
                "base_severity": base_sev,
                "risk_score": risk_score,
                "risk_label": severity_label,
                "description": attack_info.get("description", ""),
                "recommendations": self.kb.get_recommendations(attack_id)
            })

        # Sort diagnoses by confidence score descending
        diagnoses.sort(key=lambda x: x["confidence"], reverse=True)

        # Apply Insufficient Evidence Threshold (0.35)
        insufficient_evidence = False
        if not diagnoses or diagnoses[0]["confidence"] < 0.35:
            insufficient_evidence = True

        return {
            "initial_observations": initial_observations,
            "final_facts": list(fact_base.get_all_facts()),
            "fired_rules_count": len(fired_rules),
            "explanation_trace": explanation_trace,
            "diagnoses": diagnoses,
            "insufficient_evidence": insufficient_evidence
        }