import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import adapter_core
import mixed_register_core
import projection_core
import toolless_core


class Phase9MixedRegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self.tmp.name) / "mixed-register-1"
        self.source_commit = "a" * 40
        self.manifest = mixed_register_core.build_mixed_register_bundle(ROOT, self.bundle, self.source_commit)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bundle_is_deterministic_and_valid(self):
        self.assertEqual(self.manifest["claim_count"], 30)
        self.assertEqual(len(self.manifest["expected_claim_ids"]), 30)
        self.assertEqual(len(set(self.manifest["expected_claim_ids"])), 30)
        self.assertEqual(mixed_register_core.validate_mixed_register_bundle(ROOT, self.bundle), [])
        with tempfile.TemporaryDirectory() as other:
            second = mixed_register_core.build_mixed_register_bundle(ROOT, Path(other) / "mixed", self.source_commit)
            self.assertEqual(self.manifest, second)

    def test_oracle_self_test_is_perfect_but_non_empirical(self):
        audit = mixed_register_core.build_scoring_oracle_audit(ROOT, self.bundle)
        report = mixed_register_core.score_claim_audit(ROOT, self.bundle, audit)
        self.assertEqual(report["execution_kind"], "scoring_oracle")
        self.assertEqual(report["metrics"]["overall_accuracy"], 1.0)
        self.assertEqual(report["metrics"]["unsupported_assertion_rate"], 0.0)
        with self.assertRaises(mixed_register_core.MixedRegisterError):
            mixed_register_core.compare_mixed_register_reports([report, copy.deepcopy(report)])

    def test_summary_is_derived_not_trusted(self):
        audit = mixed_register_core.build_scoring_oracle_audit(ROOT, self.bundle)
        audit["summary"]["primary_class_counts"]["SUPPORTED"] += 1
        codes = [finding.code for finding in mixed_register_core.validate_claim_audit(ROOT, self.bundle, audit)]
        self.assertIn("audit.summary", codes)

    def test_missing_extra_and_duplicate_claims_fail_closed(self):
        audit = mixed_register_core.build_scoring_oracle_audit(ROOT, self.bundle)
        missing = copy.deepcopy(audit)
        missing["claims"].pop()
        missing["summary"] = mixed_register_core._derived_summary(missing["claims"])
        self.assertIn("audit.claim_set", [f.code for f in mixed_register_core.validate_claim_audit(ROOT, self.bundle, missing)])

        duplicate = copy.deepcopy(audit)
        duplicate["claims"][-1] = copy.deepcopy(duplicate["claims"][0])
        duplicate["summary"] = mixed_register_core._derived_summary(duplicate["claims"])
        codes = [f.code for f in mixed_register_core.validate_claim_audit(ROOT, self.bundle, duplicate)]
        self.assertIn("audit.duplicate_claim", codes)
        self.assertIn("audit.claim_set", codes)

    def test_evaluation_cannot_cite_itself_as_factual_evidence(self):
        audit = mixed_register_core.build_scoring_oracle_audit(ROOT, self.bundle)
        audit["claims"][0]["evidence_refs"].append("eval:this-report")
        codes = [finding.code for finding in mixed_register_core.validate_claim_audit(ROOT, self.bundle, audit)]
        self.assertIn("audit.self_evidence", codes)

    def test_model_revision_drift_is_rejected(self):
        audit = mixed_register_core.build_scoring_oracle_audit(ROOT, self.bundle)
        audit["execution_kind"] = "empirical_consumer"
        audit["run_id"] = "empirical-a"
        report_a = mixed_register_core.score_claim_audit(ROOT, self.bundle, audit)
        second = copy.deepcopy(audit)
        second["run_id"] = "empirical-b"
        second["condition"] = "micro"
        second["evaluator"]["immutable_model_revision"] = "different-revision"
        report_b = mixed_register_core.score_claim_audit(ROOT, self.bundle, second)
        with self.assertRaises(mixed_register_core.MixedRegisterError):
            mixed_register_core.compare_mixed_register_reports([report_a, report_b])

    def test_adjacent_truth_guard_survives_deterministic_delivery_surfaces(self):
        guard = "ADJACENT_TRUTH != INHERITED_TRUTH"
        self.assertIn(guard, toolless_core.CORE_GUARDS)
        self.assertIn(guard, projection_core.EPISTEMIC_RULES)
        source_manifest = json.loads((ROOT / "ai/manifest.json").read_text(encoding="utf-8"))
        self.assertIn(guard, adapter_core._projection_body(ROOT, source_manifest))
        conditions = json.loads((ROOT / "probe/conditions.json").read_text(encoding="utf-8"))
        self.assertIn(guard, conditions["epistemic_guards"])

    def test_local_nonclaim_boundaries_are_derived_from_canonical_records(self):
        identity = json.loads((ROOT / "identity/public.json").read_text(encoding="utf-8"))
        org = next(record for record in identity["records"] if record["id"] == "org:qsol-imc")
        org_item = toolless_core.CapsuleItem("org:qsol-imc", "organization", "identity/public.json", org, 0)
        self.assertIn("UNASSERTED_LEGAL_OR_CORPORATE_STATUS != FALSE", toolless_core._boundary_guards(org_item))

        projects = json.loads((ROOT / "projects/index.json").read_text(encoding="utf-8"))
        wrapper = toolless_core._wrapper_payload(projects)
        wrapper_item = toolless_core.CapsuleItem("wrapper:projects/index.json", "wrapper", "projects/index.json", wrapper, 1)
        self.assertIn("REGISTRY_OMISSION != NEGATIVE_FACT", toolless_core._boundary_guards(wrapper_item))

    def test_self_publication_chain_is_canonical_and_unique(self):
        sources = json.loads((ROOT / "sources/index.json").read_text(encoding="utf-8"))["sources"]
        publications = json.loads((ROOT / "publications/index.json").read_text(encoding="utf-8"))["records"]
        edges = json.loads((ROOT / "relationships/graph.json").read_text(encoding="utf-8"))["edges"]
        source = [item for item in sources if item.get("id") == "src:qsol-substrate-v1.0.0-release"]
        publication = [item for item in publications if item.get("id") == "publication:qsol-substrate-v1.0.0"]
        edge = [item for item in edges if item.get("id") == "rel:qsol-substrate-publishes-qsol-substrate-v1.0.0"]
        self.assertEqual(len(source), 1)
        self.assertEqual(len(publication), 1)
        self.assertEqual(len(edge), 1)
        self.assertEqual(publication[0]["doi"], "10.5281/zenodo.21959180")
        self.assertEqual(publication[0]["source_refs"], [source[0]["id"]])
        self.assertEqual(edge[0]["target"], publication[0]["id"])


if __name__ == "__main__":
    unittest.main()
