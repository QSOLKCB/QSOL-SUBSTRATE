import copy
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import epistemic_conformance_core as ecc  # noqa: E402
from epistemic_conformance_core import (  # noqa: E402
    EpistemicConformanceError,
    build_benchmark_bundle,
    checked_out_source_commit,
    compare_reports,
    comparison_markdown,
    load_source_manifest,
    report_markdown,
    score_run,
    validate_benchmark_bundle,
)


FULL_SIGNALS = {
    "ECB-A": {
        "conflict_opportunities": 2,
        "historical_opportunities": 3,
        "identifier_opportunities": 1,
        "cross_domain_opportunities": 2,
        "retrieved_text_opportunities": 2,
    },
    "ECB-B": {
        "conflict_opportunities": 1,
        "historical_opportunities": 2,
        "identifier_opportunities": 1,
        "cross_domain_opportunities": 1,
        "retrieved_text_opportunities": 1,
    },
    "ECB-C": {
        "conflict_opportunities": 1,
        "historical_opportunities": 2,
        "identifier_opportunities": 0,
        "cross_domain_opportunities": 1,
        "retrieved_text_opportunities": 1,
    },
    "ECB-D": {
        "conflict_opportunities": 1,
        "historical_opportunities": 1,
        "identifier_opportunities": 1,
        "cross_domain_opportunities": 2,
        "retrieved_text_opportunities": 1,
    },
}


