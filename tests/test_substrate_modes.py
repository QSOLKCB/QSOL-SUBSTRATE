from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

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

    def test_hard_constraints_are_complete_and_policy_bound(self) -> None:
        geometry = self.load("geometry/mode-space-v1.json")
        axes = {axis["id"] for axis in geometry["axes"]}
        expected = {
            "LEGAL_BINDING_AUTHORITY": "modes/source-policy.json#profiles.LEGAL",
            "MEDICAL_CLINICAL_GUIDANCE": "modes/source-policy.json#profiles.MEDICAL.clinical",
            "HIGH_SAFETY_LOW_EVIDENCE": "ai/mode-contract.json#geometry",
            "CROSS_DOMAIN_BRIDGE": "bridges/index.json",
        }
        constraints = {item["id"]: item for item in geometry["hard_constraints"]}
        self.assertEqual(set(constraints), set(expected))
        for cid, item in constraints.items():
            self.assertEqual(item["policy_reference"], expected[cid])
            for mapping in (item["when"], item["require"]):
                for key, value in mapping.items():
                    if key.endswith("_min") or key.endswith("_max"):
                        axis = key[:-4]
                        self.assertIn(axis, axes)
                        self.assertGreaterEqual(value, geometry["range"]["min"])
                        self.assertLessEqual(value, geometry["range"]["max"])

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
        self.assertIn("current_clinical_guideline", medical["preferred_by_axis"]["authority_class"])
        self.assertIn("peer_review", doi["does_not_entitle"])
        self.assertIn("established_truth", doi["does_not_entitle"])

    def test_claim_maturity_is_separate_from_register_and_scenario(self) -> None:
        policy = self.load("modes/source-policy.json")
        contract = self.load("ai/epistemic-contract.json")
        maturity = set(policy["source_axes"]["claim_maturity"])
        register = set(policy["source_axes"]["register"])
        scenarios = set(policy["source_axes"]["scenario_status"])
        self.assertNotIn("FICTIONAL", maturity)
        self.assertNotIn("SATIRICAL", maturity)
        self.assertEqual(register, {"LITERAL", "FICTIONAL", "SATIRICAL"})
        self.assertEqual(scenarios, {"ACTUAL", "HYPOTHETICAL", "COUNTERFACTUAL"})
        self.assertEqual(set(contract["claim_maturity_states"]), maturity)
        self.assertEqual(set(contract["register_states"]), register)
        self.assertEqual(set(contract["scenario_states"]), scenarios)

    def test_epistemic_contract_has_strict_schema_coverage(self) -> None:
        contract = self.load("ai/epistemic-contract.json")
        schema = self.load("schema/epistemic-contract.schema.json")
        Draft202012Validator.check_schema(schema)
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(contract)), [])

    def test_source_preferences_are_axis_qualified(self) -> None:
        policy = self.load("modes/source-policy.json")
        axes = policy["source_axes"]

        def walk(node):
            if not isinstance(node, dict):
                return
            self.assertNotIn("preferred", node)
            self.assertNotIn("preferred_authority_classes", node)
            preferred = node.get("preferred_by_axis")
            if preferred is not None:
                for axis, values in preferred.items():
                    self.assertIn(axis, axes)
                    self.assertTrue(values)
                    self.assertTrue(set(values).issubset(set(axes[axis])))
            for key, value in node.items():
                if key != "preferred_by_axis" and isinstance(value, dict):
                    walk(value)

        walk(policy["profiles"])

    def test_mode_contract_is_in_portable_normative_manifest(self) -> None:
        manifest = self.load("ai/manifest.json")
        self.assertIn("ai/mode-contract.json", manifest["normative_machine_files"])

    def test_claim_strength_invariant_is_identical_across_contracts(self) -> None:
        contract = self.load("ai/mode-contract.json")
        policy = self.load("modes/source-policy.json")
        self.assertEqual(contract["core_invariant"], "CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT")
        self.assertEqual(policy["core_invariant"], contract["core_invariant"])


if __name__ == "__main__":
    unittest.main()
