import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from epistemic_conformance_core import (  # noqa: E402
    EpistemicConformanceError,
    build_benchmark_bundle,
    checked_out_source_commit,
    compare_reports,
    score_run,
    validate_benchmark_bundle,
)


class EpistemicConformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bundle = self.base / "benchmark"
        self.commit = checked_out_source_commit(ROOT)
        self.manifest = build_benchmark_bundle(ROOT, self.bundle, self.commit)

    def tearDown(self):
        self.tmp.cleanup()

    def _module(self, module_id, case_count, max_points):
        return {
            "module_id": module_id,
            "raw_output": f"raw output for {module_id}",
            "completed_cases": case_count,
            "earned_points": max_points,
            "max_points": max_points,
            "major_errors": [],
            "remaining_errors": 0,
            "initial_errors": 0,
            "corrected_errors": 0,
            "model_self_assessment": {"score_fraction": 1.0, "verdict": "CONFORMANT"},
            "signals": {
                "conflict_opportunities": 1,
                "conflict_preserved": 1,
                "historical_opportunities": 1,
                "historical_preserved": 1,
                "identifier_opportunities": 1,
                "identifier_errors": 0,
                "cross_domain_opportunities": 1,
                "cross_domain_errors": 0,
                "retrieved_text_opportunities": 1,
                "retrieved_text_errors": 0,
            },
        }

    def _run(self, model="example/model", revision="r1", execution_kind="model"):
        modules = [self._module(row["id"], row["case_count"], row["max_points"]) for row in self.manifest["modules"]]
        return {
            "type": "qsol-epistemic-conformance-run",
            "schema_version": "1.0.0",
            "run_id": f"{model}:{revision}",
            "execution_kind": execution_kind,
            "benchmark": {"id": "EPISTEMIC-CONFORMANCE/1", "sha256": self.manifest["benchmark_sha256"]},
            "substrate": {
                "protocol": "QSOL-SUBSTRATE",
                "source_commit": self.commit,
                "substrate_sha256": "a" * 64,
                "delivery": "full-text",
            },
            "model": {
                "id": model,
                "revision": revision,
                "provider": "local",
                "runtime": "LM Studio",
                "quantization": "Q4_K_M",
                "parameter_count_billion": 8,
            },
            "grader": {
                "id": "external-grader",
                "revision": "1",
                "method": "deterministic_oracle" if execution_kind == "scoring_oracle" else "human_external",
            },
            "modules": modules,
        }

    def test_bundle_builds_and_validates_deterministically(self):
        self.assertEqual(self.manifest["benchmark_id"], "EPISTEMIC-CONFORMANCE/1")
        self.assertEqual(self.manifest["module_count"], 4)
        self.assertEqual(self.manifest["case_count"], 33)
        self.assertEqual(self.manifest["max_points"], 43)
        self.assertEqual(validate_benchmark_bundle(ROOT, self.bundle), [])
        first = {path.name: path.read_bytes() for path in self.bundle.iterdir()}
        second_dir = self.base / "second"
        second = build_benchmark_bundle(ROOT, second_dir, self.commit)
        self.assertEqual(self.manifest["benchmark_sha256"], second["benchmark_sha256"])
        self.assertEqual(first, {path.name: path.read_bytes() for path in second_dir.iterdir()})

    def test_perfect_external_annotation_scores_conformant(self):
        report = score_run(ROOT, self.bundle, self._run())
        self.assertEqual(report["metrics"]["external_conformance_score"], 1.0)
        self.assertEqual(report["metrics"]["completion_rate"], 1.0)
        self.assertEqual(report["metrics"]["major_error_count"], 0)
        self.assertEqual(report["metrics"]["self_score_error"], 0.0)
        self.assertEqual(report["verdict"], "CONFORMANT")

    def test_model_self_score_is_calibration_not_grade(self):
        run = self._run()
        for module in run["modules"]:
            module["model_self_assessment"]["score_fraction"] = 1.0
        run["modules"][0]["earned_points"] = 10
        report = score_run(ROOT, self.bundle, run)
        self.assertLess(report["metrics"]["external_conformance_score"], 1.0)
        self.assertGreater(report["metrics"]["self_score_error"], 0.0)

    def test_major_error_prevents_conformant_verdict(self):
        run = self._run()
        run["modules"][1]["major_errors"] = ["unsupported_identifier_completion"]
        report = score_run(ROOT, self.bundle, run)
        self.assertEqual(report["metrics"]["major_error_count"], 1)
        self.assertEqual(report["verdict"], "NON_CONFORMANT")

    def test_self_correction_metrics_are_separate_from_first_pass(self):
        run = self._run()
        d = next(module for module in run["modules"] if module["module_id"] == "ECB-D")
        d["initial_errors"] = 4
        d["corrected_errors"] = 3
        d["remaining_errors"] = 1
        report = score_run(ROOT, self.bundle, run)
        self.assertEqual(report["metrics"]["first_pass_conformance"], 0.5)
        self.assertEqual(report["metrics"]["self_correction_rate"], 0.75)
        self.assertGreater(report["metrics"]["remaining_error_rate"], 0)

    def test_signal_metrics_are_operational(self):
        run = self._run()
        run["modules"][0]["signals"]["identifier_errors"] = 1
        run["modules"][1]["signals"]["cross_domain_errors"] = 1
        run["modules"][2]["signals"]["retrieved_text_errors"] = 1
        report = score_run(ROOT, self.bundle, run)
        self.assertGreater(report["metrics"]["identifier_completion_error_rate"], 0)
        self.assertGreater(report["metrics"]["cross_domain_overreach_rate"], 0)
        self.assertLess(report["metrics"]["retrieved_text_authority_resistance"], 1.0)

    def test_wrong_benchmark_identity_is_rejected(self):
        run = self._run()
        run["benchmark"]["sha256"] = "0" * 64
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_comparison_requires_exact_substrate_identity(self):
        first = score_run(ROOT, self.bundle, self._run("model/a", "r1"))
        second_run = self._run("model/b", "r1")
        second_run["substrate"]["substrate_sha256"] = "b" * 64
        second = score_run(ROOT, self.bundle, second_run)
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [first, second])

    def test_oracle_report_cannot_enter_empirical_comparison(self):
        oracle = score_run(ROOT, self.bundle, self._run("qsol/scoring-oracle", "1", "scoring_oracle"))
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [oracle])

    def test_completed_cases_cannot_exceed_module_case_count(self):
        run = self._run()
        run["modules"][0]["completed_cases"] += 1
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)


if __name__ == "__main__":
    unittest.main()
