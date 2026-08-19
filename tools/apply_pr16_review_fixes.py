#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected exactly one replacement target, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(relative: str, marker: str, addition: str) -> None:
    replace_once(relative, marker, addition + marker)


def patch_mode_core() -> None:
    old = '''def compare_mode_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    identity_fields = ("mode_bundle_sha256", "mode_policy_sha256", "source_commit", "substrate_sha256")
    for field in identity_fields:
        if left.get(field) != right.get(field):
            raise ModeError(f"cannot compare reports with different {field}")
    if left.get("model") != right.get("model"):
        raise ModeError("condition comparison requires exact same model identity/revision")
    lm = left.get("metrics", {})
    rm = right.get("metrics", {})
    if not isinstance(lm, dict) or not isinstance(rm, dict):
        raise ModeError("reports missing metrics")
    return {
        "type": "qsol-mode-confusion-comparison",
        "schema_version": "1.0.0",
        "mode_bundle_sha256": left["mode_bundle_sha256"],
        "mode_policy_sha256": left["mode_policy_sha256"],
        "model": left["model"],
        "left_condition": left.get("condition"),
        "right_condition": right.get("condition"),
        "delta": {
            "accuracy": round(float(rm["accuracy"]) - float(lm["accuracy"]), 6),
            "reason_code_accuracy": round(float(rm["reason_code_accuracy"]) - float(lm["reason_code_accuracy"]), 6),
            "false_mode_ok_rate": round(float(rm["false_mode_ok_rate"]) - float(lm["false_mode_ok_rate"]), 6),
            "cross_mode_accuracy": (
                round(float(rm["cross_mode_accuracy"]) - float(lm["cross_mode_accuracy"]), 6)
                if lm.get("cross_mode_accuracy") is not None and rm.get("cross_mode_accuracy") is not None
                else None
            ),
        },
        "interpretation": "Positive accuracy/reason-code/cross-mode deltas favor the right condition; negative false-mode-OK delta favors the right condition.",
    }
'''
    new = '''def compare_mode_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    for label, report in (("left", left), ("right", right)):
        _require_schema_valid(root, MODE_REPORT_SCHEMA, report, f"mode comparison {label} report")
        if report.get("execution_kind") != "empirical_consumer" or report.get("empirical_model_result") is not True:
            raise ModeError(
                "mode condition comparison requires schema-valid empirical_consumer reports; "
                "scoring-oracle and non-empirical reports are refused"
            )

    identity_fields = ("mode_bundle_sha256", "mode_policy_sha256", "source_commit", "substrate_sha256")
    for field in identity_fields:
        if left.get(field) != right.get(field):
            raise ModeError(f"cannot compare reports with different {field}")
    if left.get("model") != right.get("model"):
        raise ModeError("condition comparison requires exact same model identity/revision")
    if left.get("condition") == right.get("condition"):
        raise ModeError("condition comparison requires two distinct delivery conditions")

    lm = left["metrics"]
    rm = right["metrics"]
    return {
        "type": "qsol-mode-confusion-comparison",
        "schema_version": "1.0.0",
        "artifact_class": "derived_evaluation",
        "execution_kind": "empirical_consumer_comparison",
        "empirical_model_result": True,
        "mode_bundle_sha256": left["mode_bundle_sha256"],
        "mode_policy_sha256": left["mode_policy_sha256"],
        "source_commit": left["source_commit"],
        "substrate_sha256": left["substrate_sha256"],
        "model": left["model"],
        "left_condition": left["condition"],
        "right_condition": right["condition"],
        "delta": {
            "accuracy": round(float(rm["accuracy"]) - float(lm["accuracy"]), 6),
            "reason_code_accuracy": round(float(rm["reason_code_accuracy"]) - float(lm["reason_code_accuracy"]), 6),
            "false_mode_ok_rate": round(float(rm["false_mode_ok_rate"]) - float(lm["false_mode_ok_rate"]), 6),
            "cross_mode_accuracy": (
                round(float(rm["cross_mode_accuracy"]) - float(lm["cross_mode_accuracy"]), 6)
                if lm.get("cross_mode_accuracy") is not None and rm.get("cross_mode_accuracy") is not None
                else None
            ),
        },
        "interpretation": (
            "This is a derived comparison of two schema-valid empirical-consumer reports for one exact "
            "model revision and frozen mode/substrate identity. Positive accuracy/reason-code/cross-mode "
            "deltas favor the right condition; negative false-mode-OK delta favors the right condition."
        ),
    }
'''
    replace_once("tools/mode_core.py", old, new)


