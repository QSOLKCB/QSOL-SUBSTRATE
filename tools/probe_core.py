from __future__ import annotations

from pathlib import Path
from typing import Any

import probe_core_hardening as _hard
from probe_core_hardening import *  # noqa: F401,F403

_ORIGINAL_HARDENED_SCORE = _hard.score_probe_run


def _has_unsupported_assertion(response: dict[str, Any], expected: dict[str, Any]) -> bool:
    if response.get("epistemic_state") not in {"unknown", "conflict"}:
        return True
    if expected.get("answer") is None and response.get("answer") is not None:
        return True
    expected_ids = set(expected.get("canonical_ids", []))
    actual_ids = set(response.get("canonical_ids", []))
    if actual_ids - expected_ids:
        return True
    expected_refs = set(expected.get("provenance_refs", []))
    actual_refs = set(response.get("provenance_refs", []))
    if actual_refs - expected_refs:
        return True
    return False


def _clean_predicted_unknown(response: dict[str, Any], expected: dict[str, Any]) -> bool:
    return response.get("epistemic_state") == "unknown" and not _has_unsupported_assertion(response, expected)


def score_probe_run(root: Path, bundle: Path, run: dict[str, Any]) -> dict[str, Any]:
    report = _ORIGINAL_HARDENED_SCORE(root, bundle, run)
    cases = _hard._base.load_built_cases(bundle)
    case_by_id = {case["id"]: case for case in cases}
    response_by_id = {response["probe_id"]: response for response in run["responses"]}
    substrate_ids = {case["id"] for case in cases if case["suite"] == "substrate"}
    expected_unknown_ids = {
        case["id"] for case in cases
        if case["suite"] == "substrate" and case["expected"]["epistemic_state"] == "unknown"
    }
    predicted_unknown_ids = {
        probe_id for probe_id in substrate_ids
        if _clean_predicted_unknown(response_by_id[probe_id], case_by_id[probe_id]["expected"])
    }
    unknown_tp = len(expected_unknown_ids & predicted_unknown_ids)
    unsupported_assertions = sum(
        int(_has_unsupported_assertion(response_by_id[probe_id], case_by_id[probe_id]["expected"]))
        for probe_id in expected_unknown_ids
    )
    report["metrics"]["unsupported_assertion_rate"] = _hard._base._rate(
        unsupported_assertions, len(expected_unknown_ids)
    )
    report["metrics"]["hallucination_rate"] = _hard._base._rate(
        unsupported_assertions, len(expected_unknown_ids)
    )
    report["metrics"]["unknown_precision"] = _hard._base._rate(
        unknown_tp, len(predicted_unknown_ids)
    )
    report["metrics"]["unknown_recall"] = _hard._base._rate(
        unknown_tp, len(expected_unknown_ids)
    )
    errors = _hard._base._schema_errors(root, PROBE_REPORT_SCHEMA, report)
    if errors:
        raise ProbeError("generated probe report schema violation at: " + ", ".join(errors[:8]))
    return report


_hard.score_probe_run = score_probe_run
