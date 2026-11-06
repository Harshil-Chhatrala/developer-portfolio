"""Automated unit and integration test suite for the expert system."""

import unittest
from pathlib import Path
import sys

# Ensure root directory is on import path
sys.path.append(str(Path(__file__).parent.parent))

from knowledge.knowledge_base import KnowledgeBase
from engine.inference_engine import InferenceEngine


class TestCyberExpertSystem(unittest.TestCase):

    def setUp(self):
        self.kb = KnowledgeBase()
        self.engine = InferenceEngine(self.kb)

    def test_ransomware_clear_diagnosis(self):
        """Test unambiguous ransomware scenario."""
        obs = ["IND_FILE_EXTENSION_CHANGED", "IND_RANSOM_NOTE_FOUND", "IND_SYS_SHADOW_COPIES_DELETED"]
        res = self.engine.run(obs)
        self.assertFalse(res["insufficient_evidence"])
        self.assertEqual(res["diagnoses"][0]["attack_id"], "ATTACK_RANSOMWARE")
        self.assertGreaterEqual(res["diagnoses"][0]["confidence"], 0.80)

    def test_insufficient_evidence(self):
        """Test system behavior when observations do not yield high confidence."""
        obs = ["IND_SYS_HIGH_CPU_GPU_USAGE"]  # Single non-specific symptom
        res = self.engine.run(obs)
        self.assertTrue(res["insufficient_evidence"])

    def test_competing_hypotheses(self):
        """Test scenario with overlapping network indicators."""
        obs = ["IND_NET_HIGH_OUTBOUND_TRAFFIC", "IND_NET_SUSPICIOUS_C2_IP", "IND_WEB_SQL_SYNTAX_IN_LOGS"]
        res = self.engine.run(obs)
        self.assertFalse(res["insufficient_evidence"])
        # Should detect C2 exfiltration or SQLi with strong confidence
        attack_ids = [d["attack_id"] for d in res["diagnoses"]]
        self.assertIn("ATTACK_C2_EXFILTRATION", attack_ids)


if __name__ == "__main__":
    unittest.main()