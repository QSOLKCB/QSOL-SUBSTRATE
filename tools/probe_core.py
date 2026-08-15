from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import probe_core_base as _base
from probe_core_base import *  # noqa: F401,F403

_ORIGINAL_BUILD_PROBE_BUNDLE = _base.build_probe_bundle
_ORIGINAL_VALIDATE_PROBE_BUNDLE = _base.validate_probe_bundle

_REPRODUCIBILITY_PATHS = (
    "ai",
    "schema",
    "probe",
    "tools",
    "sources",
    "identity",
    "context",
    "terminology",
    "projects",
    "publications",
    "relationships",
    "chronology",
)
_PROJECTION_COMPATIBILITY_SCHEMA = "schema/model-projection-compatibility.schema.json"
_LATENT_PREFIX_KINDS = {"soft_prompt", "virtual_tokens", "lora", "kv_cache", "prefix_state"}


def _git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProbeError(f"cannot verify probe source checkout with git: {exc}") from exc
    return result.stdout


def checked_out_source_commit(root: Path) -> str:
    root = root.resolve()
    commit = _git_output(root, "rev-parse", "--verify", "HEAD^{commit}").strip()
    if len(commit) != 40:
        raise ProbeError("git HEAD did not resolve to a full 40-character commit")
    return commit


def _meaningful_source_status(status: str) -> list[str]:
    dirty: list[str] = []
    for raw in status.splitlines():
        line = raw.strip()
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if "/__pycache__/" in path or path.endswith(".pyc"):
            continue
        dirty.append(line)
    return dirty


def _verify_source_checkout(root: Path, source_commit: str) -> None:
    root = root.resolve()
    head = checked_out_source_commit(root)
    if source_commit != head:
        raise ProbeError(
            f"probe source commit must equal checked-out HEAD: declared={source_commit} checked_out={head}"
        )
    status = _git_output(
        root,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        *_REPRODUCIBILITY_PATHS,
    )
    dirty = _meaningful_source_status(status)
    if dirty:
        raise ProbeError("refusing to stamp probe bundle from uncommitted source changes")


def build_probe_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    _verify_source_checkout(root, source_commit)
    return _ORIGINAL_BUILD_PROBE_BUNDLE(root, output, source_commit)


def validate_probe_bundle(
    root: Path,
    bundle: Path,
    schema_path: str = PROBE_MANIFEST_SCHEMA,
) -> list[ProbeFinding]:
    return _ORIGINAL_VALIDATE_PROBE_BUNDLE(root, bundle, schema_path)


def _expected_field_matches(expected: dict[str, Any], response: dict[str, Any], field: str) -> bool:
    if field in {"canonical_ids", "provenance_refs"}:
        wanted = expected.get(field, [])
        actual = response.get(field)
        if not isinstance(wanted, list) or not isinstance(actual, list):
            return False
        return set(actual) == set(wanted)
    if field not in expected:
        return True
    wanted = expected[field]
    actual = response.get(field)
    if field == "answer":
        return _base._normalise_answer(actual) == _base._normalise_answer(wanted)
    return actual == wanted


def _case_correct(case: dict[str, Any], response: dict[str, Any]) -> bool:
    return all(
        _expected_field_matches(case["expected"], response, field)
        for field in (
            "epistemic_state",
            "answer",
            "canonical_ids",
            "provenance_refs",
            "classification",
            "sarcasm",
            "hostility",
            "intent_polarity",
            "severity",
            "freshness_limited",
        )
    )


def _response_is_assertive(response: dict[str, Any]) -> bool:
    if response.get("answer") is not None:
        return True
    if response.get("canonical_ids") or response.get("provenance_refs"):
        return True
    return response.get("epistemic_state") not in {"unknown", "conflict"}


def _response_is_clean_unknown(response: dict[str, Any]) -> bool:
    return response.get("epistemic_state") == "unknown" and not _response_is_assertive(response)


