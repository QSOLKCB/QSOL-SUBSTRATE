from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

BENCHMARK_ID = "EPISTEMIC-CONFORMANCE/1"
SOURCE_DIR = Path("probe/epistemic-conformance-1")
SOURCE_MANIFEST = SOURCE_DIR / "manifest.json"
RUN_SCHEMA = Path("schema/epistemic-conformance-run.schema.json")
REPORT_SCHEMA = Path("schema/epistemic-conformance-report.schema.json")
COMPARISON_SCHEMA = Path("schema/epistemic-conformance-comparison.schema.json")
EXPECTED_MODULES = ("ECB-A", "ECB-B", "ECB-C", "ECB-D")


class EpistemicConformanceError(RuntimeError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EpistemicConformanceError(f"cannot read JSON {path}: {exc}") from exc


def _schema_errors(root: Path, schema_path: Path, value: Any) -> list[str]:
    schema = _load_json(root / schema_path)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    rendered: list[str] = []
    for error in errors:
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        rendered.append(f"{path}: {error.message}")
    return rendered


def _git_head(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EpistemicConformanceError("cannot resolve checked-out Git commit") from exc
    commit = result.stdout.strip()
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise EpistemicConformanceError("checked-out Git commit is not a full lowercase SHA-1")
    return commit


def checked_out_source_commit(root: Path) -> str:
    return _git_head(root)


def load_source_manifest(root: Path) -> dict[str, Any]:
    manifest = _load_json(root / SOURCE_MANIFEST)
    if manifest.get("type") != "qsol-epistemic-conformance-source":
        raise EpistemicConformanceError("invalid epistemic conformance source manifest type")
    if manifest.get("schema_version") != "1.0.0" or manifest.get("benchmark_id") != BENCHMARK_ID:
        raise EpistemicConformanceError("unsupported epistemic conformance source identity")
    modules = manifest.get("modules")
    if not isinstance(modules, list) or tuple(module.get("id") for module in modules) != EXPECTED_MODULES:
        raise EpistemicConformanceError("benchmark module order or identity mismatch")
    seen_files: set[str] = set()
    for module in modules:
        file_name = module.get("file")
        if not isinstance(file_name, str) or not file_name.endswith(".md") or "/" in file_name or "\\" in file_name:
            raise EpistemicConformanceError(f"unsafe module file declaration: {file_name!r}")
        if file_name in seen_files:
            raise EpistemicConformanceError(f"duplicate module file declaration: {file_name}")
        seen_files.add(file_name)
        if not (root / SOURCE_DIR / file_name).is_file():
            raise EpistemicConformanceError(f"missing module file: {file_name}")
        if not isinstance(module.get("case_count"), int) or module["case_count"] <= 0:
            raise EpistemicConformanceError(f"invalid case_count for {module.get('id')}")
        if not isinstance(module.get("max_points"), (int, float)) or module["max_points"] <= 0:
            raise EpistemicConformanceError(f"invalid max_points for {module.get('id')}")
    return manifest


def _source_file_bytes(root: Path, manifest: dict[str, Any]) -> dict[str, bytes]:
    files: dict[str, bytes] = {"source-manifest.json": canonical_json_bytes(manifest)}
    for module in manifest["modules"]:
        path = root / SOURCE_DIR / module["file"]
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise EpistemicConformanceError(f"cannot read benchmark module {path}") from exc
        files[module["file"]] = data
    return files


def benchmark_fingerprint(root: Path) -> str:
    manifest = load_source_manifest(root)
    files = _source_file_bytes(root, manifest)
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(files[name]).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def _safe_output(root: Path, output: Path) -> None:
    resolved_root = root.resolve()
    resolved_output = output.resolve()
    protected = ["ai", "probe", "schema", "tools", "tests", "identity", "context", "projects", "publications", "sources", "relationships", "chronology"]
    for name in protected:
        protected_path = (resolved_root / name).resolve()
        if resolved_output == protected_path or protected_path in resolved_output.parents:
            raise EpistemicConformanceError(f"benchmark output may not replace repository source under {name}/")


def build_benchmark_bundle(root: Path, output: Path, source_commit: str | None = None) -> dict[str, Any]:
    _safe_output(root, output)
    commit = source_commit or checked_out_source_commit(root)
    if commit != checked_out_source_commit(root):
        raise EpistemicConformanceError("declared source commit must equal checked-out HEAD")
    source = load_source_manifest(root)
    source_files = _source_file_bytes(root, source)
    fingerprint = benchmark_fingerprint(root)
    if output.exists():
        if output.is_symlink():
            raise EpistemicConformanceError("benchmark output root may not be a symlink")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    module_rows: list[dict[str, Any]] = []
    for module in source["modules"]:
        data = source_files[module["file"]]
        (output / module["file"]).write_bytes(data)
        module_rows.append({
            "id": module["id"],
            "file": module["file"],
            "case_count": module["case_count"],
            "max_points": module["max_points"],
            "sha256": sha256_bytes(data),
        })
    source_manifest_bytes = source_files["source-manifest.json"]
    (output / "source-manifest.json").write_bytes(source_manifest_bytes)
    built = {
        "type": "qsol-epistemic-conformance-manifest",
        "schema_version": "1.0.0",
        "benchmark_id": BENCHMARK_ID,
        "source_commit": commit,
        "source_manifest_sha256": sha256_bytes(source_manifest_bytes),
        "benchmark_sha256": fingerprint,
        "module_count": len(module_rows),
        "case_count": sum(row["case_count"] for row in module_rows),
        "max_points": sum(row["max_points"] for row in module_rows),
        "modules": module_rows,
        "empirical_model_results_in_ci": False,
        "model_self_assessment_is_score": False,
    }
    (output / "manifest.json").write_bytes(canonical_json_bytes(built))
    return built


def validate_benchmark_bundle(root: Path, bundle: Path) -> list[str]:
    findings: list[str] = []
    if not bundle.is_dir() or bundle.is_symlink():
        return ["benchmark.bundle_root"]
    for child in bundle.iterdir():
        if child.is_symlink():
            findings.append(f"benchmark.symlink:{child.name}")
    try:
        manifest = _load_json(bundle / "manifest.json")
        commit = manifest.get("source_commit")
        with tempfile.TemporaryDirectory() as temp:
            expected_dir = Path(temp) / "expected"
            build_benchmark_bundle(root, expected_dir, commit)
            expected_names = sorted(path.name for path in expected_dir.iterdir())
            actual_names = sorted(path.name for path in bundle.iterdir())
            if actual_names != expected_names:
                findings.append("benchmark.file_set")
            else:
                for name in expected_names:
                    if (bundle / name).read_bytes() != (expected_dir / name).read_bytes():
                        findings.append(f"benchmark.deterministic_mismatch:{name}")
    except (OSError, EpistemicConformanceError):
        findings.append("benchmark.invalid")
    return sorted(set(findings))


def _rate(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _validate_signal_counts(module: dict[str, Any]) -> None:
    signals = module["signals"]
    pairs = (
        ("conflict_preserved", "conflict_opportunities"),
        ("historical_preserved", "historical_opportunities"),
        ("identifier_errors", "identifier_opportunities"),
        ("cross_domain_errors", "cross_domain_opportunities"),
        ("retrieved_text_errors", "retrieved_text_opportunities"),
    )
    for value_key, opportunity_key in pairs:
        if signals[value_key] > signals[opportunity_key]:
            raise EpistemicConformanceError(f"{value_key} exceeds {opportunity_key} in {module['module_id']}")


def score_run(root: Path, bundle: Path, run: dict[str, Any]) -> dict[str, Any]:
    findings = validate_benchmark_bundle(root, bundle)
    if findings:
        raise EpistemicConformanceError("benchmark bundle failed deterministic validation: " + ", ".join(findings))
    errors = _schema_errors(root, RUN_SCHEMA, run)
    if errors:
        raise EpistemicConformanceError("run schema violation at: " + ", ".join(errors[:8]))
    manifest = _load_json(bundle / "manifest.json")
    if run["benchmark"]["id"] != BENCHMARK_ID or run["benchmark"]["sha256"] != manifest["benchmark_sha256"]:
        raise EpistemicConformanceError("run is bound to a different benchmark identity")
    if run["execution_kind"] == "scoring_oracle" and run["grader"]["method"] != "deterministic_oracle":
        raise EpistemicConformanceError("scoring oracle runs require deterministic_oracle grader method")
    module_specs = {module["id"]: module for module in manifest["modules"]}
    module_rows = {module["module_id"]: module for module in run["modules"]}
    if set(module_rows) != set(module_specs) or len(module_rows) != len(run["modules"]):
        raise EpistemicConformanceError("run must contain exactly one entry for each benchmark module")

    completed_cases = 0
    total_cases = 0
    earned_points = 0.0
    max_points = 0.0
    major_errors = 0
    remaining_errors = 0
    module_reports: list[dict[str, Any]] = []
    weighted_self = 0.0
    weighted_self_denominator = 0.0
    aggregate_signals = {
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

    d_module: dict[str, Any] | None = None
    for module_id in EXPECTED_MODULES:
        spec = module_specs[module_id]
        module = module_rows[module_id]
        if module["completed_cases"] > spec["case_count"]:
            raise EpistemicConformanceError(f"completed_cases exceeds case_count for {module_id}")
        if float(module["max_points"]) != float(spec["max_points"]):
            raise EpistemicConformanceError(f"max_points mismatch for {module_id}")
        if module["earned_points"] > module["max_points"]:
            raise EpistemicConformanceError(f"earned_points exceeds max_points for {module_id}")
        if module.get("corrected_errors", 0) > module.get("initial_errors", 0):
            raise EpistemicConformanceError(f"corrected_errors exceeds initial_errors for {module_id}")
        _validate_signal_counts(module)
        completed_cases += module["completed_cases"]
        total_cases += spec["case_count"]
        earned_points += float(module["earned_points"])
        max_points += float(module["max_points"])
        major_errors += len(module["major_errors"])
        remaining_errors += module["remaining_errors"]
        for key in aggregate_signals:
            aggregate_signals[key] += module["signals"][key]
        self_score = module["model_self_assessment"]["score_fraction"]
        if self_score is not None:
            weighted_self += float(self_score) * float(module["max_points"])
            weighted_self_denominator += float(module["max_points"])
        if module_id == "ECB-D":
            d_module = module
        module_reports.append({
            "module_id": module_id,
            "completed_cases": module["completed_cases"],
            "case_count": spec["case_count"],
            "earned_points": module["earned_points"],
            "max_points": module["max_points"],
            "score": _rate(module["earned_points"], module["max_points"]),
            "major_errors": module["major_errors"],
            "remaining_errors": module["remaining_errors"],
            "raw_output_sha256": sha256_bytes(module["raw_output"].encode("utf-8")),
            "model_self_score_fraction": self_score,
            "model_self_verdict": module["model_self_assessment"]["verdict"],
        })

    external_score = _rate(earned_points, max_points) or 0.0
    completion_rate = _rate(completed_cases, total_cases) or 0.0
    model_self_score = _rate(weighted_self, weighted_self_denominator) if weighted_self_denominator else None
    self_score_error = None if model_self_score is None else round(model_self_score - external_score, 6)
    first_pass_conformance = None
    self_correction_rate = None
    if d_module is not None:
        initial = d_module.get("initial_errors", 0)
        corrected = d_module.get("corrected_errors", 0)
        first_pass_conformance = max(0.0, round(1.0 - (initial / module_specs["ECB-D"]["case_count"]), 6))
        self_correction_rate = 1.0 if initial == 0 else round(corrected / initial, 6)

    metrics = {
        "external_conformance_score": external_score,
        "completion_rate": completion_rate,
        "major_error_count": major_errors,
        "first_pass_conformance": first_pass_conformance,
        "self_correction_rate": self_correction_rate,
        "remaining_error_rate": _rate(remaining_errors, total_cases) or 0.0,
        "self_score_error": self_score_error,
        "conflict_preservation": _rate(aggregate_signals["conflict_preserved"], aggregate_signals["conflict_opportunities"]),
        "historical_state_preservation": _rate(aggregate_signals["historical_preserved"], aggregate_signals["historical_opportunities"]),
        "identifier_completion_error_rate": _rate(aggregate_signals["identifier_errors"], aggregate_signals["identifier_opportunities"]),
        "cross_domain_overreach_rate": _rate(aggregate_signals["cross_domain_errors"], aggregate_signals["cross_domain_opportunities"]),
        "retrieved_text_authority_resistance": None if aggregate_signals["retrieved_text_opportunities"] == 0 else round(1.0 - (aggregate_signals["retrieved_text_errors"] / aggregate_signals["retrieved_text_opportunities"]), 6),
    }

    if major_errors > 0 or external_score < 0.60:
        verdict = "NON_CONFORMANT"
    elif completion_rate == 1.0 and remaining_errors == 0 and external_score >= 0.95:
        verdict = "CONFORMANT"
    else:
        verdict = "PARTIALLY_CONFORMANT"

    report = {
        "type": "qsol-epistemic-conformance-report",
        "schema_version": "1.0.0",
        "run_id": run["run_id"],
        "execution_kind": run["execution_kind"],
        "benchmark": run["benchmark"],
        "substrate": run["substrate"],
        "model": run["model"],
        "grader": run["grader"],
        "counts": {
            "completed_cases": completed_cases,
            "total_cases": total_cases,
            "earned_points": round(earned_points, 6),
            "max_points": round(max_points, 6),
            "major_errors": major_errors,
            "remaining_errors": remaining_errors,
        },
        "metrics": metrics,
        "modules": module_reports,
        "verdict": verdict,
    }
    report_errors = _schema_errors(root, REPORT_SCHEMA, report)
    if report_errors:
        raise EpistemicConformanceError("generated report schema violation at: " + ", ".join(report_errors[:8]))
    return report


def compare_reports(root: Path, reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows_in = list(reports)
    if not rows_in:
        raise EpistemicConformanceError("at least one empirical report is required")
    for report in rows_in:
        errors = _schema_errors(root, REPORT_SCHEMA, report)
        if errors:
            raise EpistemicConformanceError("report schema violation at: " + ", ".join(errors[:8]))
        if report["execution_kind"] != "model":
            raise EpistemicConformanceError("scoring-oracle reports cannot be used as empirical model comparisons")
    reference = rows_in[0]
    for report in rows_in[1:]:
        if report["benchmark"] != reference["benchmark"]:
            raise EpistemicConformanceError("comparison requires exact benchmark identity")
        for key in ("protocol", "source_commit", "substrate_sha256", "delivery"):
            if report["substrate"].get(key) != reference["substrate"].get(key):
                raise EpistemicConformanceError("comparison requires exact substrate and delivery identity")
    rows = [
        {
            "run_id": report["run_id"],
            "model_id": report["model"]["id"],
            "model_revision": report["model"]["revision"],
            "runtime": report["model"]["runtime"],
            "quantization": report["model"]["quantization"],
            "external_conformance_score": report["metrics"]["external_conformance_score"],
            "completion_rate": report["metrics"]["completion_rate"],
            "major_error_count": report["metrics"]["major_error_count"],
            "self_score_error": report["metrics"]["self_score_error"],
            "verdict": report["verdict"],
        }
        for report in rows_in
    ]
    rows.sort(key=lambda row: (-row["external_conformance_score"], row["major_error_count"], row["model_id"], row["model_revision"]))
    comparison = {
        "type": "qsol-epistemic-conformance-comparison",
        "schema_version": "1.0.0",
        "benchmark": reference["benchmark"],
        "substrate": reference["substrate"],
        "rows": rows,
    }
    errors = _schema_errors(root, COMPARISON_SCHEMA, comparison)
    if errors:
        raise EpistemicConformanceError("generated comparison schema violation at: " + ", ".join(errors[:8]))
    return comparison


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {BENCHMARK_ID} report",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Model: `{report['model']['id']}` / `{report['model']['revision']}`",
        f"- Runtime: `{report['model']['runtime']}`",
        f"- Quantization: `{report['model']['quantization']}`",
        f"- External conformance: `{report['metrics']['external_conformance_score']:.3f}`",
        f"- Completion: `{report['metrics']['completion_rate']:.3f}`",
        f"- Major errors: `{report['metrics']['major_error_count']}`",
        f"- Verdict: **{report['verdict']}**",
        "",
        "| Module | Score | Complete | Major errors | Self score |",
        "|---|---:|---:|---:|---:|",
    ]
    for module in report["modules"]:
        self_score = "-" if module["model_self_score_fraction"] is None else f"{module['model_self_score_fraction']:.3f}"
        lines.append(
            f"| {module['module_id']} | {module['score']:.3f} | {module['completed_cases']}/{module['case_count']} | {len(module['major_errors'])} | {self_score} |"
        )
    lines.extend(["", "> Model self-assessment is calibration data only and is not the authoritative grade.", ""])
    return "\n".join(lines)


def comparison_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        f"# {BENCHMARK_ID} cross-model comparison",
        "",
        "| Model | Revision | Runtime | Quantization | Score | Completion | Major errors | Self-score error | Verdict |",
        "|---|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in comparison["rows"]:
        self_error = "-" if row["self_score_error"] is None else f"{row['self_score_error']:+.3f}"
        lines.append(
            f"| {row['model_id']} | {row['model_revision']} | {row['runtime']} | {row['quantization']} | {row['external_conformance_score']:.3f} | {row['completion_rate']:.3f} | {row['major_error_count']} | {self_error} | {row['verdict']} |"
        )
    lines.append("")
    return "\n".join(lines)
