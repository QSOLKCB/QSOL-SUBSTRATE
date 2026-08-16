import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import mixed_register_empirical as empirical


class Phase9EmpiricalTests(unittest.TestCase):
    def test_guard_ablation_is_narrow(self):
        source = "\n".join([
            "UNKNOWN != FALSE",
            "ADJACENT_TRUTH != INHERITED_TRUTH",
            "BOUNDARY\tproject:x\tSATIRE != BIOGRAPHY",
            "SATIRE != BIOGRAPHY",
            "FORMALIZATION != PHYSICAL_TRUTH",
            "KEEP_ME",
            "",
        ])
        ablated = empirical.ablate_local_guards(source)
        self.assertIn("UNKNOWN != FALSE", ablated)
        self.assertIn("KEEP_ME", ablated)
        self.assertNotIn("ADJACENT_TRUTH != INHERITED_TRUTH", ablated)
        self.assertNotIn("BOUNDARY\t", ablated)
        self.assertNotIn("SATIRE != BIOGRAPHY", ablated)
        self.assertNotIn("FORMALIZATION != PHYSICAL_TRUTH", ablated)

    def test_visible_evidence_refs_are_explicit_only(self):
        context = "\n".join([
            "ITEM\tproject\tprojects/index.json\t{\"source_refs\":[\"src:repo-qsol\"]}",
            "EVIDENCE_REF=file:identity/public.json",
            "SOURCE_REFS=src:identity-a,src:identity-b",
        ])
        refs = empirical.visible_evidence_refs(context)
        self.assertIn("file:projects/index.json", refs)
        self.assertIn("file:identity/public.json", refs)
        self.assertIn("src:repo-qsol", refs)
        self.assertIn("src:identity-a", refs)
        self.assertIn("src:identity-b", refs)

    def test_parse_consumer_output_requires_exact_claim_set(self):
        built = [
            {"id": "mr1-001", "text": "a", "expected": {"epistemic_status": "SUPPORTED", "register": "literal"}},
            {"id": "mr1-002", "text": "b", "expected": {"epistemic_status": "CONTRADICTED", "register": "literal"}},
        ]
        payload = {
            "claims": [{
                "claim_id": "mr1-001",
                "epistemic_status": "SUPPORTED",
                "register": "literal",
                "evidence_refs": [],
                "rationale": "x",
            }]
        }
        with self.assertRaises(empirical.EmpiricalError):
            empirical.parse_consumer_output(payload, built)

    def test_cold_consumer_gate_requires_unknown_restraint_and_all_classes(self):
        built = [
            {"id": "mr1-001", "expected": {"epistemic_status": "SUPPORTED", "register": "literal"}},
            {"id": "mr1-002", "expected": {"epistemic_status": "CONTRADICTED", "register": "literal"}},
            {"id": "mr1-003", "expected": {"epistemic_status": "UNAVAILABLE_UNVERIFIED", "register": "literal"}},
            {"id": "mr1-004", "expected": {"epistemic_status": "SUPPORTED", "register": "satire"}},
        ]
        audit = {
            "claims": [
                {"claim_id": "mr1-001", "epistemic_status": "SUPPORTED", "register": "literal"},
                {"claim_id": "mr1-002", "epistemic_status": "CONTRADICTED", "register": "literal"},
                {"claim_id": "mr1-003", "epistemic_status": "UNAVAILABLE_UNVERIFIED", "register": "literal"},
                {"claim_id": "mr1-004", "epistemic_status": "SUPPORTED", "register": "satire"},
            ]
        }
        report = {
            "metrics": {
                "primary_status_accuracy": 1.0,
                "register_accuracy": 1.0,
                "evidence_fidelity": 1.0,
                "unsupported_assertion_rate": 0.0,
            }
        }
        gate = empirical.cold_consumer_gate(built, audit, report)
        self.assertTrue(gate["passed"])

        failed = copy.deepcopy(report)
        failed["metrics"]["unsupported_assertion_rate"] = 0.25
        self.assertFalse(empirical.cold_consumer_gate(built, audit, failed)["passed"])

    def test_experiment_summary_reports_guard_deltas_without_claiming_causality(self):
        identity = empirical.ModelIdentity("ollama-local", "demo", "sha256:abc")
        manifest = {
            "bundle_sha256": "a" * 64,
            "substrate": {
                "protocol": "QSOL-SUBSTRATE",
                "version": "snapshot-2026-08-16",
                "version_kind": "snapshot",
                "schema_version": "1.0.0",
                "snapshot_date": "2026-08-16",
                "source_commit": "b" * 40,
                "substrate_sha256": "c" * 64,
            },
        }
        results = []
        for condition in empirical.CONDITIONS:
            for variant, status_acc, unsupported in (
                ("guarded", 0.9, 0.0),
                ("ablated", 0.7, 0.25),
            ):
                results.append({
                    "condition": condition,
                    "variant": variant,
                    "report": {"metrics": {
                        "primary_status_accuracy": status_acc,
                        "register_accuracy": 0.9 if variant == "guarded" else 0.8,
                        "evidence_fidelity": 0.8 if variant == "guarded" else 0.6,
                        "unsupported_assertion_rate": unsupported,
                    }},
                    "cold_consumer_gate": {"passed": variant == "guarded"},
                })
        summary = empirical.experiment_summary(results, manifest, identity)
        self.assertTrue(summary["cold_consumer_demonstrated"])
        self.assertEqual(summary["passing_guarded_conditions"], list(empirical.CONDITIONS))
        for row in summary["rows"]:
            self.assertEqual(row["guard_effect"]["primary_status_accuracy_delta"], 0.2)
            self.assertEqual(row["guard_effect"]["unsupported_assertion_rate_reduction"], 0.25)
        self.assertIn("do not by themselves establish", summary["interpretation"])


if __name__ == "__main__":
    unittest.main()