def _perfect_signals(module_id):
    opportunities = dict(FULL_SIGNALS[module_id])
    return {
        **opportunities,
        "conflict_preserved": opportunities["conflict_opportunities"],
        "historical_preserved": opportunities["historical_opportunities"],
        "identifier_errors": 0,
        "cross_domain_errors": 0,
        "retrieved_text_errors": 0,
    }


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
            "signals": _perfect_signals(module_id),
        }

    def _run(self, model="example/model", revision="r1", execution_kind="model", provider="local"):
        modules = [
            self._module(row["id"], row["case_count"], row["max_points"])
            for row in self.manifest["modules"]
        ]
        return {
            "type": "qsol-epistemic-conformance-run",
            "schema_version": "1.0.0",
            "run_id": f"{provider}:{model}:{revision}",
            "execution_kind": execution_kind,
            "benchmark": {
                "id": "EPISTEMIC-CONFORMANCE/1",
                "sha256": self.manifest["benchmark_sha256"],
            },
            "substrate": {
                "protocol": "QSOL-SUBSTRATE",
                "source_commit": self.commit,
                "substrate_sha256": "a" * 64,
                "delivery": "full-text",
            },
            "model": {
                "id": model,
                "revision": revision,
                "provider": provider,
                "runtime": "LM Studio",
                "quantization": "Q4_K_M",
                "parameter_count_billion": 8,
            },
            "inference": {
                "context_size": 32768,
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
                "seed": 1234,
                "sampler": "llama.cpp-default",
                "extra": {"min_p": 0.0},
            },
            "grader": {
                "id": "external-grader",
                "revision": "1",
                "method": "deterministic_oracle"
                if execution_kind == "scoring_oracle"
                else "human_external",
            },
            "modules": modules,
        }

    @staticmethod
    def _zero_signals(module):
        module["signals"] = {
            "conflict_opportunities": 0,
            "conflict_preserved": 0,
            "historical_opportunities": 0,
            "historical_preserved": 0,
            "identifier_opportunities": 0,
            "identifier_errors": 0,
            "cross_domain_opportunities": 0,
            "cross_domain_errors": 0,
            "retrieved_text_opportunities": 0,
            "retrieved_text_errors": 0,
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

    def test_source_case_markers_match_external_grading(self):
        source = load_source_manifest(ROOT)
        self.assertEqual(sum(row["case_count"] for row in source["modules"]), 33)
        with mock.patch.object(ecc, "_prompt_case_ids", return_value=("A1",)):
            with self.assertRaises(EpistemicConformanceError):
                load_source_manifest(ROOT)

    def test_source_and_grading_schemas_are_enforced(self):
        original = ecc._load_json

        def source_extra(path):
            value = original(path)
            if path == ROOT / ecc.SOURCE_MANIFEST:
                value = copy.deepcopy(value)
                value["unexpected_contract_field"] = True
            return value

        with mock.patch.object(ecc, "_load_json", side_effect=source_extra):
            with self.assertRaises(EpistemicConformanceError):
                load_source_manifest(ROOT)

        def grading_extra(path):
            value = original(path)
            if path == ROOT / ecc.SOURCE_DIR / "external-grading-v1.json":
                value = copy.deepcopy(value)
                value["policy"]["unexpected_policy_field"] = True
            return value

        with mock.patch.object(ecc, "_load_json", side_effect=grading_extra):
            with self.assertRaises(EpistemicConformanceError):
                load_source_manifest(ROOT)

    def test_non_object_source_module_fails_closed(self):
        original = ecc._load_json

        def fake_load(path):
            value = original(path)
            if path == ROOT / ecc.SOURCE_MANIFEST:
                value = copy.deepcopy(value)
                value["modules"][0] = None
            return value

        with mock.patch.object(ecc, "_load_json", side_effect=fake_load):
            with self.assertRaises(EpistemicConformanceError):
                load_source_manifest(ROOT)

    def test_perfect_external_annotation_scores_conformant(self):
        report = score_run(ROOT, self.bundle, self._run())
        self.assertEqual(report["metrics"]["external_conformance_score"], 1.0)
        self.assertEqual(report["metrics"]["completion_rate"], 1.0)
        self.assertEqual(report["metrics"]["major_error_count"], 0)
        self.assertEqual(report["metrics"]["self_score_error"], 0.0)
        self.assertEqual(report["verdict"], "CONFORMANT")

    def test_inference_configuration_is_required_and_preserved(self):
        run = self._run()
        del run["inference"]
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

        first = self._run("model/shared", "r1")
        second = self._run("model/shared", "r1")
        second["run_id"] = "local:model/shared:r1:hot"
        second["inference"]["temperature"] = 0.8
        comparison = compare_reports(
            ROOT,
            [score_run(ROOT, self.bundle, first), score_run(ROOT, self.bundle, second)],
        )
        self.assertEqual(
            {row["inference"]["temperature"] for row in comparison["rows"]},
            {0.2, 0.8},
        )

    def test_model_self_score_is_calibration_not_grade(self):
        run = self._run()
        for module in run["modules"]:
            module["model_self_assessment"]["score_fraction"] = 1.0
        run["modules"][0]["earned_points"] = 10
        report = score_run(ROOT, self.bundle, run)
        self.assertLess(report["metrics"]["external_conformance_score"], 1.0)
        self.assertGreater(report["metrics"]["self_score_error"], 0.0)

    def test_self_score_uses_same_assessed_subset(self):
        run = self._run()
        for module in run["modules"][:3]:
            module["model_self_assessment"]["score_fraction"] = None
            module["model_self_assessment"]["verdict"] = None
            module["earned_points"] = 0
        d = run["modules"][3]
        d["model_self_assessment"]["score_fraction"] = 1.0
        report = score_run(ROOT, self.bundle, run)
        self.assertEqual(report["metrics"]["self_score_error"], 0.0)

    def test_major_error_prevents_conformant_verdict(self):
        run = self._run()
        run["modules"][1]["major_errors"] = [
            {"case": "B7", "code": "unsupported_identifier_completion"}
        ]
        report = score_run(ROOT, self.bundle, run)
        self.assertEqual(report["metrics"]["major_error_count"], 1)
        self.assertEqual(report["verdict"], "NON_CONFORMANT")

    def test_major_error_occurrences_preserve_repeated_codes(self):
        run = self._run()
        run["modules"][0]["major_errors"] = [
            {"case": "A5", "code": "cross_domain_evidence_overclaim"},
            {"case": "A9", "code": "cross_domain_evidence_overclaim"},
        ]
        report = score_run(ROOT, self.bundle, run)
        self.assertEqual(report["metrics"]["major_error_count"], 2)
        self.assertEqual(len(report["modules"][0]["major_errors"]), 2)

    def test_major_errors_cannot_reference_uncompleted_cases(self):
        run = self._run()
        a = run["modules"][0]
        a["completed_cases"] = 0
        a["earned_points"] = 0
        a["major_errors"] = [
            {"case": "A1", "code": "registry_omission_overclaim"}
        ]
        self._zero_signals(a)
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

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

    def test_incomplete_ecb_d_metrics_are_unknown(self):
        run = self._run()
        d = next(module for module in run["modules"] if module["module_id"] == "ECB-D")
        d["completed_cases"] = 0
        d["earned_points"] = 0
        d["initial_errors"] = 0
        d["corrected_errors"] = 0
        d["remaining_errors"] = 0
        self._zero_signals(d)
        report = score_run(ROOT, self.bundle, run)
        self.assertIsNone(report["metrics"]["first_pass_conformance"])
        self.assertIsNone(report["metrics"]["self_correction_rate"])

    def test_fully_corrected_first_pass_errors_can_still_be_conformant(self):
        run = self._run()
        d = next(module for module in run["modules"] if module["module_id"] == "ECB-D")
        d["initial_errors"] = 3
        d["corrected_errors"] = 3
        d["remaining_errors"] = 0
        report = score_run(ROOT, self.bundle, run)
        self.assertLess(report["metrics"]["first_pass_conformance"], 1.0)
        self.assertEqual(report["metrics"]["self_correction_rate"], 1.0)
        self.assertEqual(report["verdict"], "CONFORMANT")

    def test_ecb_d_error_accounting_must_partition_initial_errors(self):
        run = self._run()
        d = next(module for module in run["modules"] if module["module_id"] == "ECB-D")
        d["initial_errors"] = 1
        d["corrected_errors"] = 1
        d["remaining_errors"] = 1
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

        d["corrected_errors"] = 0
        d["remaining_errors"] = 0
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_points_cannot_be_awarded_to_uncompleted_cases(self):
        run = self._run()
        a = next(module for module in run["modules"] if module["module_id"] == "ECB-A")
        a["completed_cases"] = 0
        a["earned_points"] = a["max_points"]
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

        a["completed_cases"] = 1
        a["earned_points"] = 3
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_persisted_report_reapplies_completion_cap(self):
        report = score_run(ROOT, self.bundle, self._run())
        tampered = copy.deepcopy(report)
        a = next(module for module in tampered["modules"] if module["module_id"] == "ECB-A")
        a["completed_cases"] = 0
        a["earned_points"] = 20
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [tampered])

    def test_signal_opportunities_are_frozen_by_completed_case_prefix(self):
        run = self._run()
        run["modules"][0]["signals"]["conflict_opportunities"] = 100
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

        run = self._run()
        d = run["modules"][3]
        d["completed_cases"] = 2
        d["earned_points"] = 2
        d["initial_errors"] = 0
        d["corrected_errors"] = 0
        d["remaining_errors"] = 0
        self._zero_signals(d)
        d["signals"]["conflict_opportunities"] = 1
        d["signals"]["conflict_preserved"] = 1
        report = score_run(ROOT, self.bundle, run)
        self.assertLess(report["metrics"]["completion_rate"], 1.0)

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

    def test_delivery_identity_is_required(self):
        run = self._run()
        del run["substrate"]["delivery"]
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_comparison_requires_exact_substrate_identity(self):
        first = score_run(ROOT, self.bundle, self._run("model/a", "r1"))
        second_run = self._run("model/b", "r1")
        second_run["substrate"]["substrate_sha256"] = "b" * 64
        second = score_run(ROOT, self.bundle, second_run)
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [first, second])

    def test_comparison_preserves_provider_and_grader_identity(self):
        first = score_run(
            ROOT,
            self.bundle,
            self._run("model/shared", "r1", provider="provider-a"),
        )
        second_run = self._run("model/shared", "r1", provider="provider-b")
        second_run["grader"]["id"] = "grader-b"
        second_run["grader"]["revision"] = "2"
        second = score_run(ROOT, self.bundle, second_run)
        comparison = compare_reports(ROOT, [first, second])
        self.assertEqual(
            {row["provider"] for row in comparison["rows"]},
            {"provider-a", "provider-b"},
        )
        self.assertEqual(
            {row["grader_id"] for row in comparison["rows"]},
            {"external-grader", "grader-b"},
        )

    def test_comparison_preserves_all_declared_metrics(self):
        run = self._run("model/self-correcting", "r1")
        run["modules"][0]["signals"]["identifier_errors"] = 1
        run["modules"][1]["signals"]["cross_domain_errors"] = 1
        run["modules"][2]["signals"]["retrieved_text_errors"] = 1
        d = next(module for module in run["modules"] if module["module_id"] == "ECB-D")
        d["initial_errors"] = 2
        d["corrected_errors"] = 2
        d["remaining_errors"] = 0
        report = score_run(ROOT, self.bundle, run)
        comparison = compare_reports(ROOT, [report])
        row = comparison["rows"][0]
        self.assertEqual(row["parameter_count_billion"], 8)
        for metric in ecc.EXPECTED_METRICS:
            self.assertEqual(row[metric], report["metrics"][metric])
        markdown = comparison_markdown(comparison)
        self.assertIn("Epistemic boundary metrics", markdown)
        self.assertIn("Identifier error rate", markdown)
        self.assertIn("Cross-domain overreach", markdown)

    def test_comparison_order_is_independent_of_input_order(self):
        first_run = self._run("model/repeat", "r1")
        second_run = self._run("model/repeat", "r1")
        first_run["run_id"] = "run-z"
        second_run["run_id"] = "run-a"
        first = score_run(ROOT, self.bundle, first_run)
        second = score_run(ROOT, self.bundle, second_run)
        forward = compare_reports(ROOT, [first, second])
        reverse = compare_reports(ROOT, [second, first])
        self.assertEqual(forward, reverse)
        self.assertEqual([row["run_id"] for row in forward["rows"]], ["run-a", "run-z"])

    def test_comparison_markdown_preserves_exact_binding_identity(self):
        report = score_run(ROOT, self.bundle, self._run())
        comparison = compare_reports(ROOT, [report])
        markdown = comparison_markdown(comparison)
        self.assertIn(comparison["benchmark"]["sha256"], markdown)
        self.assertIn(comparison["substrate"]["source_commit"], markdown)
        self.assertIn(comparison["substrate"]["substrate_sha256"], markdown)
        self.assertIn('"delivery":"full-text"', markdown)

    def test_markdown_escapes_identity_table_metacharacters(self):
        run = self._run(model="name | injected\nrow", provider="prov|ider")
        report = score_run(ROOT, self.bundle, run)
        markdown = comparison_markdown(compare_reports(ROOT, [report]))
        self.assertIn("prov\\|ider", markdown)
        self.assertIn("name \\| injected<br>row", markdown)

    def test_malformed_persisted_report_fails_closed(self):
        report = score_run(ROOT, self.bundle, self._run())
        malformed = copy.deepcopy(report)
        malformed["model"] = {}
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [malformed])

    def test_tampered_persisted_metrics_and_verdict_fail_closed(self):
        report = score_run(ROOT, self.bundle, self._run())
        for field, value in (
            ("counts", {**report["counts"], "earned_points": 0}),
            ("metrics", {**report["metrics"], "external_conformance_score": 0.1}),
        ):
            tampered = copy.deepcopy(report)
            tampered[field] = value
            with self.assertRaises(EpistemicConformanceError):
                compare_reports(ROOT, [tampered])
        tampered = copy.deepcopy(report)
        tampered["verdict"] = "PARTIALLY_CONFORMANT"
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [tampered])

    def test_oracle_report_cannot_enter_empirical_comparison(self):
        oracle = score_run(
            ROOT,
            self.bundle,
            self._run("qsol/scoring-oracle", "1", "scoring_oracle"),
        )
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [oracle])
        markdown = report_markdown(oracle)
        self.assertIn("NON-EMPIRICAL SCORING ORACLE", markdown)
        self.assertIn("scoring-oracle self-test report", markdown)

    def test_model_report_with_oracle_grader_is_rejected(self):
        report = score_run(ROOT, self.bundle, self._run())
        tampered = copy.deepcopy(report)
        tampered["grader"]["method"] = "deterministic_oracle"
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [tampered])

    def test_completed_cases_cannot_exceed_module_case_count(self):
        run = self._run()
        run["modules"][0]["completed_cases"] += 1
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_non_finite_numbers_are_rejected(self):
        run = self._run()
        run["modules"][0]["earned_points"] = math.nan
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)
        run = self._run()
        run["model"]["parameter_count_billion"] = math.inf
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_unpaired_surrogates_are_rejected(self):
        run = self._run()
        run["modules"][0]["raw_output"] = chr(0xD800)
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_non_object_bundle_manifest_is_invalid_finding(self):
        (self.bundle / "manifest.json").write_text("[]\n", encoding="utf-8")
        self.assertIn("benchmark.invalid", validate_benchmark_bundle(ROOT, self.bundle))

    def test_in_repo_output_is_restricted_to_designated_dist_root(self):
        with self.assertRaises(EpistemicConformanceError):
            build_benchmark_bundle(ROOT, ROOT, self.commit)
        with self.assertRaises(EpistemicConformanceError):
            build_benchmark_bundle(ROOT, ROOT / "dist", self.commit)
        with self.assertRaises(EpistemicConformanceError):
            build_benchmark_bundle(ROOT, ROOT.parent, self.commit)

    def test_dirty_benchmark_sources_fail_closed(self):
        original = ecc._git_output

        def fake_git_output(root, args):
            if args and args[0] == "status":
                return " M probe/epistemic-conformance-1/A-blind-conformance.md\n"
            return original(root, args)

        with mock.patch.object(ecc, "_git_output", side_effect=fake_git_output):
            with self.assertRaises(EpistemicConformanceError):
                build_benchmark_bundle(ROOT, self.base / "dirty", self.commit)


if __name__ == "__main__":
    unittest.main()
