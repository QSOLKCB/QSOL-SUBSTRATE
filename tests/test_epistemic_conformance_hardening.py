import copy
import json
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
    report_markdown,
    score_run,
)
from validate_epistemic_conformance_cohort import validate_cohort  # noqa: E402

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


class EpistemicConformanceHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bundle = self.base / "benchmark"
        self.commit = checked_out_source_commit(ROOT)
        self.manifest = build_benchmark_bundle(ROOT, self.bundle, self.commit)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, revision="r1"):
        modules = []
        for row in self.manifest["modules"]:
            modules.append(
                {
                    "module_id": row["id"],
                    "raw_output": f"raw output for {row['id']}",
                    "completed_cases": row["case_count"],
                    "earned_points": row["max_points"],
                    "max_points": row["max_points"],
                    "major_errors": [],
                    "remaining_errors": 0,
                    "initial_errors": 0,
                    "corrected_errors": 0,
                    "model_self_assessment": {
                        "score_fraction": 1.0,
                        "verdict": "CONFORMANT",
                    },
                    "signals": _perfect_signals(row["id"]),
                }
            )
        return {
            "type": "qsol-epistemic-conformance-run",
            "schema_version": "1.0.0",
            "run_id": f"hardening:{revision}",
            "execution_kind": "model",
            "benchmark": {
                "id": "EPISTEMIC-CONFORMANCE/1",
                "sha256": self.manifest["benchmark_sha256"],
            },
            "substrate": {
                "protocol": "QSOL-SUBSTRATE",
                "source_commit": self.commit,
                "substrate_sha256": "a" * 64,
                "delivery": "full-text",
                "delivery_kind": "textual",
            },
            "projection_execution": None,
            "model": {
                "id": "example/model",
                "revision": revision,
                "provider": "local",
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
                "extra": {},
            },
            "grader": {
                "id": "external-grader",
                "revision": "1",
                "method": "human_external",
            },
            "modules": modules,
        }

    def test_unknown_revision_is_explicit_and_comparable_as_partial_identity(self):
        unknown = self._run(None)
        unknown["run_id"] = "unknown-revision"
        known = self._run("r1")
        known["run_id"] = "known-revision"
        unknown_report = score_run(ROOT, self.bundle, unknown)
        known_report = score_run(ROOT, self.bundle, known)
        self.assertIsNone(unknown_report["model"]["revision"])
        comparison = compare_reports(ROOT, [known_report, unknown_report])
        revisions = {row["model_revision"] for row in comparison["rows"]}
        self.assertEqual(revisions, {None, "r1"})

    def test_projection_execution_requires_exact_revision(self):
        run = self._run(None)
        run["substrate"]["delivery"] = "lora"
        run["substrate"]["delivery_kind"] = "lora"
        run["projection_execution"] = {
            "artifact_sha256": "b" * 64,
            "execution_evidence_sha256": "c" * 64,
            "compatibility": {
                "type": "qsol-model-projection-compatibility",
                "schema_version": "1.0.0",
                "projection_kind": "lora",
                "model_id": "example/model",
                "model_revision": "r1",
                "architecture": "example",
                "tokenizer_id": "example-tokenizer",
                "tokenizer_sha256": "d" * 64,
                "context_length": 32768,
                "hidden_size": 4096,
                "num_hidden_layers": 32,
                "num_attention_heads": 32,
                "kv_layout_version": "v1",
                "tensor_dtype": "f16",
                "kv_cache_dtype": "f16",
                "quantization_id": "Q4_K_M",
            },
        }
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

    def test_integral_float_is_not_an_operational_integer(self):
        run = self._run()
        run["modules"][0]["completed_cases"] = 1.0
        with self.assertRaises(EpistemicConformanceError):
            score_run(ROOT, self.bundle, run)

        report = score_run(ROOT, self.bundle, self._run())
        tampered = copy.deepcopy(report)
        tampered["modules"][0]["completed_cases"] = 10.0
        with self.assertRaises(EpistemicConformanceError):
            compare_reports(ROOT, [tampered])

    def test_report_markdown_carries_complete_bound_identity(self):
        report = score_run(ROOT, self.bundle, self._run())
        markdown = report_markdown(report)
        self.assertIn("## Bound identity", markdown)
        self.assertIn(report["benchmark"]["sha256"], markdown)
        self.assertIn(report["substrate"]["source_commit"], markdown)
        self.assertIn(report["substrate"]["substrate_sha256"], markdown)
        self.assertIn('"delivery":"full-text"', markdown)

    def test_exploratory_cohort_is_schema_governed_and_unbound(self):
        self.assertEqual(validate_cohort(ROOT), [])
        cohort = json.loads(
            (ROOT / "empirical/epistemic-conformance-1/2026-08-25/cohort.json").read_text(
                encoding="utf-8"
            )
        )
        cohort["models"][0]["immutable_revision"] = "invented-revision"
        path = self.base / "tampered-cohort.json"
        path.write_text(json.dumps(cohort), encoding="utf-8")
        self.assertTrue(validate_cohort(ROOT, path))

    def test_manifest_uses_standard_tool_registration(self):
        manifest = json.loads((ROOT / "ai/manifest.json").read_text(encoding="utf-8"))
        entry = manifest["epistemic_conformance_build"]
        self.assertEqual(entry["tool"], "tools/build_epistemic_conformance.py")
        self.assertNotIn("build_tool", entry)
        self.assertEqual(
            entry["cohort_schema"],
            "schema/epistemic-conformance-cohort.schema.json",
        )


if __name__ == "__main__":
    unittest.main()