def _validate_projection_execution(root: Path, run: dict[str, Any]) -> None:
    condition = run.get("condition")
    execution_kind = run.get("execution_kind")
    projection = run.get("projection_execution")
    requires_projection = execution_kind == "model" and condition in {"latent-prefix", "hybrid"}

    if not requires_projection:
        if projection is not None:
            raise ProbeError("projection_execution is only valid for empirical latent-prefix/hybrid runs")
        return

    if not isinstance(projection, dict):
        raise ProbeError("latent-prefix/hybrid model runs require projection_execution evidence")
    if projection.get("executed") is not True:
        raise ProbeError("projection_execution must attest executed=true")
    compatibility = projection.get("compatibility")
    if not isinstance(compatibility, dict):
        raise ProbeError("projection_execution requires a Phase 6 compatibility identity")
    errors = _base._schema_errors(root, _PROJECTION_COMPATIBILITY_SCHEMA, compatibility)
    if errors:
        raise ProbeError("projection compatibility schema violation at: " + ", ".join(errors[:8]))

    model = run["model"]
    if compatibility.get("model_id") != model.get("id"):
        raise ProbeError("projection compatibility model_id does not match run model")
    if compatibility.get("model_revision") != model.get("revision"):
        raise ProbeError("projection compatibility model_revision does not match run model")
    if compatibility.get("tokenizer_id") != run["usage"].get("tokenizer"):
        raise ProbeError("projection compatibility tokenizer_id does not match run tokenizer")

    projection_kind = compatibility.get("projection_kind")
    if condition == "hybrid" and projection_kind != "hybrid":
        raise ProbeError("hybrid condition requires projection_kind=hybrid")
    if condition == "latent-prefix" and projection_kind not in _LATENT_PREFIX_KINDS:
        raise ProbeError("latent-prefix condition requires a non-hybrid Phase 6 projection kind")


