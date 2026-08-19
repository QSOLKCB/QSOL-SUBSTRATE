import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import mixed_register_empirical as empirical
import run_mixed_register_empirical as runner


class FakeOllama(empirical.OllamaClient):
    def __init__(self, model, models=None, response_text=None):
        super().__init__("http://invalid", model)
        self._models = models or []
        self._response_text = response_text

    def _json(self, method, path, body=None):
        if path == "/api/tags":
            return {"models": self._models}
        if path == "/api/generate":
            return {
                "response": self._response_text,
                "prompt_eval_count": 10,
                "eval_count": 20,
                "total_duration": 30,
                "load_duration": 40,
            }
        raise AssertionError(path)


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

    def test_ablated_prompt_is_blinded_and_does_not_restate_treatment(self):
        claims = [{"id": "mr1-001", "text": "demo claim"}]
        guarded = empirical.build_prompt("report", claims, "context", "micro", "guarded")
        ablated = empirical.build_prompt("report", claims, "context", "micro", "ablated")
        self.assertIn("true neighbouring sentence", guarded)
        self.assertIn("humorous framing is not biography", guarded)
        self.assertNotIn("true neighbouring sentence", ablated)
        self.assertNotIn("neighbouring truth", ablated)
        self.assertNotIn("humorous framing is not biography", ablated)
        for prompt in (guarded, ablated):
            self.assertNotIn("LOCAL_BOUNDARY_VARIANT", prompt)
            self.assertNotIn("VARIANT=guarded", prompt)
            self.assertNotIn("VARIANT=ablated", prompt)

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

    def _perfect_gate_fixture(self):
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
        return built, audit, report

    def test_cold_consumer_gate_requires_unknown_restraint_and_all_classes(self):
        built, audit, report = self._perfect_gate_fixture()
        gate = empirical.cold_consumer_gate(built, audit, report)
        self.assertTrue(gate["passed"])
        failed = copy.deepcopy(report)
        failed["metrics"]["unsupported_assertion_rate"] = 0.25
        self.assertFalse(empirical.cold_consumer_gate(built, audit, failed)["passed"])

    def test_cold_consumer_gate_rejects_evidence_reference_violations(self):
        built, audit, report = self._perfect_gate_fixture()
        violations = [{"claim_id": "mr1-001", "evidence_ref": "file:invented.json"}]
        gate = empirical.cold_consumer_gate(
            built, audit, report, evidence_ref_violations=violations
        )
        self.assertFalse(gate["passed"])
        self.assertFalse(gate["checks"]["evidence_reference_integrity"])
        self.assertEqual(gate["evidence_ref_violation_count"], 1)

    def test_ollama_identity_requires_one_exact_canonical_tag(self):
        models = [
            {"name": "qwen2.5:1.5b", "model": "qwen2.5:1.5b", "digest": "sha256:a"},
            {"name": "qwen2.5:7b", "model": "qwen2.5:7b", "digest": "sha256:b"},
        ]
        with self.assertRaises(empirical.EmpiricalError):
            FakeOllama("qwen2.5", models=models).identity()
        client = FakeOllama("qwen2.5:1.5b", models=models)
        identity = client.identity()
        self.assertEqual(identity.model_id, "qwen2.5:1.5b")
        self.assertEqual(identity.immutable_revision, "sha256:a")
        self.assertEqual(client.model, "qwen2.5:1.5b")

    def test_generate_preserves_exact_raw_response_text_and_hash(self):
        raw = '{  "claims" : [] }'
        client = FakeOllama("demo:tag", response_text=raw)
        payload, metadata, exact = client.generate("prompt")
        self.assertEqual(payload, {"claims": []})
        self.assertEqual(exact, raw)
        self.assertEqual(
            metadata["raw_response_sha256"],
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        )

    def test_work_directory_refuses_repository_and_unmarked_existing_path(self):
        with self.assertRaises(empirical.EmpiricalError):
            runner._prepare_work_dir(ROOT)
        with tempfile.TemporaryDirectory() as temp_root:
            existing = Path(temp_root) / "someone-elses-directory"
            existing.mkdir()
            (existing / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(empirical.EmpiricalError):
                runner._prepare_work_dir(existing)
            self.assertTrue((existing / "keep.txt").is_file())

    def test_empirical_protocol_schema_and_executable_constants_agree(self):
        protocol = empirical.load_empirical_protocol(ROOT)
        self.assertEqual(tuple(protocol["conditions"]), empirical.CONDITIONS)
        self.assertEqual(tuple(protocol["paired_variants"].keys()), empirical.VARIANTS)
        self.assertEqual(protocol["cold_consumer_gate"], empirical.DEFAULT_THRESHOLDS)
        self.assertTrue(protocol["consumer_contract"]["treatment_assignment_blinded"])
        self.assertTrue(protocol["consumer_contract"]["evidence_reference_violations_fail_gate"])

    def test_workflow_default_model_matches_machine_protocol(self):
        protocol = empirical.load_empirical_protocol(ROOT)
        model = protocol["default_local_runner"]["model"]
        workflow = (ROOT / ".github/workflows/phase9-empirical-consumer.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("default: " + model, workflow)
        self.assertIn("inputs.model || '" + model + "'", workflow)

    def _summary_fixture(self):
        identity = empirical.ModelIdentity("ollama-local", "demo:tag", "sha256:abc")
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
        return identity, manifest

    def test_protocol_failure_is_recorded_as_model_outcome_not_harness_failure(self):
        identity, manifest = self._summary_fixture()
        protocol = empirical.load_empirical_protocol(ROOT)
        results = []
        for condition in empirical.CONDITIONS:
            for variant in empirical.VARIANTS:
                if condition == "micro" and variant == "guarded":
                    results.append({
                        "condition": condition,
                        "variant": variant,
                        "report": None,
                        "protocol_error": "consumer omitted frozen claims: mr1-030",
                        "cold_consumer_gate": runner._protocol_failure_gate(
                            "consumer omitted frozen claims: mr1-030"
                        ),
                    })
                else:
                    results.append({
                        "condition": condition,
                        "variant": variant,
                        "report": {"metrics": {
                            "primary_status_accuracy": 0.8,
                            "register_accuracy": 0.8,
                            "evidence_fidelity": 0.8,
                            "unsupported_assertion_rate": 0.0,
                        }},
                        "cold_consumer_gate": {"passed": False},
                    })
        summary = runner._summarize_results(results, manifest, identity, protocol)
        self.assertEqual(summary["consumer_protocol_failure_count"], 1)
        self.assertFalse(summary["cold_consumer_demonstrated"])
        micro = next(row for row in summary["rows"] if row["condition"] == "micro")
        self.assertEqual(micro["guarded_protocol_error"], "consumer omitted frozen claims: mr1-030")
        self.assertIsNone(micro["guarded"])
        self.assertIsNone(micro["guard_effect"]["primary_status_accuracy_delta"])
        self.assertFalse(micro["cold_consumer_gate"]["passed"])

    def test_experiment_summary_reports_guard_deltas_without_claiming_causality(self):
        identity, manifest = self._summary_fixture()
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
