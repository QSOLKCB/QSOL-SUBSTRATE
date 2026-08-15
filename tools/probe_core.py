from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import canonical_json_bytes
from toolless_core import _identity

PROBE_SPEC_VERSION = "1.0.0"
PROBE_MANIFEST_SCHEMA = "schema/probe-manifest.schema.json"
MODEL_RUN_SCHEMA = "schema/model-run.schema.json"
PROBE_REPORT_SCHEMA = "schema/probe-report.schema.json"
PROBE_COMPARISON_SCHEMA = "schema/probe-comparison.schema.json"
SOURCE_DIR = "probe"
EXPECTED_FILES = {
    "substrate-probe.jsonl",
    "yeah-nah-1.jsonl",
    "conditions.json",
    "scoring-contract.json",
    "manifest.json",
}
CONDITION_IDS = (
    "naked",
    "micro",
    "standard",
    "full",
    "vector",
    "latent-prefix",
    "hybrid",
    "tool-enabled",
)
EPISTEMIC_STATES = {"known", "retrieved", "inferred", "unknown", "conflict", "fiction"}
YN_CLASSIFICATIONS = {
    "literal",
    "sarcastic",
    "deadpan",
    "understatement",
    "banter",
    "mock_hostility",
    "affectionate_insult",
    "polarity_reversal",
    "self_deprecation",
    "uncertain",
}
SARCASM_VALUES = {"yes", "no", "uncertain"}
HOSTILITY_VALUES = {"none", "mock", "actual", "uncertain"}
POLARITY_VALUES = {"positive", "negative", "neutral", "uncertain"}
SEVERITY_VALUES = {"low", "moderate", "high", "critical", "unknown"}

