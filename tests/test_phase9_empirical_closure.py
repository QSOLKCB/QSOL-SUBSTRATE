from __future__ import annotations

import hashlib
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
    EmpiricalClosureError,
    adjacency_trap_ids,
    build_closure,
)


class Phase9EmpiricalClosureTests(unittest.TestCase):
    BUNDLE_SHA = "b" * 64
    SOURCE_COMMIT = "a" * 40
    MODEL = {
        "provider": "fixture",
        "model_id": "fixture-model",
        "immutable_model_revision": "fixture-revision",
    }
    SUBSTRATE = {
        "protocol": "QSOL-SUBSTRATE",
        "version": "snapshot-2026-08-15",
        "snapshot_date": "2026-08-15",
        "source_commit": SOURCE_COMMIT,
        "substrate_sha256": "c" * 64,
    }

    def claims(self):
        rows = []
        for line in (ROOT / "probe/mixed-register-1.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def claim_rows(self, claims, *, ablated=False):
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
        return rows

    @staticmethod
    def binding(root: Path, relative: str):
        path = root / relative
        data = path.read_bytes()
        return {
            "path": relative,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }

    def write_fixture(self, empirical_dir: Path):
        claims = self.claims()
        summary = {
            "type": "qsol-mixed-register-empirical-summary",
            "schema_version": "1.0.0",
            "empirical_spec_version": "1.0.0",
            "artifact_class": "derived_evaluation",
            "canonical_truth_authority": False,
            "evaluation_bundle_sha256": self.BUNDLE_SHA,
            "substrate": self.SUBSTRATE,
            "model": self.MODEL,
            "conditions": list(CONDITIONS),
            "variants": ["guarded", "ablated"],
            "rows": [],
            "cold_consumer_demonstrated": True,
            "passing_guarded_conditions": list(CONDITIONS),
            "source_commit": self.SOURCE_COMMIT,
            "artifact_bindings": {},
        }

        for condition in CONDITIONS:
            condition_bindings = {}
            metrics = {
                "guarded": {
                    "overall_accuracy": 1.0,
                    "primary_status_accuracy": 1.0,
                    "register_accuracy": 1.0,
                    "evidence_fidelity": 1.0,
                    "unsupported_assertion_rate": 0.0,
                },
                "ablated": {
                    "overall_accuracy": 0.966667,
                    "primary_status_accuracy": 0.966667,
                    "register_accuracy": 1.0,
                    "evidence_fidelity": 0.966667,
                    "unsupported_assertion_rate": 0.083333,
                },
            }
            summary["rows"].append({
                "condition": condition,
                "guarded": metrics["guarded"],
                "ablated": metrics["ablated"],
                "guard_effect": {
                    "primary_status_accuracy_delta": 0.033333,
                    "register_accuracy_delta": 0.0,
                    "evidence_fidelity_delta": 0.033333,
                    "unsupported_assertion_rate_reduction": 0.083333,
                },
                "cold_consumer_gate": {"passed": True},
            })

            for variant in ("guarded", "ablated"):
                stem = f"{condition}.{variant}"
                prompt_rel = f"prompts/{stem}.txt"
                carrier_rel = f"carriers/{stem}.txt"
                raw_rel = f"raw/{stem}.response.json"
                audit_rel = f"audits/{stem}.json"
                report_rel = f"reports/{stem}.json"

                (empirical_dir / prompt_rel).parent.mkdir(parents=True, exist_ok=True)
                (empirical_dir / prompt_rel).write_text(f"prompt:{stem}\n", encoding="utf-8")
                (empirical_dir / carrier_rel).parent.mkdir(parents=True, exist_ok=True)
                (empirical_dir / carrier_rel).write_text(f"carrier:{stem}\n", encoding="utf-8")
                (empirical_dir / raw_rel).parent.mkdir(parents=True, exist_ok=True)
                (empirical_dir / raw_rel).write_text(
                    json.dumps({"claims": []}, separators=(",", ":")), encoding="utf-8"
                )

                prompt_sha = hashlib.sha256((empirical_dir / prompt_rel).read_bytes()).hexdigest()
                carrier_sha = hashlib.sha256((empirical_dir / carrier_rel).read_bytes()).hexdigest()
                raw_sha = hashlib.sha256((empirical_dir / raw_rel).read_bytes()).hexdigest()

                audit = {
                    "type": "qsol-claim-audit",
                    "schema_version": "1.0.0",
                    "artifact_class": "derived_evaluation",
                    "execution_kind": "empirical_consumer",
                    "run_id": f"mixed-register-cold:{self.MODEL['model_id']}:{condition}:{variant}",
                    "evaluator": self.MODEL,
                    "condition": condition,
                    "tool_mode": "repository" if condition == "tool-enabled" else "none",
                    "run_date": "2026-08-19",
                    "prompt_test_identity": f"MIXED-REGISTER/1-COLD-CONSUMER/1.0.0:{variant}",
                    "classification_contract_version": "MIXED-REGISTER/1",
                    "evaluation_bundle_sha256": self.BUNDLE_SHA,
                    "substrate": self.SUBSTRATE,
                    "artifact_hashes": {
                        "evaluation_bundle": self.BUNDLE_SHA,
                        "empirical_prompt": prompt_sha,
                        "empirical_carrier": carrier_sha,
                        "raw_consumer_response": raw_sha,
                    },
                    "claims": self.claim_rows(claims, ablated=variant == "ablated"),
                    "summary": {},
                }
                (empirical_dir / audit_rel).parent.mkdir(parents=True, exist_ok=True)
                (empirical_dir / audit_rel).write_text(
                    json.dumps(audit, separators=(",", ":")), encoding="utf-8"
                )

                report = {
                    "type": "qsol-mixed-register-report",
                    "schema_version": "1.0.0",
                    "artifact_class": "derived_evaluation",
                    "execution_kind": "empirical_consumer",
                    "run_id": audit["run_id"],
                    "evaluator": self.MODEL,
                    "condition": condition,
                    "evaluation_bundle_sha256": self.BUNDLE_SHA,
                    "substrate": self.SUBSTRATE,
                    "metrics": metrics[variant],
                    "claim_scores": [],
                }
                (empirical_dir / report_rel).parent.mkdir(parents=True, exist_ok=True)
                (empirical_dir / report_rel).write_text(
                    json.dumps(report, separators=(",", ":")), encoding="utf-8"
                )
                condition_bindings[variant] = {
                    "prompt": self.binding(empirical_dir, prompt_rel),
                    "carrier": self.binding(empirical_dir, carrier_rel),
                    "raw_response": self.binding(empirical_dir, raw_rel),
                    "audit": self.binding(empirical_dir, audit_rel),
                    "report": self.binding(empirical_dir, report_rel),
                }
            summary["artifact_bindings"][condition] = condition_bindings

        (empirical_dir / "summary.json").write_text(
            json.dumps(summary, separators=(",", ":")), encoding="utf-8"
        )

    def refresh_binding(self, empirical_dir: Path, condition: str, variant: str, kind: str):
        summary_path = empirical_dir / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        relative = summary["artifact_bindings"][condition][variant][kind]["path"]
        summary["artifact_bindings"][condition][variant][kind] = self.binding(
            empirical_dir, relative
        )
        summary_path.write_text(json.dumps(summary, separators=(",", ":")), encoding="utf-8")

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
        self.assertTrue(closure["provenance_binding_validated"])
        self.assertEqual(closure["validated_audit_count"], 10)
        self.assertEqual(closure["validated_artifact_count"], 50)
        self.assertEqual(closure["strict_passing_guarded_conditions"], list(CONDITIONS))
        for row in closure["rows"]:
            self.assertEqual(row["guard_effect_classification"], "improved")
            self.assertTrue(row["strict_cold_consumer_gate"]["passed"])
            self.assertGreater(row["guard_effect"]["adjacency_false_support_rate_reduction"], 0)

    def test_closure_rejects_mixed_run_audit_even_when_binding_hash_is_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            empirical_dir = Path(tmp) / "empirical"
            empirical_dir.mkdir()
            self.write_fixture(empirical_dir)
            source = empirical_dir / "audits/micro.guarded.json"
            target = empirical_dir / "audits/standard.guarded.json"
            target.write_bytes(source.read_bytes())
            self.refresh_binding(empirical_dir, "standard", "guarded", "audit")
            with self.assertRaisesRegex(EmpiricalClosureError, "audit provenance binding mismatch"):
                build_closure(ROOT, empirical_dir)

    def test_closure_rejects_edited_prompt_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            empirical_dir = Path(tmp) / "empirical"
            empirical_dir.mkdir()
            self.write_fixture(empirical_dir)
            (empirical_dir / "prompts/micro.guarded.txt").write_text(
                "edited after summary\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(EmpiricalClosureError, "artifact hash/size mismatch"):
                build_closure(ROOT, empirical_dir)

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
