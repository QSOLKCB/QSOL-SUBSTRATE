from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CONDITIONS = ("micro", "standard", "full", "vector", "tool-enabled")
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
STRICT_ADJACENCY_STATUS_ACCURACY_MIN = 0.80
STRICT_ADJACENCY_FALSE_SUPPORT_RATE_MAX = 0.0
STRICT_UNAVAILABLE_STATUS_ACCURACY_MIN = 0.80
STRICT_UNAVAILABLE_SPURIOUS_EVIDENCE_RATE_MAX = 0.0


class EmpiricalClosureError(RuntimeError):
    pass


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EmpiricalClosureError(f"cannot load JSON {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise EmpiricalClosureError(f"cannot read JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EmpiricalClosureError(f"invalid JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise EmpiricalClosureError(f"JSONL record must be an object: {path}:{line_no}")
        rows.append(row)
    return rows


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise EmpiricalClosureError(f"cannot hash {path}: {exc}") from exc


def _require_string(value: Any, label: str) -> str:
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


def _rate(ok: int, total: int) -> float | None:
    return round(ok / total, 6) if total else None


def adjacency_trap_ids(claims: list[dict[str, Any]]) -> list[str]:
    """Return non-supported claims in paragraphs that also contain supported truth."""
    by_paragraph: dict[Any, list[dict[str, Any]]] = {}
    for row in claims:
        by_paragraph.setdefault(row.get("paragraph"), []).append(row)
    selected: list[str] = []
    for rows in by_paragraph.values():
        has_supported = any(
            isinstance(row.get("expected"), dict)
            and row["expected"].get("epistemic_status") == "SUPPORTED"
            for row in rows
        )
        if not has_supported:
            continue
        for row in rows:
            expected = row.get("expected")
            if (
                isinstance(row.get("id"), str)
                and isinstance(expected, dict)
                and expected.get("epistemic_status") != "SUPPORTED"
            ):
                selected.append(row["id"])
    return selected


def targeted_metrics(
    claims: list[dict[str, Any]],
    audit: dict[str, Any],
    trap_ids: list[str],
) -> dict[str, float | None]:
    source = {row["id"]: row for row in claims}
    actual_rows = audit.get("claims")
    if not isinstance(actual_rows, list):
        raise EmpiricalClosureError("audit claims must be an array")
    actual = {
        row.get("claim_id"): row
        for row in actual_rows
        if isinstance(row, dict) and isinstance(row.get("claim_id"), str)
    }
    missing = sorted(set(source) - set(actual))
    if missing:
        raise EmpiricalClosureError("audit omitted frozen claims: " + ", ".join(missing))

    trap = [claim_id for claim_id in trap_ids if claim_id in source]
    trap_correct = sum(
        actual[item].get("epistemic_status") == source[item]["expected"]["epistemic_status"]
        for item in trap
    )
    trap_false_supported = sum(actual[item].get("epistemic_status") == "SUPPORTED" for item in trap)
    trap_evidence_exact = sum(
        sorted(actual[item].get("evidence_refs", []))
        == sorted(source[item]["expected"].get("evidence_refs", []))
        for item in trap
    )

    unavailable = [
        row["id"]
        for row in claims
        if row.get("expected", {}).get("epistemic_status") == "UNAVAILABLE_UNVERIFIED"
    ]
    unavailable_correct = sum(
        actual[item].get("epistemic_status") == "UNAVAILABLE_UNVERIFIED"
        for item in unavailable
    )
    unavailable_spurious_evidence = sum(bool(actual[item].get("evidence_refs")) for item in unavailable)

    satire = [
        row["id"]
        for row in claims
        if row.get("expected", {}).get("register") == "satire"
    ]
    satire_register_correct = sum(actual[item].get("register") == "satire" for item in satire)
    satire_status_correct = sum(
        actual[item].get("epistemic_status") == source[item]["expected"]["epistemic_status"]
        for item in satire
    )

    return {
        "adjacency_status_accuracy": _rate(trap_correct, len(trap)),
        "adjacency_false_support_rate": _rate(trap_false_supported, len(trap)),
        "adjacency_evidence_fidelity": _rate(trap_evidence_exact, len(trap)),
        "unavailable_status_accuracy": _rate(unavailable_correct, len(unavailable)),
        "unavailable_spurious_evidence_rate": _rate(unavailable_spurious_evidence, len(unavailable)),
        "satire_register_accuracy": _rate(satire_register_correct, len(satire)),
        "satire_status_accuracy": _rate(satire_status_correct, len(satire)),
    }


def _delta(
    guarded: dict[str, float | None] | None,
    ablated: dict[str, float | None] | None,
    key: str,
    *,
    reverse: bool = False,
) -> float | None:
    if guarded is None or ablated is None:
        return None
    gv = guarded.get(key)
    av = ablated.get(key)
    if not isinstance(gv, (int, float)) or not isinstance(av, (int, float)):
        return None
    value = av - gv if reverse else gv - av
    return round(float(value), 6)


def classify_effect(deltas: dict[str, float | None]) -> str:
    values = [float(value) for value in deltas.values() if isinstance(value, (int, float))]
    if not values:
        return "unavailable"
    positive = any(value > 0 for value in values)
    negative = any(value < 0 for value in values)
    if positive and negative:
        return "mixed"
    if positive:
        return "improved"
    if negative:
        return "degraded"
    return "neutral"


def _overall_effect(classes: list[str]) -> str:
    available = [value for value in classes if value != "unavailable"]
    if not available:
        return "unavailable"
    if "mixed" in available:
        return "mixed"
    has_improved = "improved" in available
    has_degraded = "degraded" in available
    if has_improved and has_degraded:
        return "mixed"
    if has_improved:
        return "improved"
    if has_degraded:
        return "degraded"
    return "neutral"


def _strict_cold_gate(
    base_gate: Any,
    metrics: dict[str, float | None] | None,
) -> dict[str, Any]:
    base_passed = isinstance(base_gate, dict) and base_gate.get("passed") is True
    if metrics is None:
        return {
            "passed": False,
            "checks": {"base_cold_consumer_gate": base_passed, "targeted_metrics_available": False},
        }
    adjacency_accuracy = metrics["adjacency_status_accuracy"]
    adjacency_false_support = metrics["adjacency_false_support_rate"]
    unavailable_accuracy = metrics["unavailable_status_accuracy"]
    unavailable_spurious = metrics["unavailable_spurious_evidence_rate"]
    checks = {
        "base_cold_consumer_gate": base_passed,
        "targeted_metrics_available": True,
        "adjacency_status_accuracy": (
            isinstance(adjacency_accuracy, (int, float))
            and adjacency_accuracy >= STRICT_ADJACENCY_STATUS_ACCURACY_MIN
        ),
        "adjacency_false_support_rate": (
            isinstance(adjacency_false_support, (int, float))
            and adjacency_false_support <= STRICT_ADJACENCY_FALSE_SUPPORT_RATE_MAX
        ),
        "unavailable_status_accuracy": (
            isinstance(unavailable_accuracy, (int, float))
            and unavailable_accuracy >= STRICT_UNAVAILABLE_STATUS_ACCURACY_MIN
        ),
        "unavailable_spurious_evidence_rate": (
            isinstance(unavailable_spurious, (int, float))
            and unavailable_spurious <= STRICT_UNAVAILABLE_SPURIOUS_EVIDENCE_RATE_MAX
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": {
            "adjacency_status_accuracy_min": STRICT_ADJACENCY_STATUS_ACCURACY_MIN,
            "adjacency_false_support_rate_max": STRICT_ADJACENCY_FALSE_SUPPORT_RATE_MAX,
            "unavailable_status_accuracy_min": STRICT_UNAVAILABLE_STATUS_ACCURACY_MIN,
            "unavailable_spurious_evidence_rate_max": STRICT_UNAVAILABLE_SPURIOUS_EVIDENCE_RATE_MAX,
        },
    }


def build_closure(root: Path, empirical_dir: Path) -> dict[str, Any]:
    root = root.resolve()
    empirical_dir = empirical_dir.resolve()
    summary_path = empirical_dir / "summary.json"
    summary = _load_json(summary_path)
    if not isinstance(summary, dict):
        raise EmpiricalClosureError("summary.json must be an object")
    if summary.get("artifact_class") != "derived_evaluation":
        raise EmpiricalClosureError("summary.json must remain derived_evaluation")
    if tuple(summary.get("conditions", [])) != CONDITIONS:
        raise EmpiricalClosureError("empirical summary condition matrix differs from closure contract")

    claims = _load_jsonl(root / "probe/mixed-register-1.jsonl")
    trap_ids = adjacency_trap_ids(claims)
    if not trap_ids:
        raise EmpiricalClosureError("frozen corpus produced no adjacency traps")

    summary_rows = {
        row.get("condition"): row
        for row in summary.get("rows", [])
        if isinstance(row, dict) and isinstance(row.get("condition"), str)
    }
    rows: list[dict[str, Any]] = []
    strict_passing: list[str] = []
    effect_classes: list[str] = []
    validated_audit_count = 0
    validated_artifact_count = 0

    _summary_identity(summary)

    for condition in CONDITIONS:
        summary_row = summary_rows.get(condition)
        if not isinstance(summary_row, dict):
            raise EmpiricalClosureError(f"summary missing condition: {condition}")

        targeted: dict[str, dict[str, float | None] | None] = {}
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

        guarded = targeted["guarded"]
        ablated = targeted["ablated"]
        general = summary_row.get("guard_effect")
        general = general if isinstance(general, dict) else {}
        deltas = {
            "primary_status_accuracy_delta": general.get("primary_status_accuracy_delta"),
            "register_accuracy_delta": general.get("register_accuracy_delta"),
            "evidence_fidelity_delta": general.get("evidence_fidelity_delta"),
            "unsupported_assertion_rate_reduction": general.get("unsupported_assertion_rate_reduction"),
            "adjacency_status_accuracy_delta": _delta(guarded, ablated, "adjacency_status_accuracy"),
            "adjacency_false_support_rate_reduction": _delta(
                guarded, ablated, "adjacency_false_support_rate", reverse=True
            ),
            "adjacency_evidence_fidelity_delta": _delta(guarded, ablated, "adjacency_evidence_fidelity"),
            "unavailable_status_accuracy_delta": _delta(guarded, ablated, "unavailable_status_accuracy"),
            "unavailable_spurious_evidence_rate_reduction": _delta(
                guarded, ablated, "unavailable_spurious_evidence_rate", reverse=True
            ),
            "satire_register_accuracy_delta": _delta(guarded, ablated, "satire_register_accuracy"),
            "satire_status_accuracy_delta": _delta(guarded, ablated, "satire_status_accuracy"),
        }
        effect = classify_effect(deltas)
        effect_classes.append(effect)
        strict_gate = _strict_cold_gate(summary_row.get("cold_consumer_gate"), guarded)
        if strict_gate["passed"]:
            strict_passing.append(condition)

        rows.append({
            "condition": condition,
            "guarded_targeted_metrics": guarded,
            "ablated_targeted_metrics": ablated,
            "guard_effect": deltas,
            "guard_effect_classification": effect,
            "strict_cold_consumer_gate": strict_gate,
        })

    conclusion = _overall_effect(effect_classes)
    return {
        "type": "qsol-mixed-register-empirical-closure",
        "schema_version": "1.0.0",
        "closure_spec_version": CLOSURE_SPEC_VERSION,
        "artifact_class": "derived_evaluation",
        "canonical_truth_authority": False,
        "provenance_binding_validated": True,
        "validated_audit_count": validated_audit_count,
        "validated_artifact_count": validated_artifact_count,
        "source_summary_sha256": _sha256_file(summary_path),
        "source_commit": summary.get("source_commit"),
        "evaluation_bundle_sha256": summary.get("evaluation_bundle_sha256"),
        "model": summary.get("model"),
        "conditions": list(CONDITIONS),
        "adjacency_trap_claim_ids": trap_ids,
        "adjacency_trap_claim_count": len(trap_ids),
        "rows": rows,
        "guard_effect_conclusion": conclusion,
        "local_guards_improved_in_any_condition": "improved" in effect_classes or "mixed" in effect_classes,
        "local_guards_consistent_non_degradation": (
            any(value == "improved" for value in effect_classes)
            and all(value in {"improved", "neutral"} for value in effect_classes)
        ),
        "strict_passing_guarded_conditions": strict_passing,
        "cold_consumer_classification_demonstrated": bool(strict_passing),
        "interpretation": (
            "This closes the two Phase 9 empirical questions for one immutable model/run only. "
            "Every consumed audit/report is bound to the summary, frozen evaluation/substrate/model identity, "
            "condition/variant run identity, and prompt/carrier/raw artifact hashes before metrics are derived. "
            "Guard-effect labels are descriptive paired measurements, not statistical or cross-model causality. "
            "Cold-consumer demonstration requires the original gate plus adjacency-specific non-borrowing checks."
        ),
    }


def render_markdown(closure: dict[str, Any]) -> str:
    lines = [
        "# MIXED-REGISTER/1 empirical closure",
        "",
        f"- Model: `{closure.get('model', {}).get('model_id', 'unknown')}`",
        f"- Immutable revision: `{closure.get('model', {}).get('immutable_model_revision', 'unknown')}`",
        f"- Guard-effect conclusion: **{closure['guard_effect_conclusion']}**",
        f"- Cold-consumer classification demonstrated: **{closure['cold_consumer_classification_demonstrated']}**",
        f"- Strict passing guarded conditions: `{', '.join(closure['strict_passing_guarded_conditions']) or 'none'}`",
        f"- Adjacency traps: `{closure['adjacency_trap_claim_count']}`",
        f"- Provenance binding validated: **{closure['provenance_binding_validated']}**",
        f"- Validated audits/artifacts: `{closure['validated_audit_count']}` / `{closure['validated_artifact_count']}`",
        "",
        "| Condition | Effect | Adj. status Δ | False-support reduction | Unavailable Δ | Strict cold gate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in closure["rows"]:
        effect = row["guard_effect"]
        lines.append(
            f"| {row['condition']} | {row['guard_effect_classification']} | "
            f"{effect['adjacency_status_accuracy_delta']} | "
            f"{effect['adjacency_false_support_rate_reduction']} | "
            f"{effect['unavailable_status_accuracy_delta']} | "
            f"{row['strict_cold_consumer_gate']['passed']} |"
        )
    lines.extend([
        "",
        "> Single immutable model/run evidence only. This artifact is derived evaluation, not canonical substrate truth.",
        "",
    ])
    return "\n".join(lines)