SCORING_CONTRACT: dict[str, Any] = {
    "type": "qsol-probe-scoring-contract",
    "schema_version": "1.0.0",
    "probe_spec_version": PROBE_SPEC_VERSION,
    "response_contract": {
        "structured_fields": [
            "probe_id",
            "raw_answer",
            "epistemic_state",
            "answer",
            "canonical_ids",
            "provenance_refs",
            "classification",
            "sarcasm",
            "hostility",
            "intent_polarity",
            "severity",
            "confidence",
            "freshness_limited",
        ],
        "free_form_prose_is_audit_material_not_the_primary_score_source": True,
        "missing_structured_fields_fail_closed": True,
    },
    "general_metrics": [
        "overall_accuracy",
        "factual_accuracy",
        "unsupported_assertion_rate",
        "unknown_precision",
        "unknown_recall",
        "alias_resolution_accuracy",
        "provenance_fidelity",
        "contradiction_handling",
        "claim_boundary_preservation",
        "context_token_efficiency",
        "substrate_uplift_over_naked",
        "hallucination_reduction_relative_to_naked",
    ],
    "yeah_nah_1_metrics": [
        "overall_accuracy",
        "sarcasm_precision",
        "sarcasm_recall",
        "literal_meaning_error_rate",
        "banter_misclassification_rate",
        "hostility_false_positive_rate",
        "understatement_severity_preservation_rate",
        "confidence_brier",
        "cultural_context_uplift_over_naked",
    ],
    "principles": [
        "UNKNOWN != FALSE",
        "INFERENCE != FACT",
        "SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED",
        "UNCERTAIN != SARCASTIC",
        "BANTER != HOSTILITY",
        "UNDERSTATEMENT != LOW_SEVERITY",
        "CONTEXT > TOKEN_POLARITY",
    ],
}


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProbeFinding:
    code: str
    path: str
    message: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"cannot load JSON {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProbeError(f"cannot read JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProbeError(f"invalid JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ProbeError(f"JSONL row {path}:{line_no} must be an object")
        rows.append(row)
    return rows


def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def _normalise_answer(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().casefold().split())
    return value


def _safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise ProbeError("refusing to replace symlinked probe output")
    output = output.resolve()
    if output == root or output in root.parents:
        raise ProbeError("probe output may not replace or contain repository root")
    if root in output.parents and output != root / "dist" / "probes":
        raise ProbeError("in-repository probe output is restricted to dist/probes")
    if output.exists() and not output.is_dir():
        raise ProbeError("refusing to replace non-directory probe output")
    return root, output


def _validate_expected(expected: dict[str, Any], suite: str, path: str) -> None:
    state = expected.get("epistemic_state")
    if state not in EPISTEMIC_STATES:
        raise ProbeError(f"{path}: invalid expected epistemic_state")
    if "canonical_ids" in expected:
        ids = expected["canonical_ids"]
        if not isinstance(ids, list) or any(not isinstance(item, str) or not item for item in ids):
            raise ProbeError(f"{path}: canonical_ids must be nonempty strings")
    if "provenance_refs" in expected:
        refs = expected["provenance_refs"]
        if not isinstance(refs, list) or any(not isinstance(item, str) or not item for item in refs):
            raise ProbeError(f"{path}: provenance_refs must be nonempty strings")
    if "freshness_limited" in expected and not isinstance(expected["freshness_limited"], bool):
        raise ProbeError(f"{path}: freshness_limited must be boolean")
    if suite == "yeah-nah-1":
        if expected.get("classification") not in YN_CLASSIFICATIONS:
            raise ProbeError(f"{path}: invalid YEAH-NAH/1 classification")
        if expected.get("sarcasm") not in SARCASM_VALUES:
            raise ProbeError(f"{path}: invalid sarcasm value")
        if expected.get("hostility") not in HOSTILITY_VALUES:
            raise ProbeError(f"{path}: invalid hostility value")
        if expected.get("intent_polarity") not in POLARITY_VALUES:
            raise ProbeError(f"{path}: invalid intent polarity")
        if expected.get("severity") not in SEVERITY_VALUES:
            raise ProbeError(f"{path}: invalid severity")


def load_probe_sources(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    general = _load_jsonl(root / SOURCE_DIR / "substrate-probe.jsonl")
    yeah_nah = _load_jsonl(root / SOURCE_DIR / "yeah-nah-1.jsonl")
    conditions = _load_json(root / SOURCE_DIR / "conditions.json")
    all_ids: set[str] = set()

    for expected_suite, rows in (("substrate", general), ("yeah-nah-1", yeah_nah)):
        for index, row in enumerate(rows):
            path = f"{expected_suite}[{index}]"
            if row.get("suite") != expected_suite:
                raise ProbeError(f"{path}: suite mismatch")
            item_id = row.get("id")
            if not isinstance(item_id, str) or not item_id:
                raise ProbeError(f"{path}: missing id")
            if item_id in all_ids:
                raise ProbeError(f"duplicate probe id: {item_id}")
            all_ids.add(item_id)
            if not isinstance(row.get("category"), str) or not row["category"]:
                raise ProbeError(f"{path}: missing category")
            if not isinstance(row.get("prompt"), str) or not row["prompt"].strip():
                raise ProbeError(f"{path}: missing prompt")
            if not isinstance(row.get("tags"), list):
                raise ProbeError(f"{path}: tags must be an array")
            expected = row.get("expected")
            if not isinstance(expected, dict):
                raise ProbeError(f"{path}: expected must be an object")
            _validate_expected(expected, expected_suite, path)

    if conditions.get("type") != "qsol-probe-condition-matrix":
        raise ProbeError("conditions.json: wrong type")
    items = conditions.get("conditions")
    if not isinstance(items, list):
        raise ProbeError("conditions.json: conditions must be an array")
    ids = [item.get("id") for item in items if isinstance(item, dict)]
    if tuple(ids) != CONDITION_IDS:
        raise ProbeError("conditions.json: condition order/identity does not match Phase 7 contract")
    if conditions.get("comparison_baseline") != "naked":
        raise ProbeError("conditions.json: naked must remain the comparison baseline")
    return general, yeah_nah, conditions


def _category_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        category = str(row["category"])
        result[category] = result.get(category, 0) + 1
    return dict(sorted(result.items()))


def build_probe_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _safe_output(root, output)
    identity, _ = _identity(root, source_commit)
    general, yeah_nah, conditions = load_probe_sources(root)

    files = {
        "substrate-probe.jsonl": _jsonl_bytes(general),
        "yeah-nah-1.jsonl": _jsonl_bytes(yeah_nah),
        "conditions.json": canonical_json_bytes(conditions),
        "scoring-contract.json": canonical_json_bytes(SCORING_CONTRACT),
    }
    file_rows = [
        {"path": path, "sha256": _sha256(data), "bytes": len(data)}
        for path, data in sorted(files.items())
    ]
    material = "".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n" for row in file_rows
    ).encode("utf-8")
    all_rows = general + yeah_nah
    manifest = {
        "type": "qsol-substrate-probe-manifest",
        "schema_version": "1.0.0",
        "probe_spec_version": PROBE_SPEC_VERSION,
        "substrate": identity,
        "artifact_class": "deterministic_evaluation_protocol",
        "empirical_model_results_in_ci": False,
        "scoring_oracle_is_empirical_result": False,
        "conditions": list(CONDITION_IDS),
        "probe_count": len(all_rows),
        "suite_counts": {
            "substrate": len(general),
            "yeah-nah-1": len(yeah_nah),
        },
        "category_counts": _category_counts(all_rows),
        "files": file_rows,
        "bundle_sha256": _sha256(material),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir: Path | None = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        for path, data in files.items():
            (temp_dir / path).write_bytes(data)
        (temp_dir / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        if output.exists():
            shutil.rmtree(output)
        temp_dir.replace(output)
        temp_dir = None
        return manifest
    finally:
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _schema_errors(root: Path, schema_path: str, value: Any) -> list[str]:
    schema = _load_json(root / schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        "/".join(str(part) for part in error.absolute_path) or "$"
        for error in validator.iter_errors(value)
    ]


def validate_probe_bundle(root: Path, bundle: Path, schema_path: str = PROBE_MANIFEST_SCHEMA) -> list[ProbeFinding]:
    root = root.resolve()
    if bundle.is_symlink():
        return [ProbeFinding("probe.bundle", str(bundle), "bundle may not be a symlink")]
    bundle = bundle.resolve()
    findings: list[ProbeFinding] = []
    if not bundle.is_dir():
        return [ProbeFinding("probe.bundle", str(bundle), "bundle must be a real directory")]

    try:
        manifest = _load_json(bundle / "manifest.json")
    except ProbeError as exc:
        return [ProbeFinding("probe.manifest", "manifest.json", str(exc))]
    if not isinstance(manifest, dict):
        return [ProbeFinding("probe.manifest", "manifest.json", "manifest must be an object")]

    try:
        for pointer in _schema_errors(root, schema_path, manifest):
            findings.append(ProbeFinding("probe.schema", f"manifest.json/{pointer}", "probe manifest schema violation"))
    except Exception as exc:
        return [ProbeFinding("probe.schema_definition", schema_path, str(exc))]

    actual_names: set[str] = set()
    try:
        for child in bundle.iterdir():
            if child.is_symlink():
                findings.append(ProbeFinding("probe.symlink", child.name, "bundle entries may not be symlinks"))
                continue
            if not child.is_file():
                findings.append(ProbeFinding("probe.extra_entry", child.name, "bundle entries must be regular files"))
                continue
            actual_names.add(child.name)
    except OSError as exc:
        return findings + [ProbeFinding("probe.bundle_read", str(bundle), str(exc))]
    if actual_names != EXPECTED_FILES:
        findings.append(ProbeFinding("probe.file_set", str(bundle), "bundle file set must match deterministic Phase 7 layout"))

    substrate = manifest.get("substrate", {})
    source_commit = substrate.get("source_commit") if isinstance(substrate, dict) else None
    if not isinstance(source_commit, str):
        findings.append(ProbeFinding("probe.source_commit", "manifest.json/substrate/source_commit", "missing source commit"))
        return findings

    with tempfile.TemporaryDirectory() as temp:
        expected_dir = Path(temp) / "probes"
        try:
            expected_manifest = build_probe_bundle(root, expected_dir, source_commit)
        except Exception as exc:
            findings.append(ProbeFinding("probe.recompile", "probe_sources", str(exc)))
            return findings
        for name in sorted(EXPECTED_FILES):
            actual_path = bundle / name
            expected_path = expected_dir / name
            if not actual_path.is_file() or actual_path.is_symlink():
                continue
            try:
                if actual_path.read_bytes() != expected_path.read_bytes():
                    findings.append(ProbeFinding("probe.deterministic_mismatch", name, "file differs from deterministic rebuild"))
            except OSError as exc:
                findings.append(ProbeFinding("probe.file_read", name, str(exc)))
        if manifest != expected_manifest:
            findings.append(ProbeFinding("probe.manifest_mismatch", "manifest.json", "manifest differs from deterministic rebuild"))
    return findings


def load_built_cases(bundle: Path) -> list[dict[str, Any]]:
    return _load_jsonl(bundle / "substrate-probe.jsonl") + _load_jsonl(bundle / "yeah-nah-1.jsonl")


def _response_defaults(probe_id: str) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "raw_answer": "",
        "epistemic_state": "unknown",
        "answer": None,
        "canonical_ids": [],
        "provenance_refs": [],
        "classification": None,
        "sarcasm": None,
        "hostility": None,
        "intent_polarity": None,
        "severity": None,
        "confidence": 0.0,
        "freshness_limited": None,
    }


def build_scoring_oracle_run(bundle: Path, condition: str = "naked") -> dict[str, Any]:
    manifest = _load_json(bundle / "manifest.json")
    if condition not in CONDITION_IDS:
        raise ProbeError(f"unknown condition: {condition}")
    responses: list[dict[str, Any]] = []
    for case in load_built_cases(bundle):
        response = _response_defaults(case["id"])
        expected = case["expected"]
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
        ):
            if field in expected:
                response[field] = expected[field]
        response["raw_answer"] = f"SCORING ORACLE ONLY: {case['id']}"
        response["confidence"] = 1.0
        responses.append(response)
    return {
        "type": "qsol-probe-model-run",
        "schema_version": "1.0.0",
        "run_id": f"scoring-oracle:{condition}",
        "execution_kind": "scoring_oracle",
        "model": {
            "id": "qsol/scoring-oracle",
            "revision": PROBE_SPEC_VERSION,
            "provider": "QSOL-SUBSTRATE",
        },
        "condition": condition,
        "probe_bundle_sha256": manifest["bundle_sha256"],
        "substrate": manifest["substrate"],
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "tokenizer": "not_applicable",
        },
        "responses": responses,
    }