def patch_run_summary_bindings() -> None:
    marker = '''def main() -> int:
'''
    addition = '''def _file_binding(output_dir: Path, relative: str) -> dict[str, object] | None:
    path = output_dir / relative
    if not path.is_file() or path.is_symlink():
        return None
    data = path.read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def _artifact_bindings(output_dir: Path) -> dict[str, object]:
    bindings: dict[str, object] = {}
    for condition in CONDITIONS:
        variants: dict[str, object] = {}
        for variant in ("guarded", "ablated"):
            stem = f"{condition}.{variant}"
            variants[variant] = {
                "prompt": _file_binding(output_dir, f"prompts/{stem}.txt"),
                "carrier": _file_binding(output_dir, f"carriers/{stem}.txt"),
                "raw_response": _file_binding(output_dir, f"raw/{stem}.response.json"),
                "audit": _file_binding(output_dir, f"audits/{stem}.json"),
                "report": _file_binding(output_dir, f"reports/{stem}.json"),
            }
        bindings[condition] = variants
    return bindings


'''
    insert_before("tools/run_mixed_register_empirical.py", marker, addition)

    old = '''        summary["protocol_sha256"] = hashlib.sha256(
            (ROOT / "empirical/mixed-register/experiment.json").read_bytes()
        ).hexdigest()
        _write_json(output_dir / "summary.json", summary)
'''
    new = '''        summary["protocol_sha256"] = hashlib.sha256(
            (ROOT / "empirical/mixed-register/experiment.json").read_bytes()
        ).hexdigest()
        summary["artifact_bindings"] = _artifact_bindings(output_dir)
        _write_json(output_dir / "summary.json", summary)
'''
    replace_once("tools/run_mixed_register_empirical.py", old, new)


