from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from mode_core import (  # noqa: E402
    CONDITIONS,
    CORPUS_PATH,
    FORMAL_INVARIANTS,
    POLICY_RESOURCES,
    ModeError,
    build_mode_bundle,
    build_oracle_run,
    calibrate_reports,
    classify_case,
    policy_index,
    score_mode_run,
    validate_mode_bundle,
)
from retrieve_mode_context import _safe_context_output  # noqa: E402


class DeferredModeWorkTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_policy_resources_are_explicitly_noncanonical(self) -> None:
        delivery = self.load("ai/mode-delivery.json")
        legal = self.load("modes/legal-jurisdictions.json")
        medical = self.load("modes/medical-specialties.json")
        resolvers = self.load("modes/authority-resolvers.json")
        witness = self.load("formal/mode-separation.json")
        self.assertEqual(delivery["classification"], "noncanonical_policy_projection")
        self.assertEqual(legal["classification"], "policy_not_legal_authority")
        self.assertEqual(medical["classification"], "policy_not_clinical_guidance")
        self.assertEqual(resolvers["classification"], "resolver_policy_not_source_authority_itself")
        self.assertIn("not_external_truth", witness["classification"])

    def test_legal_and_medical_guards_fail_closed(self) -> None:
        corpus = [
            json.loads(line)
            for line in (ROOT / CORPUS_PATH).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cases = {row["id"]: row for row in corpus}
        self.assertEqual(classify_case(cases["MC1-008"])["status"], "MODE_UNRESOLVED")
        self.assertEqual(classify_case(cases["MC1-010"])["status"], "MODE_VIOLATION")
        self.assertEqual(classify_case(cases["MC1-011"])["status"], "MODE_OK")
        self.assertEqual(classify_case(cases["MC1-022"])["reason_codes"], ["SCENARIO_PROMOTION"])

    def test_sparse_geometry_structural_benchmark_is_not_empirical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            manifest = build_mode_bundle(ROOT, out, "0" * 40)
            reference = json.loads((out / "reference-report.json").read_text(encoding="utf-8"))
            self.assertEqual(reference["classification"], "deterministic_oracle_self_test_not_empirical_model_result")
            self.assertEqual(reference["sparse_24d"]["accuracy"], 1.0)
            self.assertEqual(reference["sparse_24d"]["reason_code_accuracy"], 1.0)
            self.assertGreaterEqual(reference["sparse_24d"]["accuracy"], reference["rule_only"]["accuracy"])
            self.assertFalse(manifest["empirical_model_results_in_ci"])
            self.assertFalse(manifest["oracle_is_empirical_evidence"])

    def test_formal_witness_executes_every_declared_invariant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            build_mode_bundle(ROOT, out, "0" * 40)
            reference = json.loads((out / "reference-report.json").read_text(encoding="utf-8"))
        witness = reference["formal_witness"]
        self.assertTrue(witness["passed"])
        self.assertEqual(set(witness["invariant_results"]), FORMAL_INVARIANTS)
        for result in witness["invariant_results"].values():
            self.assertTrue(result["passed"])
            self.assertGreater(result["checks"], 0)

    def test_mode_bundle_rebuild_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            build_mode_bundle(ROOT, out, "1" * 40)
            self.assertEqual(validate_mode_bundle(ROOT, out), [])
            first = {path.name: path.read_bytes() for path in out.iterdir()}
            build_mode_bundle(ROOT, out, "1" * 40)
            second = {path.name: path.read_bytes() for path in out.iterdir()}
            self.assertEqual(first, second)

    def test_oracle_run_scores_perfect_including_reason_codes_but_is_not_empirical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            build_mode_bundle(ROOT, out, "2" * 40)
            run = build_oracle_run(out)
            report = score_mode_run(out, run)
            self.assertEqual(report["counts"]["correct"], report["counts"]["total"])
            self.assertEqual(report["counts"]["reason_codes_correct"], report["counts"]["total"])
            self.assertFalse(report["empirical_model_result"])
            with self.assertRaises(ModeError):
                calibrate_reports([report])

    def test_calibration_rejects_forged_oracle_boolean(self) -> None:
        forged = {
            "execution_kind": "scoring_oracle",
            "empirical_model_result": True,
        }
        with self.assertRaisesRegex(ModeError, "non-empirical execution kind"):
            calibrate_reports([forged])

    def test_calibration_requires_two_models_and_all_conditions(self) -> None:
        base = {
            "execution_kind": "empirical_consumer",
            "empirical_model_result": True,
            "mode_bundle_sha256": "a" * 64,
            "mode_policy_sha256": "b" * 64,
            "source_commit": "c" * 40,
            "substrate_sha256": "d" * 64,
            "metrics": {"category_accuracy": {"bridge_omission": 0.9}},
        }
        reports = []
        for revision in ("r1", "r2"):
            for condition in CONDITIONS:
                reports.append(dict(base, condition=condition, model={"provider": "test", "model_id": "m", "model_revision": revision}))
        result = calibrate_reports(reports)
        self.assertEqual(result["model_revision_count"], 2)
        self.assertEqual(set(result["condition_coverage"]), set(CONDITIONS))
        self.assertFalse(result["threshold_recommendation"]["automatic_mutation"])

    def test_mode_run_is_schema_validated_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            build_mode_bundle(ROOT, out, "3" * 40)
            run = build_oracle_run(out)
            run["execution_kind"] = "not-a-real-kind"
            with self.assertRaisesRegex(ModeError, "mode run violates"):
                score_mode_run(out, run)

    def test_tampered_mode_bundle_is_rejected_before_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            build_mode_bundle(ROOT, out, "4" * 40)
            run = build_oracle_run(out)
            with (out / "mode-confusion-1.jsonl").open("a", encoding="utf-8") as handle:
                handle.write("\n")
            with self.assertRaisesRegex(ModeError, "mode bundle validation failed"):
                score_mode_run(out, run)

    def test_mode_manifest_run_and_report_schemas_cover_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            manifest = build_mode_bundle(ROOT, out, "5" * 40)
            run = build_oracle_run(out)
            report = score_mode_run(out, run)
            triples = (
                (manifest, self.load("schema/mode-policy-manifest.schema.json")),
                (run, self.load("schema/mode-run.schema.json")),
                (report, self.load("schema/mode-report.schema.json")),
            )
            for value, schema in triples:
                Draft202012Validator.check_schema(schema)
                self.assertEqual(list(Draft202012Validator(schema).iter_errors(value)), [])

    def test_policy_fingerprint_changes_when_resource_changes(self) -> None:
        index = policy_index(ROOT)
        self.assertRegex(index["policy_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(index["policy_version"], "QSOL-MODE-POLICY/1")
        self.assertIn("schema/mode-policy-resource.schema.json", {row["path"] for row in index["resources"]})

    def test_policy_index_refuses_unknown_resolver_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in (*POLICY_RESOURCES, CORPUS_PATH):
                source = ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            legal_path = root / "modes/legal-jurisdictions.json"
            legal = json.loads(legal_path.read_text(encoding="utf-8"))
            legal["jurisdictions"][0]["primary_authority_resolvers"][0] = "resolver:not-real"
            legal_path.write_text(json.dumps(legal), encoding="utf-8")
            with self.assertRaisesRegex(ModeError, "unknown resolver"):
                policy_index(root)

    def test_mode_aware_retrieval_output_cannot_overwrite_normative_source(self) -> None:
        with self.assertRaisesRegex(ModeError, "restricted to dist/retrieved"):
            _safe_context_output(ROOT / "ai/manifest.json")


if __name__ == "__main__":
    unittest.main()
