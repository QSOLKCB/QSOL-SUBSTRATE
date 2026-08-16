import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = "ADJACENT_TRUTH != INHERITED_TRUTH"


class Phase9EpistemicGuardTests(unittest.TestCase):
    def test_adjacent_truth_guard_is_normative_machine_semantics(self):
        manifest = json.loads((ROOT / "ai/manifest.json").read_text(encoding="utf-8"))
        contract = json.loads((ROOT / "ai/epistemic-contract.json").read_text(encoding="utf-8"))

        self.assertIn("ai/epistemic-contract.json", manifest["normative_machine_files"])
        self.assertIn(GUARD, contract["rules"])

    def test_human_design_principle_explains_claim_local_evidence(self):
        text = (ROOT / "docs/DESIGN_PRINCIPLES.md").read_text(encoding="utf-8")

        self.assertIn(GUARD, text)
        self.assertIn("Every substantive claim must be evaluated against its own evidence", text)


if __name__ == "__main__":
    unittest.main()