def score_probe_run(root: Path, bundle: Path, run: dict[str, Any]) -> dict[str, Any]:
    manifest = _base._require_valid_bundle(root, bundle)
    if run.get("probe_bundle_sha256") != manifest.get("bundle_sha256"):
        raise ProbeError("model run is bound to a different probe bundle")
    if run.get("substrate") != manifest.get("substrate"):
        raise ProbeError("model run substrate identity does not match probe bundle")
    _base._validate_run_shape(root, run)
    _validate_projection_execution(root, run)

    cases = _base.load_built_cases(bundle)
    case_by_id = {case["id"]: case for case in cases}
    responses = run["responses"]
    if len(responses) != len(cases):
        raise ProbeError("model run must contain exactly one response per probe")
    seen: set[str] = set()
    for response in responses:
        probe_id = response["probe_id"]
        if probe_id in seen:
            raise ProbeError(f"duplicate response for {probe_id}")
        seen.add(probe_id)
        if probe_id not in case_by_id:
            raise ProbeError(f"response references unknown probe id {probe_id}")
    if seen != set(case_by_id):
        raise ProbeError("model run response set does not match probe set")

    scored: list[dict[str, Any]] = []
    for response in responses:
        case = case_by_id[response["probe_id"]]
        scored.append({
            "probe_id": case["id"],
            "suite": case["suite"],
            "category": case["category"],
            "correct": _case_correct(case, response),
            "expected_epistemic_state": case["expected"]["epistemic_state"],
            "actual_epistemic_state": response["epistemic_state"],
            "confidence": response["confidence"],
        })

    total = len(scored)
    correct_count = sum(1 for item in scored if item["correct"])
    substrate_scored = [item for item in scored if item["suite"] == "substrate"]
    yn_scored = [item for item in scored if item["suite"] == "yeah-nah-1"]
    response_by_id = {response["probe_id"]: response for response in responses}

    factual_categories = {"exact_known_fact", "project_relationship", "publication_doi"}
    factual = [item for item in substrate_scored if item["category"] in factual_categories]
    aliases = [item for item in substrate_scored if item["category"] == "alias_resolution"]
    contradictions = [item for item in substrate_scored if item["category"] == "contradiction"]
    boundaries = [
        item for item in substrate_scored
        if item["category"] in {"satire_boundary", "formalization_boundary"}
    ]

    provenance_cases = [
        case_by_id[item["probe_id"]]
        for item in substrate_scored
        if case_by_id[item["probe_id"]]["expected"].get("provenance_refs", [])
        or response_by_id[item["probe_id"]].get("provenance_refs", [])
    ]
    provenance_hits = sum(
        int(
            set(case["expected"].get("provenance_refs", []))
            == set(response_by_id[case["id"]].get("provenance_refs", []))
        )
        for case in provenance_cases
    )

    substrate_ids = {case["id"] for case in cases if case["suite"] == "substrate"}
    expected_unknown_ids = {
        case["id"] for case in cases
        if case["suite"] == "substrate" and case["expected"]["epistemic_state"] == "unknown"
    }
    predicted_unknown_ids = {
        response["probe_id"] for response in responses
        if response["probe_id"] in substrate_ids and _response_is_clean_unknown(response)
    }
    unknown_tp = len(expected_unknown_ids & predicted_unknown_ids)
    unsupported_assertions = sum(
        int(_response_is_assertive(response_by_id[probe_id]))
        for probe_id in expected_unknown_ids
    )

    yn_ids = {case["id"] for case in cases if case["suite"] == "yeah-nah-1"}
    sarcasm_expected_yes = {
        case["id"] for case in cases
        if case["suite"] == "yeah-nah-1" and case["expected"].get("sarcasm") == "yes"
    }
    sarcasm_predicted_yes = {
        response["probe_id"] for response in responses
        if response["probe_id"] in yn_ids and response.get("sarcasm") == "yes"
    }
    sarcasm_tp = len(sarcasm_expected_yes & sarcasm_predicted_yes)

    literal_traps = [
        case for case in cases
        if case["suite"] == "yeah-nah-1" and "literal-trap" in case.get("tags", [])
    ]
    literal_trap_errors = sum(
        int(response_by_id[case["id"]].get("intent_polarity") != case["expected"].get("intent_polarity"))
        for case in literal_traps
    )

    banter_classes = {"banter", "mock_hostility", "affectionate_insult"}
    banter_cases = [
        case for case in cases
        if case["suite"] == "yeah-nah-1" and case["expected"].get("classification") in banter_classes
    ]
    banter_errors = sum(
        int(response_by_id[case["id"]].get("classification") not in banter_classes)
        for case in banter_cases
    )

    non_actual_hostility = [
        case for case in cases
        if case["suite"] == "yeah-nah-1" and case["expected"].get("hostility") != "actual"
    ]
    hostility_fp = sum(
        int(response_by_id[case["id"]].get("hostility") == "actual")
        for case in non_actual_hostility
    )

    understatement_cases = [
        case for case in cases
        if case["suite"] == "yeah-nah-1" and case["expected"].get("classification") == "understatement"
    ]
    understatement_preserved = sum(
        int(response_by_id[case["id"]].get("severity") == case["expected"].get("severity"))
        for case in understatement_cases
    )

    brier_values: list[float] = []
    for item in yn_scored:
        p = float(item["confidence"])
        outcome = 1.0 if item["correct"] else 0.0
        brier_values.append((p - outcome) ** 2)
    brier = round(sum(brier_values) / len(brier_values), 6) if brier_values else None

    input_tokens = int(run["usage"]["input_tokens"])
    token_eff = round(correct_count / (input_tokens / 1000.0), 6) if input_tokens > 0 else None

    metrics = {
        "overall_accuracy": _base._rate(correct_count, total),
        "factual_accuracy": _base._rate(sum(item["correct"] for item in factual), len(factual)),
        "unsupported_assertion_rate": _base._rate(unsupported_assertions, len(expected_unknown_ids)),
        "unknown_precision": _base._rate(unknown_tp, len(predicted_unknown_ids)),
        "unknown_recall": _base._rate(unknown_tp, len(expected_unknown_ids)),
        "alias_resolution_accuracy": _base._rate(sum(item["correct"] for item in aliases), len(aliases)),
        "provenance_fidelity": _base._rate(provenance_hits, len(provenance_cases)),
        "contradiction_handling": _base._rate(sum(item["correct"] for item in contradictions), len(contradictions)),
        "claim_boundary_preservation": _base._rate(sum(item["correct"] for item in boundaries), len(boundaries)),
        "context_token_efficiency": token_eff,
        "hallucination_rate": _base._rate(unsupported_assertions, len(expected_unknown_ids)),
    }
    yn_metrics = {
        "overall_accuracy": _base._rate(sum(item["correct"] for item in yn_scored), len(yn_scored)),
        "sarcasm_precision": _base._rate(sarcasm_tp, len(sarcasm_predicted_yes)),
        "sarcasm_recall": _base._rate(sarcasm_tp, len(sarcasm_expected_yes)),
        "literal_meaning_error_rate": _base._rate(literal_trap_errors, len(literal_traps)),
        "banter_misclassification_rate": _base._rate(banter_errors, len(banter_cases)),
        "hostility_false_positive_rate": _base._rate(hostility_fp, len(non_actual_hostility)),
        "understatement_severity_preservation_rate": _base._rate(understatement_preserved, len(understatement_cases)),
        "confidence_brier": brier,
    }

    category_metrics: dict[str, float | None] = {}
    for category in sorted({item["category"] for item in scored}):
        bucket = [item for item in scored if item["category"] == category]
        category_metrics[category] = _base._rate(sum(item["correct"] for item in bucket), len(bucket))

    report: dict[str, Any] = {
        "type": "qsol-probe-report-card",
        "schema_version": "1.0.0",
        "probe_spec_version": PROBE_SPEC_VERSION,
        "run_id": run["run_id"],
        "execution_kind": run["execution_kind"],
        "model": run["model"],
        "condition": run["condition"],
        "probe_bundle_sha256": run["probe_bundle_sha256"],
        "substrate": run["substrate"],
        "usage": run["usage"],
        "counts": {
            "total": total,
            "correct": correct_count,
            "substrate": len(substrate_scored),
            "yeah_nah_1": len(yn_scored),
        },
        "metrics": metrics,
        "yeah_nah_1": yn_metrics,
        "category_accuracy": category_metrics,
        "case_results": scored,
        "interpretation": (
            "Scores structured model outputs against deterministic probe ground truth. "
            "A scoring-oracle run validates the scorer only and is not an empirical model result."
        ),
    }
    if run.get("projection_execution") is not None:
        report["projection_execution"] = run["projection_execution"]

    errors = _base._schema_errors(root, PROBE_REPORT_SCHEMA, report)
    if errors:
        raise ProbeError("generated probe report schema violation at: " + ", ".join(errors[:8]))
    return report