def patch_closure() -> None:
    old_constants = '''CONDITIONS = ("micro", "standard", "full", "vector", "tool-enabled")
PRIMARY_STATUSES = ("SUPPORTED", "CONTRADICTED", "UNAVAILABLE_UNVERIFIED")
CLOSURE_SPEC_VERSION = "1.0.0"
'''
    new_constants = '''CONDITIONS = ("micro", "standard", "full", "vector", "tool-enabled")
VARIANTS = ("guarded", "ablated")
PRIMARY_STATUSES = ("SUPPORTED", "CONTRADICTED", "UNAVAILABLE_UNVERIFIED")
CLOSURE_SPEC_VERSION = "1.0.0"
ARTIFACT_LAYOUT = {
    "prompt": "prompts/{stem}.txt",
    "carrier": "carriers/{stem}.txt",
    "raw_response": "raw/{stem}.response.json",
    "audit": "audits/{stem}.json",
    "report": "reports/{stem}.json",
}
'''
    replace_once("tools/mixed_register_empirical_closure.py", old_constants, new_constants)

    marker = '''def _rate(ok: int, total: int) -> float | None:
'''
    addition = '''def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise EmpiricalClosureError(f"{label} must be a non-empty string")
    return value


def _summary_identity(summary: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any], str]:
    bundle_sha = _require_string(summary.get("evaluation_bundle_sha256"), "summary evaluation bundle")
    source_commit = _require_string(summary.get("source_commit"), "summary source_commit")
    if len(bundle_sha) != 64 or len(source_commit) != 40:
        raise EmpiricalClosureError("summary uses malformed frozen identity hashes")

    substrate = summary.get("substrate")
    model = summary.get("model")
    if not isinstance(substrate, dict) or not isinstance(model, dict):
        raise EmpiricalClosureError("summary substrate/model identity must be objects")
    if substrate.get("source_commit") != source_commit:
        raise EmpiricalClosureError("summary source_commit differs from substrate source_commit")
    for key in ("provider", "model_id", "immutable_model_revision"):
        _require_string(model.get(key), f"summary model.{key}")
    return bundle_sha, substrate, model, source_commit


def _validate_file_binding(
    empirical_dir: Path,
    binding: Any,
    expected_relative: str,
    label: str,
) -> tuple[Path, str]:
    if not isinstance(binding, dict):
        raise EmpiricalClosureError(f"{label} binding must be an object")
    if binding.get("path") != expected_relative:
        raise EmpiricalClosureError(f"{label} binding path mismatch")
    path = empirical_dir / expected_relative
    if path.is_symlink() or not path.is_file():
        raise EmpiricalClosureError(f"{label} bound artifact is missing or symlinked")
    resolved = path.resolve()
    if empirical_dir != resolved.parent and empirical_dir not in resolved.parents:
        raise EmpiricalClosureError(f"{label} bound artifact escapes empirical directory")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if binding.get("sha256") != digest or binding.get("bytes") != len(data):
        raise EmpiricalClosureError(f"{label} artifact hash/size mismatch")
    return path, digest


def _validated_audit(
    empirical_dir: Path,
    summary: dict[str, Any],
    summary_row: dict[str, Any],
    condition: str,
    variant: str,
) -> tuple[dict[str, Any] | None, int]:
    bindings = summary.get("artifact_bindings")
    if not isinstance(bindings, dict):
        raise EmpiricalClosureError("summary artifact_bindings must be an object")
    condition_bindings = bindings.get(condition)
    if not isinstance(condition_bindings, dict):
        raise EmpiricalClosureError(f"summary artifact bindings missing condition: {condition}")
    variant_bindings = condition_bindings.get(variant)
    if not isinstance(variant_bindings, dict):
        raise EmpiricalClosureError(f"summary artifact bindings missing {condition}/{variant}")

    stem = f"{condition}.{variant}"
    validated: dict[str, tuple[Path, str]] = {}
    artifact_count = 0
    for key in ("prompt", "carrier", "raw_response"):
        relative = ARTIFACT_LAYOUT[key].format(stem=stem)
        validated[key] = _validate_file_binding(
            empirical_dir, variant_bindings.get(key), relative, f"{condition}/{variant} {key}"
        )
        artifact_count += 1

    protocol_error = summary_row.get(f"{variant}_protocol_error")
    audit_binding = variant_bindings.get("audit")
    report_binding = variant_bindings.get("report")
    if audit_binding is None or report_binding is None:
        if protocol_error:
            if audit_binding is not None or report_binding is not None:
                raise EmpiricalClosureError(f"{condition}/{variant} has partial audit/report binding")
            return None, artifact_count
        raise EmpiricalClosureError(f"{condition}/{variant} is missing audit/report without protocol failure")

    audit_path, _ = _validate_file_binding(
        empirical_dir,
        audit_binding,
        ARTIFACT_LAYOUT["audit"].format(stem=stem),
        f"{condition}/{variant} audit",
    )
    report_path, _ = _validate_file_binding(
        empirical_dir,
        report_binding,
        ARTIFACT_LAYOUT["report"].format(stem=stem),
        f"{condition}/{variant} report",
    )
    artifact_count += 2

    audit = _load_json(audit_path)
    report = _load_json(report_path)
    if not isinstance(audit, dict) or not isinstance(report, dict):
        raise EmpiricalClosureError(f"{condition}/{variant} audit/report must be objects")

    bundle_sha, substrate, model, _ = _summary_identity(summary)
    expected_run_id = f"mixed-register-cold:{model['model_id']}:{condition}:{variant}"
    expected_prompt_identity = (
        f"MIXED-REGISTER/1-COLD-CONSUMER/{summary.get('empirical_spec_version')}:{variant}"
    )
    expected_tool_mode = "repository" if condition == "tool-enabled" else "none"

    checks = {
        "type": audit.get("type") == "qsol-claim-audit",
        "artifact_class": audit.get("artifact_class") == "derived_evaluation",
        "execution_kind": audit.get("execution_kind") == "empirical_consumer",
        "run_id": audit.get("run_id") == expected_run_id,
        "evaluator": audit.get("evaluator") == model,
        "condition": audit.get("condition") == condition,
        "tool_mode": audit.get("tool_mode") == expected_tool_mode,
        "prompt_test_identity": audit.get("prompt_test_identity") == expected_prompt_identity,
        "evaluation_bundle_sha256": audit.get("evaluation_bundle_sha256") == bundle_sha,
        "substrate": audit.get("substrate") == substrate,
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise EmpiricalClosureError(
            f"{condition}/{variant} audit provenance binding mismatch: {', '.join(failed)}"
        )

    hashes = audit.get("artifact_hashes")
    if not isinstance(hashes, dict):
        raise EmpiricalClosureError(f"{condition}/{variant} audit artifact_hashes must be an object")
    expected_hashes = {
        "evaluation_bundle": bundle_sha,
        "empirical_prompt": validated["prompt"][1],
        "empirical_carrier": validated["carrier"][1],
        "raw_consumer_response": validated["raw_response"][1],
    }
    mismatched_hashes = [
        key for key, value in expected_hashes.items() if hashes.get(key) != value
    ]
    if mismatched_hashes:
        raise EmpiricalClosureError(
            f"{condition}/{variant} audit artifact hash binding mismatch: "
            + ", ".join(mismatched_hashes)
        )

    report_checks = {
        "type": report.get("type") == "qsol-mixed-register-report",
        "artifact_class": report.get("artifact_class") == "derived_evaluation",
        "execution_kind": report.get("execution_kind") == "empirical_consumer",
        "run_id": report.get("run_id") == expected_run_id,
        "evaluator": report.get("evaluator") == model,
        "condition": report.get("condition") == condition,
        "evaluation_bundle_sha256": report.get("evaluation_bundle_sha256") == bundle_sha,
        "substrate": report.get("substrate") == substrate,
        "metrics": report.get("metrics") == summary_row.get(variant),
    }
    failed_report = [key for key, passed in report_checks.items() if not passed]
    if failed_report:
        raise EmpiricalClosureError(
            f"{condition}/{variant} report provenance binding mismatch: "
            + ", ".join(failed_report)
        )
    return audit, artifact_count


'''
    insert_before("tools/mixed_register_empirical_closure.py", marker, addition)

    old_loop = '''    rows: list[dict[str, Any]] = []
    strict_passing: list[str] = []
    effect_classes: list[str] = []

    for condition in CONDITIONS:
'''
    new_loop = '''    rows: list[dict[str, Any]] = []
    strict_passing: list[str] = []
    effect_classes: list[str] = []
    validated_audit_count = 0
    validated_artifact_count = 0

    _summary_identity(summary)

    for condition in CONDITIONS:
'''
    replace_once("tools/mixed_register_empirical_closure.py", old_loop, new_loop)

    old_targeted = '''        targeted: dict[str, dict[str, float | None] | None] = {}
        for variant in ("guarded", "ablated"):
            audit_path = empirical_dir / "audits" / f"{condition}.{variant}.json"
            targeted[variant] = targeted_metrics(claims, _load_json(audit_path), trap_ids) if audit_path.is_file() else None
'''
    new_targeted = '''        targeted: dict[str, dict[str, float | None] | None] = {}
        for variant in VARIANTS:
            audit, artifact_count = _validated_audit(
                empirical_dir, summary, summary_row, condition, variant
            )
            validated_artifact_count += artifact_count
            if audit is None:
                targeted[variant] = None
            else:
                validated_audit_count += 1
                targeted[variant] = targeted_metrics(claims, audit, trap_ids)
'''
    replace_once("tools/mixed_register_empirical_closure.py", old_targeted, new_targeted)

    old_return = '''        "canonical_truth_authority": False,
        "source_summary_sha256": _sha256_file(summary_path),
        "source_commit": summary.get("source_commit"),
'''
    new_return = '''        "canonical_truth_authority": False,
        "provenance_binding_validated": True,
        "validated_audit_count": validated_audit_count,
        "validated_artifact_count": validated_artifact_count,
        "source_summary_sha256": _sha256_file(summary_path),
        "source_commit": summary.get("source_commit"),
'''
    replace_once("tools/mixed_register_empirical_closure.py", old_return, new_return)

    old_interpretation = '''            "This closes the two Phase 9 empirical questions for one immutable model/run only. "
            "Guard-effect labels are descriptive paired measurements, not statistical or cross-model causality. "
            "Cold-consumer demonstration requires the original gate plus adjacency-specific non-borrowing checks."
'''
    new_interpretation = '''            "This closes the two Phase 9 empirical questions for one immutable model/run only. "
            "Every consumed audit/report is bound to the summary, frozen evaluation/substrate/model identity, "
            "condition/variant run identity, and prompt/carrier/raw artifact hashes before metrics are derived. "
            "Guard-effect labels are descriptive paired measurements, not statistical or cross-model causality. "
            "Cold-consumer demonstration requires the original gate plus adjacency-specific non-borrowing checks."
'''
    replace_once("tools/mixed_register_empirical_closure.py", old_interpretation, new_interpretation)

    old_md = '''        f"- Adjacency traps: `{closure['adjacency_trap_claim_count']}`",
        "",
'''
    new_md = '''        f"- Adjacency traps: `{closure['adjacency_trap_claim_count']}`",
        f"- Provenance binding validated: **{closure['provenance_binding_validated']}**",
        f"- Validated audits/artifacts: `{closure['validated_audit_count']}` / `{closure['validated_artifact_count']}`",
        "",
'''
    replace_once("tools/mixed_register_empirical_closure.py", old_md, new_md)


