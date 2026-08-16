from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SubstrateModesTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_mode_validator_accepts_repository(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/validate_modes.py"), "--root", str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("VALID MODES", result.stdout)

    def test_geometry_is_exactly_24d_and_non_evidentiary(self) -> None:
        geometry = self.load("geometry/mode-space-v1.json")
        self.assertEqual(geometry["dimension_count"], 24)
        self.assertEqual(len(geometry["axes"]), 24)
        self.assertEqual([axis["index"] for axis in geometry["axes"]], list(range(1, 25)))
        self.assertEqual(geometry["classification"], "validation_geometry_not_evidence")
        self.assertIn("coordinates_do_not_prove_truth", geometry["validation_principles"])

    def test_every_bridge_uses_declared_modes(self) -> None:
        mode_ids = {mode["id"] for mode in self.load("modes/index.json")["modes"]}
        bridges = self.load("bridges/index.json")["bridges"]
        self.assertGreater(len(bridges), 0)
        for bridge in bridges:
            self.assertIn(bridge["from"], mode_ids)
            self.assertIn(bridge["to"], mode_ids)
            self.assertTrue(bridge["non_equivalences"])

    def test_high_stakes_source_guards_are_fail_closed(self) -> None:
        policy = self.load("modes/source-policy.json")
        legal = policy["profiles"]["LEGAL"]["binding_claim"]
        medical = policy["profiles"]["MEDICAL"]["clinical"]
        doi = policy["repository_doi_policy"]

        self.assertEqual(legal["required_authority_classes"], ["primary_legal_authority"])
        self.assertFalse(legal["secondary_authority_permitted_as_final_support"])
        self.assertFalse(medical["preprints_normative"])
        self.assertIn("current_clinical_guideline", medical["preferred_authority_classes"])
        self.assertIn("peer_review", doi["does_not_entitle"])
        self.assertIn("established_truth", doi["does_not_entitle"])

    def test_claim_strength_invariant_is_identical_across_contracts(self) -> None:
        contract = self.load("ai/mode-contract.json")
        policy = self.load("modes/source-policy.json")
        self.assertEqual(contract["core_invariant"], "CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT")
        self.assertEqual(policy["core_invariant"], contract["core_invariant"])


if __name__ == "__main__":
    unittest.main()