def _expected_field_matches(expected: dict[str, Any], response: dict[str, Any], field: str) -> bool:
    if field not in expected:
        return True
    wanted = expected[field]
    actual = response.get(field)
    if field == "answer":
        return _normalise_answer(actual) == _normalise_answer(wanted)
    if field in {"canonical_ids", "provenance_refs"}:
        if not isinstance(actual, list):
            return False
        return set(wanted).issubset(set(actual))
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


def _rate(numerator: int | float, denominator: int | float) -> float | None:
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 6)


def _validate_run_shape(root: Path, run: dict[str, Any]) -> None:
    errors = _schema_errors(root, MODEL_RUN_SCHEMA, run)
    if errors:
        raise ProbeError("model run schema violation at: " + ", ".join(errors[:8]))


def score_probe_run(root: Path, bundle: Path, run: dict[str, Any]) -> dict[str, Any]:
    manifest = _load_json(bundle / "manifest.json")
    if run.get("probe_bundle_sha256") != manifest.get("bundle_sha256"):
        raise ProbeError("model run is bound to a different probe bundle")
    if run.get("substrate") != manifest.get("substrate"):
        raise ProbeError("model run substrate identity does not match probe bundle")
    _validate_run_shape(root, run)

    cases = load_built_cases(bundle)
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
        correct = _case_correct(case, response)
        scored.append({
            "probe_id": case["id"],
            "suite": case["suite"],
            "category": case["category"],
            "correct": correct,
            "expected_epistemic_state": case["expected"]["epistemic_state"],
            "actual_epistemic_state": response["epistemic_state"],
            "confidence": response["confidence"],
        })

    total = len(scored)
    correct_count = sum(1 for item in scored if item["correct"])
    substrate_scored = [item for item in scored if item["suite"] == "substrate"]
    yn_scored = [item for item in scored if item["suite"] == "yeah-nah-1"]

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
        if "provenance_refs" in case_by_id[item["probe_id"]]["expected"]
    ]
    response_by_id = {response["probe_id"]: response for response in responses}
    provenance_hits = sum(
        int(set(case["expected"]["provenance_refs"]).issubset(set(response_by_id[case["id"]]["provenance_refs"])))
        for case in provenance_cases
    )

    substrate_ids = {case["id"] for case in cases if case["suite"] == "substrate"}
    expected_unknown_ids = {
        case["id"] for case in cases
        if case["suite"] == "substrate" and case["expected"]["epistemic_state"] == "unknown"
    }
    predicted_unknown_ids = {
        response["probe_id"] for response in responses
        if response["probe_id"] in substrate_ids and response["epistemic_state"] == "unknown"
    }
    unknown_tp = len(expected_unknown_ids & predicted_unknown_ids)
    unsupported_assertions = len(expected_unknown_ids - predicted_unknown_ids)

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

    brier_values = []
    for item in yn_scored:
        p = float(item["confidence"])
        outcome = 1.0 if item["correct"] else 0.0
        brier_values.append((p - outcome) ** 2)
    brier = round(sum(brier_values) / len(brier_values), 6) if brier_values else None

    input_tokens = int(run["usage"]["input_tokens"])
    token_eff = None
    if input_tokens > 0:
        token_eff = round(correct_count / (input_tokens / 1000.0), 6)

    metrics = {
        "overall_accuracy": _rate(correct_count, total),
        "factual_accuracy": _rate(sum(item["correct"] for item in factual), len(factual)),
        "unsupported_assertion_rate": _rate(unsupported_assertions, len(expected_unknown_ids)),
        "unknown_precision": _rate(unknown_tp, len(predicted_unknown_ids)),
        "unknown_recall": _rate(unknown_tp, len(expected_unknown_ids)),
        "alias_resolution_accuracy": _rate(sum(item["correct"] for item in aliases), len(aliases)),
        "provenance_fidelity": _rate(provenance_hits, len(provenance_cases)),
        "contradiction_handling": _rate(sum(item["correct"] for item in contradictions), len(contradictions)),
        "claim_boundary_preservation": _rate(sum(item["correct"] for item in boundaries), len(boundaries)),
        "context_token_efficiency": token_eff,
        "hallucination_rate": _rate(unsupported_assertions, len(expected_unknown_ids)),
    }
    yn_metrics = {
        "overall_accuracy": _rate(sum(item["correct"] for item in yn_scored), len(yn_scored)),
        "sarcasm_precision": _rate(sarcasm_tp, len(sarcasm_predicted_yes)),
        "sarcasm_recall": _rate(sarcasm_tp, len(sarcasm_expected_yes)),
        "literal_meaning_error_rate": _rate(literal_trap_errors, len(literal_traps)),
        "banter_misclassification_rate": _rate(banter_errors, len(banter_cases)),
        "hostility_false_positive_rate": _rate(hostility_fp, len(non_actual_hostility)),
        "understatement_severity_preservation_rate": _rate(understatement_preserved, len(understatement_cases)),
        "confidence_brier": brier,
    }

    category_metrics: dict[str, float | None] = {}
    categories = sorted({item["category"] for item in scored})
    for category in categories:
        bucket = [item for item in scored if item["category"] == category]
        category_metrics[category] = _rate(sum(item["correct"] for item in bucket), len(bucket))

    report = {
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
        "interpretation": "Scores structured model outputs against deterministic probe ground truth. A scoring-oracle run validates the scorer only and is not an empirical model result.",
    }
    errors = _schema_errors(root, PROBE_REPORT_SCHEMA, report)
    if errors:
        raise ProbeError("generated probe report schema violation at: " + ", ".join(errors[:8]))
    return report