def patch_closure_schema() -> None:
    old_required = '''"canonical_truth_authority", "source_summary_sha256"'''
    new_required = '''"canonical_truth_authority", "provenance_binding_validated", "validated_audit_count", "validated_artifact_count", "source_summary_sha256"'''
    replace_once("schema/mixed-register-empirical-closure.schema.json", old_required, new_required)

    old_props = '''    "canonical_truth_authority": {"const": false},
    "source_summary_sha256": {"$ref": "#/$defs/hash"},
'''
    new_props = '''    "canonical_truth_authority": {"const": false},
    "provenance_binding_validated": {"const": true},
    "validated_audit_count": {"type": "integer", "minimum": 0, "maximum": 10},
    "validated_artifact_count": {"type": "integer", "minimum": 0, "maximum": 50},
    "source_summary_sha256": {"$ref": "#/$defs/hash"},
'''
    replace_once("schema/mixed-register-empirical-closure.schema.json", old_props, new_props)


def patch_protocol_and_docs() -> None:
    replace_once(
        "empirical/mixed-register/experiment.json",
        '    "model": "qwen2.5:1.5b",',
        '    "model": "qwen2.5:3b",',
    )

    old_changelog = (
        "- Phase 9 empirical closure adds paired guarded/ablated mixed-register measurement, "
        "mechanically derived adjacency traps, false-support/spurious-evidence metrics, and a cold "
        "open-weight consumer workflow that remains `derived_evaluation` rather than canonical truth."
    )
    new_changelog = (
        "- Phase 9 empirical closure adds paired guarded/ablated mixed-register measurement, "
        "mechanically derived adjacency traps, false-support/spurious-evidence metrics, and a cold "
        "open-weight consumer workflow that remains `derived_evaluation` rather than canonical truth; "
        "closure now rejects mixed-run evidence by binding every audit/report to the summary, immutable "
        "model/substrate identity, condition/variant, and prompt/carrier/raw hashes."
    )
    replace_once("CHANGELOG.md", old_changelog, new_changelog)

    marker = '''`closure.json` derives adjacency traps from the frozen corpus, computes targeted guarded-versus-ablated metrics, classifies each condition as `improved`, `neutral`, `degraded`, `mixed`, or `unavailable`, and records whether at least one guarded condition satisfies the stricter cold-consumer criterion.

'''
    addition = '''Before deriving any metric, the closure pass verifies every available audit and scored report against `summary.json`: complete evaluation-bundle and substrate identity, immutable provider/model revision, condition and guarded/ablated run identity, plus the recorded prompt, carrier, raw-response, audit, and report hashes. Mixed-run or edited evidence is refused even when each individual JSON file remains schema-shaped.

'''
    insert_before("docs/MIXED_REGISTER_EMPIRICAL.md", marker, addition)