def _model_identity_key(report: dict[str, Any]) -> tuple[str, str, str]:
    model = report["model"]
    return (model["id"], model["revision"], model["provider"])


def _model_identity_label(key: tuple[str, str, str]) -> str:
    return f"{key[0]}@{key[1]}#{key[2]}"


def compare_probe_reports(root: Path, reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ProbeError("at least one report is required")
    for report in reports:
        if _base._schema_errors(root, PROBE_REPORT_SCHEMA, report):
            raise ProbeError("invalid report supplied for comparison")
        if report.get("execution_kind") == "scoring_oracle":
            raise ProbeError("scoring-oracle reports cannot be used as empirical comparisons")

    bundle_ids = {report["probe_bundle_sha256"] for report in reports}
    substrate_ids = {
        tuple(sorted(report["substrate"].items()))
        for report in reports
    }
    if len(bundle_ids) != 1 or len(substrate_ids) != 1:
        raise ProbeError("comparison requires identical probe bundle and substrate identity")

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    seen_conditions: set[tuple[tuple[str, str, str], str]] = set()
    for report in reports:
        key = _model_identity_key(report)
        pair = (key, report["condition"])
        if pair in seen_conditions:
            raise ProbeError("comparison contains duplicate model-identity/condition report")
        seen_conditions.add(pair)
        grouped.setdefault(key, []).append(report)

    rows: list[dict[str, Any]] = []
    for key, model_reports in sorted(grouped.items()):
        baseline = next((report for report in model_reports if report["condition"] == "naked"), None)
        for report in sorted(model_reports, key=lambda item: CONDITION_IDS.index(item["condition"])):
            row = {
                "model_id": key[0],
                "model_revision": key[1],
                "model_provider": key[2],
                "condition": report["condition"],
                "overall_accuracy": report["metrics"]["overall_accuracy"],
                "hallucination_rate": report["metrics"]["hallucination_rate"],
                "yeah_nah_1_accuracy": report["yeah_nah_1"]["overall_accuracy"],
                "context_token_efficiency": report["metrics"]["context_token_efficiency"],
                "substrate_uplift_over_naked": None,
                "hallucination_reduction_relative_to_naked": None,
                "cultural_context_uplift_over_naked": None,
            }
            if baseline is not None:
                base_acc = baseline["metrics"]["overall_accuracy"]
                base_hall = baseline["metrics"]["hallucination_rate"]
                base_yn = baseline["yeah_nah_1"]["overall_accuracy"]
                if base_acc is not None and row["overall_accuracy"] is not None:
                    row["substrate_uplift_over_naked"] = round(row["overall_accuracy"] - base_acc, 6)
                if base_hall is not None and row["hallucination_rate"] is not None:
                    row["hallucination_reduction_relative_to_naked"] = round(
                        base_hall - row["hallucination_rate"], 6
                    )
                if base_yn is not None and row["yeah_nah_1_accuracy"] is not None:
                    row["cultural_context_uplift_over_naked"] = round(
                        row["yeah_nah_1_accuracy"] - base_yn, 6
                    )
            rows.append(row)

    comparison = {
        "type": "qsol-probe-comparison",
        "schema_version": "1.0.0",
        "probe_spec_version": PROBE_SPEC_VERSION,
        "probe_bundle_sha256": next(iter(bundle_ids)),
        "substrate": reports[0]["substrate"],
        "models": [_model_identity_label(key) for key in sorted(grouped)],
        "conditions": list(CONDITION_IDS),
        "rows": rows,
        "research_question": "How much substrate is enough?",
        "interpretation": (
            "Uplift is measured only against the same model ID, revision, and provider naked baseline. "
            "Missing exact-identity baselines produce null uplift fields."
        ),
    }
    errors = _base._schema_errors(root, PROBE_COMPARISON_SCHEMA, comparison)
    if errors:
        raise ProbeError("generated comparison schema violation at: " + ", ".join(errors[:8]))
    return comparison


def comparison_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# QSOL-SUBSTRATE Probe Comparison",
        "",
        "| Model | Revision | Provider | Condition | Accuracy | Uplift | Hallucination reduction | YEAH-NAH/1 uplift |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in comparison["rows"]:
        lines.append(
            f"| {row['model_id']} | {row['model_revision']} | {row['model_provider']} | {row['condition']} | "
            f"{row['overall_accuracy']} | {row['substrate_uplift_over_naked']} | "
            f"{row['hallucination_reduction_relative_to_naked']} | "
            f"{row['cultural_context_uplift_over_naked']} |"
        )
    lines.extend(["", "**Research question:** How much substrate is enough?", ""])
    return "\n".join(lines)


# The base implementation is retained byte-for-byte so existing helpers and
# deterministic serialization remain stable. Patch only the trust-boundary
# entry points/global helpers that must observe the hardened semantics.
_base.build_probe_bundle = build_probe_bundle
_base.validate_probe_bundle = validate_probe_bundle
_base._expected_field_matches = _expected_field_matches
_base._case_correct = _case_correct
_base.score_probe_run = score_probe_run
_base.compare_probe_reports = compare_probe_reports
_base.comparison_markdown = comparison_markdown
