from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CONDITIONS = ("micro", "standard", "full", "vector", "tool-enabled")
PRIMARY_STATUSES = ("SUPPORTED", "CONTRADICTED", "UNAVAILABLE_UNVERIFIED")
CLOSURE_SPEC_VERSION = "1.0.0"
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

    for condition in CONDITIONS:
        summary_row = summary_rows.get(condition)
        if not isinstance(summary_row, dict):
            raise EmpiricalClosureError(f"summary missing condition: {condition}")

        targeted: dict[str, dict[str, float | None] | None] = {}
        for variant in ("guarded", "ablated"):
            audit_path = empirical_dir / "audits" / f"{condition}.{variant}.json"
            targeted[variant] = targeted_metrics(claims, _load_json(audit_path), trap_ids) if audit_path.is_file() else None

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