def compare_probe_reports(root: Path, reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ProbeError("at least one report is required")
    for report in reports:
        errors = _schema_errors(root, PROBE_REPORT_SCHEMA, report)
        if errors:
            raise ProbeError("invalid report supplied for comparison")
        if report.get("execution_kind") == "scoring_oracle":
            raise ProbeError("scoring-oracle reports cannot be used as empirical comparisons")

    bundle_ids = {report["probe_bundle_sha256"] for report in reports}
    substrate_ids = {
        (report["substrate"]["source_commit"], report["substrate"]["substrate_sha256"])
        for report in reports
    }
    if len(bundle_ids) != 1 or len(substrate_ids) != 1:
        raise ProbeError("comparison requires identical probe bundle and substrate identity")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for report in reports:
        grouped.setdefault(report["model"]["id"], []).append(report)

    rows: list[dict[str, Any]] = []
    for model_id, model_reports in sorted(grouped.items()):
        baseline = next((report for report in model_reports if report["condition"] == "naked"), None)
        for report in sorted(model_reports, key=lambda item: CONDITION_IDS.index(item["condition"])):
            row = {
                "model_id": model_id,
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
                    row["hallucination_reduction_relative_to_naked"] = round(base_hall - row["hallucination_rate"], 6)
                if base_yn is not None and row["yeah_nah_1_accuracy"] is not None:
                    row["cultural_context_uplift_over_naked"] = round(row["yeah_nah_1_accuracy"] - base_yn, 6)
            rows.append(row)

    comparison = {
        "type": "qsol-probe-comparison",
        "schema_version": "1.0.0",
        "probe_spec_version": PROBE_SPEC_VERSION,
        "probe_bundle_sha256": next(iter(bundle_ids)),
        "substrate": reports[0]["substrate"],
        "models": sorted(grouped),
        "conditions": list(CONDITION_IDS),
        "rows": rows,
        "research_question": "How much substrate is enough?",
        "interpretation": "Uplift is measured against the same model's naked baseline. Missing baselines produce null uplift fields.",
    }
    errors = _schema_errors(root, PROBE_COMPARISON_SCHEMA, comparison)
    if errors:
        raise ProbeError("generated comparison schema violation at: " + ", ".join(errors[:8]))
    return comparison


def report_markdown(report: dict[str, Any]) -> str:
    m = report["metrics"]
    y = report["yeah_nah_1"]
    lines = [
        f"# QSOL-SUBSTRATE Probe Report — {report['model']['id']} / {report['condition']}",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Execution kind: `{report['execution_kind']}`",
        f"- Probe bundle: `{report['probe_bundle_sha256']}`",
        f"- Correct: `{report['counts']['correct']}/{report['counts']['total']}`",
        f"- Overall accuracy: `{m['overall_accuracy']}`",
        f"- Factual accuracy: `{m['factual_accuracy']}`",
        f"- Unsupported assertion rate: `{m['unsupported_assertion_rate']}`",
        f"- UNKNOWN precision / recall: `{m['unknown_precision']}` / `{m['unknown_recall']}`",
        f"- Provenance fidelity: `{m['provenance_fidelity']}`",
        f"- Claim-boundary preservation: `{m['claim_boundary_preservation']}`",
        f"- YEAH-NAH/1 accuracy: `{y['overall_accuracy']}`",
        f"- Sarcasm precision / recall: `{y['sarcasm_precision']}` / `{y['sarcasm_recall']}`",
        f"- Hostility false-positive rate: `{y['hostility_false_positive_rate']}`",
        f"- Confidence Brier: `{y['confidence_brier']}`",
        "",
        "> A scoring-oracle report validates the scorer. It is not an empirical model benchmark.",
        "",
    ]
    return "\n".join(lines)


def comparison_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# QSOL-SUBSTRATE Probe Comparison",
        "",
        "| Model | Condition | Accuracy | Uplift | Hallucination reduction | YEAH-NAH/1 uplift |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in comparison["rows"]:
        lines.append(
            f"| {row['model_id']} | {row['condition']} | {row['overall_accuracy']} | "
            f"{row['substrate_uplift_over_naked']} | {row['hallucination_reduction_relative_to_naked']} | "
            f"{row['cultural_context_uplift_over_naked']} |"
        )
    lines.extend(["", "**Research question:** How much substrate is enough?", ""])
    return "\n".join(lines)
