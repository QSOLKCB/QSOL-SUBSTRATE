import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from probe_core import (  # noqa: E402
    CONDITION_IDS,
    ProbeError,
    build_probe_bundle,
    build_scoring_oracle_run,
    checked_out_source_commit,
    compare_probe_reports,
    score_probe_run,
    validate_probe_bundle,
)


class Phase7ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bundle = self.base / "probes"
        self.commit = checked_out_source_commit(ROOT)

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, commit=None):
        return build_probe_bundle(ROOT, self.bundle, commit or self.commit)

    def _oracle(self, condition="naked"):
        self._build()
        return build_scoring_oracle_run(self.bundle, condition)

    def _projection_execution(self, kind, model="example/model", revision="r1", tokenizer="test-tokenizer"):
        return {
            "executed": True,
            "backend": "test-runner",
            "artifact_sha256": "a" * 64,
            "runtime_evidence_sha256": "b" * 64,
            "compatibility": {
                "type": "qsol-model-projection-compatibility",
                "schema_version": "1.0.0",
                "projection_kind": kind,
                "model_id": model,
                "model_revision": revision,
                "architecture": "test-architecture",
                "tokenizer_id": tokenizer,
                "tokenizer_sha256": "c" * 64,
                "context_length": 4096,
                "hidden_size": 1024,
                "num_hidden_layers": 12,
                "num_attention_heads": 8,
                "kv_layout_version": "test-kv-v1",
                "tensor_dtype": "float16",
                "kv_cache_dtype": "float16",
                "quantization_id": "none",
            },
        }

    def _empirical(self, condition="naked", model="example/model", revision="r1", provider="test", include_projection=True):
        run = self._oracle(condition)
        run["execution_kind"] = "model"
        run["run_id"] = f"{model}:{revision}:{condition}"
        run["model"] = {"id": model, "revision": revision, "provider": provider}
        run["usage"] = {"input_tokens": 1000, "output_tokens": 100, "tokenizer": "test-tokenizer"}
        if include_projection and condition == "latent-prefix":
            run["projection_execution"] = self._projection_execution("prefix_state", model, revision)
        if include_projection and condition == "hybrid":
            run["projection_execution"] = self._projection_execution("hybrid", model, revision)
        return run

    def test_probe_bundle_builds_and_validates(self):
        manifest = self._build()
        self.assertEqual(manifest["probe_count"], 48)
        self.assertEqual(manifest["suite_counts"], {"substrate": 24, "yeah-nah-1": 24})
        self.assertEqual(validate_probe_bundle(ROOT, self.bundle), [])

    def test_probe_build_is_deterministic(self):
        first = self._build()
        first_files = {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        shutil.rmtree(self.bundle)
        second = self._build()
        second_files = {p.name: p.read_bytes() for p in self.bundle.iterdir()}
        self.assertEqual(first["bundle_sha256"], second["bundle_sha256"])
        self.assertEqual(first_files, second_files)

    def test_declared_source_commit_must_equal_checked_out_head(self):
        with self.assertRaises(ProbeError):
            self._build("a" * 40)

    def test_uncommitted_probe_source_changes_fail_closed(self):
        with mock.patch("probe_core._git_output", side_effect=[self.commit + "\n", " M probe/conditions.json\n"]):
            with self.assertRaises(ProbeError):
                self._build()

    def test_all_comparison_conditions_are_present(self):
        manifest = self._build()
        self.assertEqual(tuple(manifest["conditions"]), CONDITION_IDS)

    def test_ci_manifest_explicitly_denies_empirical_claim(self):
        manifest = self._build()
        self.assertFalse(manifest["empirical_model_results_in_ci"])
        self.assertFalse(manifest["scoring_oracle_is_empirical_result"])

    def test_oracle_scores_perfectly(self):
        run = self._oracle()
        report = score_probe_run(ROOT, self.bundle, run)
        self.assertEqual(report["counts"]["correct"], 48)
        self.assertEqual(report["metrics"]["overall_accuracy"], 1.0)
        self.assertEqual(report["yeah_nah_1"]["overall_accuracy"], 1.0)
        self.assertEqual(report["yeah_nah_1"]["confidence_brier"], 0.0)

    def test_oracle_is_labelled_non_empirical(self):
        run = self._oracle()
        self.assertEqual(run["execution_kind"], "scoring_oracle")
        self.assertEqual(run["model"]["id"], "qsol/scoring-oracle")

    def test_unknown_precision_and_recall_are_operational(self):
        report = score_probe_run(ROOT, self.bundle, self._oracle())
        self.assertEqual(report["metrics"]["unknown_precision"], 1.0)
        self.assertEqual(report["metrics"]["unknown_recall"], 1.0)
        self.assertEqual(report["metrics"]["unsupported_assertion_rate"], 0.0)

    def test_unknown_state_cannot_carry_invented_answer(self):
        run = self._empirical()
        target = next(r for r in run["responses"] if r["probe_id"] == "substrate:unknown:qsol-imc-legal-status")
        target["answer"] = "invented legal status"
        with self.assertRaises(ProbeError):
            score_probe_run(ROOT, self.bundle, run)

    def test_unknown_with_extra_identifier_counts_as_hallucination(self):
        run = self._empirical()
        target = next(r for r in run["responses"] if r["probe_id"] == "substrate:unknown:qsol-imc-legal-status")
        target["canonical_ids"] = ["project:invented"]
        report = score_probe_run(ROOT, self.bundle, run)
        self.assertGreater(report["metrics"]["unsupported_assertion_rate"], 0)
        self.assertGreater(report["metrics"]["hallucination_rate"], 0)
        self.assertLess(report["metrics"]["unknown_recall"], 1.0)

    def test_extra_canonical_identifier_is_not_accepted(self):
        run = self._empirical()
        target = next(r for r in run["responses"] if r["canonical_ids"])
        target["canonical_ids"].append("project:invented-extra")
        report = score_probe_run(ROOT, self.bundle, run)
        result = next(item for item in report["case_results"] if item["probe_id"] == target["probe_id"])
        self.assertFalse(result["correct"])
        self.assertLess(report["metrics"]["overall_accuracy"], 1.0)

    def test_extra_provenance_reference_reduces_fidelity(self):
        run = self._empirical()
        target = next(r for r in run["responses"] if r["provenance_refs"])
        target["provenance_refs"].append("src:invented-extra")
        report = score_probe_run(ROOT, self.bundle, run)
        self.assertLess(report["metrics"]["provenance_fidelity"], 1.0)

    def test_provenance_alias_conflict_and_claim_boundaries_are_scored(self):
        report = score_probe_run(ROOT, self.bundle, self._oracle())
        self.assertEqual(report["metrics"]["alias_resolution_accuracy"], 1.0)
        self.assertEqual(report["metrics"]["provenance_fidelity"], 1.0)
        self.assertEqual(report["metrics"]["contradiction_handling"], 1.0)
        self.assertEqual(report["metrics"]["claim_boundary_preservation"], 1.0)

    def test_token_efficiency_uses_declared_run_usage(self):
        run = self._empirical()
        report = score_probe_run(ROOT, self.bundle, run)
        self.assertEqual(report["metrics"]["context_token_efficiency"], 48.0)

    def test_wrong_probe_bundle_identity_is_rejected(self):
        run = self._oracle()
        run["probe_bundle_sha256"] = "0" * 64
        with self.assertRaises(ProbeError):
            score_probe_run(ROOT, self.bundle, run)

    def test_missing_response_is_rejected(self):
        run = self._oracle()
        run["responses"].pop()
        with self.assertRaises(ProbeError):
            score_probe_run(ROOT, self.bundle, run)

    def test_duplicate_response_is_rejected(self):
        run = self._oracle()
        run["responses"][-1] = dict(run["responses"][0])
        with self.assertRaises(ProbeError):
            score_probe_run(ROOT, self.bundle, run)

    def test_tampered_probe_file_fails_deterministic_validation(self):
        self._build()
        path = self.bundle / "substrate-probe.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace("Trent Slade", "Invented Person", 1), encoding="utf-8")
        codes = [finding.code for finding in validate_probe_bundle(ROOT, self.bundle)]
        self.assertIn("probe.deterministic_mismatch", codes)

    def test_extra_probe_file_is_rejected(self):
        self._build()
        (self.bundle / "extra.txt").write_text("nope", encoding="utf-8")
        codes = [finding.code for finding in validate_probe_bundle(ROOT, self.bundle)]
        self.assertIn("probe.file_set", codes)

    def test_symlinked_probe_entry_is_rejected(self):
        self._build()
        target = self.base / "outside.json"
        target.write_text("{}", encoding="utf-8")
        path = self.bundle / "conditions.json"
        path.unlink()
        path.symlink_to(target)
        codes = [finding.code for finding in validate_probe_bundle(ROOT, self.bundle)]
        self.assertIn("probe.symlink", codes)

    def test_probe_output_cannot_replace_repository_source(self):
        with self.assertRaises(ProbeError):
            build_probe_bundle(ROOT, ROOT / "tools", self.commit)

    def test_latent_model_run_requires_runtime_projection_evidence(self):
        run = self._empirical("latent-prefix", include_projection=False)
        with self.assertRaises(ProbeError):
            score_probe_run(ROOT, self.bundle, run)

    def test_latent_projection_identity_must_match_model_revision(self):
        run = self._empirical("latent-prefix")
        run["projection_execution"]["compatibility"]["model_revision"] = "wrong-revision"
        with self.assertRaises(ProbeError):
            score_probe_run(ROOT, self.bundle, run)

    def test_valid_latent_projection_evidence_survives_report(self):
        run = self._empirical("latent-prefix")
        report = score_probe_run(ROOT, self.bundle, run)
        self.assertEqual(report["projection_execution"], run["projection_execution"])

    def test_empirical_comparison_requires_common_probe_identity(self):
        naked = score_probe_run(ROOT, self.bundle, self._empirical("naked"))
        micro_run = self._empirical("micro")
        micro = score_probe_run(ROOT, self.bundle, micro_run)
        micro["probe_bundle_sha256"] = "0" * 64
        with self.assertRaises(ProbeError):
            compare_probe_reports(ROOT, [naked, micro])

    def test_empirical_comparison_computes_uplift_from_naked(self):
        naked_run = self._empirical("naked")
        target = next(r for r in naked_run["responses"] if r["probe_id"] == "substrate:unknown:qsol-imc-legal-status")
        target["epistemic_state"] = "known"
        target["answer"] = "invented"
        naked = score_probe_run(ROOT, self.bundle, naked_run)
        micro = score_probe_run(ROOT, self.bundle, self._empirical("micro"))
        comparison = compare_probe_reports(ROOT, [naked, micro])
        micro_row = next(row for row in comparison["rows"] if row["condition"] == "micro")
        self.assertGreater(micro_row["substrate_uplift_over_naked"], 0)
        self.assertGreater(micro_row["hallucination_reduction_relative_to_naked"], 0)

    def test_mixed_model_revisions_do_not_share_naked_baseline(self):
        naked = score_probe_run(ROOT, self.bundle, self._empirical("naked", revision="r1"))
        micro = score_probe_run(ROOT, self.bundle, self._empirical("micro", revision="r2"))
        comparison = compare_probe_reports(ROOT, [naked, micro])
        micro_row = next(row for row in comparison["rows"] if row["condition"] == "micro")
        self.assertEqual(micro_row["model_revision"], "r2")
        self.assertIsNone(micro_row["substrate_uplift_over_naked"])
        self.assertEqual(len(comparison["models"]), 2)

    def test_oracle_reports_cannot_be_used_as_empirical_comparisons(self):
        report = score_probe_run(ROOT, self.bundle, self._oracle())
        with self.assertRaises(ProbeError):
            compare_probe_reports(ROOT, [report])

    def test_score_cli_creates_documented_parent_directories(self):
        run = self._empirical("micro")
        run_path = self.base / "run.json"
        run_path.write_text(json.dumps(run), encoding="utf-8")
        output = self.base / "reports" / "nested" / "model-micro.json"
        markdown = self.base / "reports" / "markdown" / "model-micro.md"
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "score_probe_run.py"), "--bundle", str(self.bundle), "--run", str(run_path), "--output", str(output), "--markdown", str(markdown)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(output.is_file())
        self.assertTrue(markdown.is_file())

    def test_compare_cli_creates_documented_parent_directories(self):
        naked = score_probe_run(ROOT, self.bundle, self._empirical("naked"))
        micro = score_probe_run(ROOT, self.bundle, self._empirical("micro"))
        naked_path = self.base / "naked.json"
        micro_path = self.base / "micro.json"
        naked_path.write_text(json.dumps(naked), encoding="utf-8")
        micro_path.write_text(json.dumps(micro), encoding="utf-8")
        output = self.base / "comparison" / "nested" / "comparison.json"
        markdown = self.base / "comparison" / "markdown" / "comparison.md"
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "compare_probe_reports.py"), str(naked_path), str(micro_path), "--output", str(output), "--markdown", str(markdown)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(output.is_file())
        self.assertTrue(markdown.is_file())


if __name__ == "__main__":
    unittest.main()
