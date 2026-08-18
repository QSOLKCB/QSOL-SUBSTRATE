from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from mixed_register_empirical_closure import (  # noqa: E402
    CONDITIONS,
    adjacency_trap_ids,
    build_closure,
)


class Phase9EmpiricalClosureTests(unittest.TestCase):
    def claims(self):
        rows = []
        for line in (ROOT / "probe/mixed-register-1.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def audit(self, claims, *, ablated=False):
        trap_ids = adjacency_trap_ids(claims)
        changed = trap_ids[0]
        rows = []
        for claim in claims:
            expected = claim["expected"]
            status = expected["epistemic_status"]
            refs = list(expected.get("evidence_refs", []))
            if ablated and claim["id"] == changed:
                status = "SUPPORTED"
                refs = ["file:identity/public.json"]
            rows.append({
                "claim_id": claim["id"],
                "epistemic_status": status,
                "register": expected["register"],
                "evidence_refs": refs,
                "rationale": "synthetic deterministic fixture",
            })
        return {"claims": rows}

    def write_fixture(self, empirical_dir: Path):
        claims = self.claims()
        summary = {
            "type": "qsol-mixed-register-empirical-summary",
            "schema_version": "1.0.0",
            "empirical_spec_version": "1.0.0",
            "artifact_class": "derived_evaluation",
            "canonical_truth_authority": False,
            "evaluation_bundle_sha256": "b" * 64,
            "substrate": {},
            "model": {
                "provider": "fixture",
                "model_id": "fixture-model",
                "immutable_model_revision": "fixture-revision",
            },
            "conditions": list(CONDITIONS),
            "variants": ["guarded", "ablated"],
            "rows": [],
            "cold_consumer_demonstrated": True,
            "passing_guarded_conditions": list(CONDITIONS),
            "source_commit": "a" * 40,
        }
        for condition in CONDITIONS:
            summary["rows"].append({
                "condition": condition,
                "guard_effect": {
                    "primary_status_accuracy_delta": 0.033333,
                    "register_accuracy_delta": 0.0,
                    "evidence_fidelity_delta": 0.033333,
                    "unsupported_assertion_rate_reduction": 0.033333,
                },
                "cold_consumer_gate": {"passed": True},
            })
            audits = empirical_dir / "audits"
            audits.mkdir(parents=True, exist_ok=True)
            (audits / f"{condition}.guarded.json").write_text(
                json.dumps(self.audit(claims, ablated=False)), encoding="utf-8"
            )
            (audits / f"{condition}.ablated.json").write_text(
                json.dumps(self.audit(claims, ablated=True)), encoding="utf-8"
            )
        (empirical_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    def test_adjacency_traps_are_derived_from_mixed_paragraphs(self):
        trap_ids = adjacency_trap_ids(self.claims())
        self.assertEqual(len(trap_ids), 16)
        self.assertIn("mr1-002", trap_ids)
        self.assertIn("mr1-030", trap_ids)
        self.assertNotIn("mr1-001", trap_ids)

    def test_closure_detects_guard_improvement_and_strict_cold_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            empirical_dir = Path(tmp) / "empirical"
            empirical_dir.mkdir()
            self.write_fixture(empirical_dir)
            closure = build_closure(ROOT, empirical_dir)

        self.assertEqual(closure["guard_effect_conclusion"], "improved")
        self.assertTrue(closure["local_guards_improved_in_any_condition"])
        self.assertTrue(closure["local_guards_consistent_non_degradation"])
        self.assertTrue(closure["cold_consumer_classification_demonstrated"])
        self.assertEqual(closure["strict_passing_guarded_conditions"], list(CONDITIONS))
        for row in closure["rows"]:
            self.assertEqual(row["guard_effect_classification"], "improved")
            self.assertTrue(row["strict_cold_consumer_gate"]["passed"])
            self.assertGreater(row["guard_effect"]["adjacency_false_support_rate_reduction"], 0)

    def test_closure_schema_accepts_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            empirical_dir = Path(tmp) / "empirical"
            empirical_dir.mkdir()
            self.write_fixture(empirical_dir)
            closure = build_closure(ROOT, empirical_dir)
        schema = json.loads(
            (ROOT / "schema/mixed-register-empirical-closure.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(closure))
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