def patch_mode_tests() -> None:
    replace_once(
        "tests/test_mode_deferred.py",
        "import json\nimport shutil\n",
        "import copy\nimport json\nimport shutil\n",
    )
    replace_once(
        "tests/test_mode_deferred.py",
        '''    classify_case,
    policy_index,
''',
        '''    classify_case,
    compare_mode_reports,
    policy_index,
''',
    )

    marker = '''    def test_calibration_rejects_forged_oracle_boolean(self) -> None:
'''
    addition = '''    def test_mode_comparison_requires_schema_valid_empirical_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "modes"
            build_mode_bundle(ROOT, out, "6" * 40)
            oracle_run = build_oracle_run(out)
            oracle_report = score_mode_run(out, oracle_run)
            with self.assertRaisesRegex(ModeError, "empirical_consumer"):
                compare_mode_reports(oracle_report, oracle_report)

            left_run = copy.deepcopy(oracle_run)
            left_run["execution_kind"] = "empirical_consumer"
            left_run["condition"] = "micro"
            left_run["model"] = {
                "provider": "fixture",
                "model_id": "fixture-model",
                "model_revision": "fixture-revision",
            }
            right_run = copy.deepcopy(left_run)
            right_run["condition"] = "full"
            left_report = score_mode_run(out, left_run)
            right_report = score_mode_run(out, right_run)
            comparison = compare_mode_reports(left_report, right_report)
            self.assertEqual(comparison["execution_kind"], "empirical_consumer_comparison")
            self.assertTrue(comparison["empirical_model_result"])
            self.assertEqual(comparison["source_commit"], "6" * 40)

            malformed = copy.deepcopy(left_report)
            malformed["unexpected"] = True
            with self.assertRaisesRegex(ModeError, "mode comparison left report violates"):
                compare_mode_reports(malformed, right_report)

'''
    insert_before("tests/test_mode_deferred.py", marker, addition)


def patch_empirical_tests() -> None:
    marker = '''    def _summary_fixture(self):
'''
    addition = '''    def test_workflow_default_model_matches_machine_protocol(self):
        protocol = empirical.load_empirical_protocol(ROOT)
        model = protocol["default_local_runner"]["model"]
        workflow = (ROOT / ".github/workflows/phase9-empirical-consumer.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("default: " + model, workflow)
        self.assertIn("inputs.model || '" + model + "'", workflow)

'''
    insert_before("tests/test_phase9_empirical.py", marker, addition)


def rewrite_closure_tests() -> None:
    content = r'''from __future__ import annotations

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
'''
    (ROOT / "tests/test_phase9_empirical_closure.py").write_text(content, encoding="utf-8")


def main() -> None:
    patch_mode_core()
    patch_run_summary_bindings()
    patch_closure()
    patch_closure_schema()
    patch_protocol_and_docs()
    patch_mode_tests()
    patch_empirical_tests()
    rewrite_closure_tests()
    print("Applied PR #16 empirical and Codex review fixes.")


if __name__ == "__main__":
    main()
