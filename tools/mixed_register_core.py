from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import canonical_json_bytes
from toolless_core import _identity

MIXED_REGISTER_SPEC_VERSION = "1.0.0"
CLASSIFICATION_CONTRACT_VERSION = "MIXED-REGISTER/1"
MANIFEST_SCHEMA = "schema/mixed-register-manifest.schema.json"
AUDIT_SCHEMA = "schema/claim-audit.schema.json"
SOURCE_REPORT = "probe/mixed-register-1.md"
SOURCE_CLAIMS = "probe/mixed-register-1.jsonl"
SCORER_SOURCE = "tools/score_mixed_register.py"
EXPECTED_FILES = {
    "report.md",
    "claims.jsonl",
    "oracle.json",
    "scoring-contract.json",
    "scorer.py",
    "manifest.json",
}
PRIMARY_STATUSES = ("SUPPORTED", "CONTRADICTED", "UNAVAILABLE_UNVERIFIED")
REGISTER_VALUES = ("literal", "satire", "fictional_control")
EXECUTION_KINDS = ("empirical_consumer", "scoring_oracle", "non_empirical_analysis")
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

SCORING_CONTRACT: dict[str, Any] = {
    "type": "qsol-mixed-register-scoring-contract",
    "schema_version": "1.0.0",
    "classification_contract_version": CLASSIFICATION_CONTRACT_VERSION,
    "primary_epistemic_statuses": list(PRIMARY_STATUSES),
    "secondary_register_annotations": list(REGISTER_VALUES),
    "principles": [
        "UNKNOWN != FALSE",
        "INFERENCE != FACT",
        "SATIRE != BIOGRAPHY",
        "FORMALIZATION != PHYSICAL_TRUTH",
        "ADJACENT_TRUTH != INHERITED_TRUTH",
        "PRIMARY_EPISTEMIC_STATUS != REGISTER_ANNOTATION",
        "EACH_CLAIM_REQUIRES_CLAIM_LOCAL_EVIDENCE",
    ],
    "integrity_invariants": [
        "summary counts are mechanically derived from claims",
        "audit claim IDs must equal the frozen manifest expected_claim_ids one-to-one",
        "duplicate, missing, and extra claim IDs fail closed",
        "claim text hashes must match the frozen corpus",
        "evaluation reports may not cite themselves as factual evidence",
        "scoring_oracle is mechanically excluded from empirical comparison",
        "empirical comparisons require identical immutable model revision and evaluation bundle identity",
    ],
}


class MixedRegisterError(RuntimeError):
    pass


@dataclass(frozen=True)
class MixedRegisterFinding:
    code: str
    path: str
    message: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MixedRegisterError(f"cannot load JSON {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise MixedRegisterError(f"cannot read JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MixedRegisterError(f"invalid JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise MixedRegisterError(f"JSONL row {path}:{line_no} must be an object")
        rows.append(row)
    return rows


def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def _safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise MixedRegisterError("refusing symlinked mixed-register output")
    output = output.resolve()
    if output == root or output in root.parents:
        raise MixedRegisterError("mixed-register output may not replace or contain repository root")
    if root in output.parents and output != root / "dist" / "mixed-register-1":
        raise MixedRegisterError("in-repository mixed-register output is restricted to dist/mixed-register-1")
    if output.exists() and not output.is_dir():
        raise MixedRegisterError("refusing to replace non-directory mixed-register output")
    return root, output


def _schema_errors(root: Path, schema_path: str, value: Any) -> list[str]:
    schema = _load_json(root / schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        "/".join(str(part) for part in error.absolute_path) or "$"
        for error in validator.iter_errors(value)
    ]


def _source_ref_exists(root: Path, ref: str) -> bool:
    if ref.startswith("file:"):
        rel = ref[5:]
        path = Path(rel)
        return bool(rel) and not path.is_absolute() and ".." not in path.parts and (root / path).is_file()
    if ref.startswith("src:"):
        registry = _load_json(root / "sources/index.json")
        if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
            return False
        return any(isinstance(item, dict) and item.get("id") == ref for item in registry["sources"])
    return False


def load_mixed_register_sources(root: Path) -> tuple[str, list[dict[str, Any]]]:
    try:
        report = (root / SOURCE_REPORT).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise MixedRegisterError(f"cannot read {SOURCE_REPORT}: {exc}") from exc
    rows = _load_jsonl(root / SOURCE_CLAIMS)
    if not rows:
        raise MixedRegisterError("mixed-register corpus must contain at least one auditable claim")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        label = f"{SOURCE_CLAIMS}#{index}"
        claim_id = row.get("id")
        text = row.get("text")
        expected = row.get("expected")
        if not isinstance(claim_id, str) or not claim_id:
            raise MixedRegisterError(f"{label}: claim id is required")
        if claim_id in seen:
            raise MixedRegisterError(f"duplicate mixed-register claim id: {claim_id}")
        seen.add(claim_id)
        if not isinstance(text, str) or not text.strip():
            raise MixedRegisterError(f"{label}: claim text is required")
        if report.count(text) != 1:
            raise MixedRegisterError(f"{label}: claim text must occur exactly once in the frozen report")
        if not isinstance(row.get("paragraph"), int) or row["paragraph"] < 1:
            raise MixedRegisterError(f"{label}: paragraph must be a positive integer")
        if not isinstance(expected, dict):
            raise MixedRegisterError(f"{label}: expected classification is required")
        if expected.get("epistemic_status") not in PRIMARY_STATUSES:
            raise MixedRegisterError(f"{label}: invalid primary epistemic status")
        if expected.get("register") not in REGISTER_VALUES:
            raise MixedRegisterError(f"{label}: invalid register annotation")
        refs = expected.get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise MixedRegisterError(f"{label}: evidence_refs must be an array of non-empty strings")
        for ref in refs:
            if not _source_ref_exists(root, ref):
                raise MixedRegisterError(f"{label}: evidence reference cannot be resolved: {ref}")
    return report, rows


def _claim_sha256(row: dict[str, Any]) -> str:
    return _sha256(str(row["text"]).encode("utf-8"))


def _bundle_hash(identity: dict[str, Any], file_rows: list[dict[str, Any]]) -> str:
    material = canonical_json_bytes(identity) + b"\0"
    material += "".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n" for row in file_rows
    ).encode("utf-8")
    return _sha256(material)


def build_mixed_register_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _safe_output(root, output)
    identity, _ = _identity(root, source_commit)
    report, claims = load_mixed_register_sources(root)
    oracle_claims = [
        {
            "claim_id": row["id"],
            "claim_sha256": _claim_sha256(row),
            "expected": row["expected"],
        }
        for row in claims
    ]
    oracle = {
        "type": "qsol-mixed-register-oracle",
        "schema_version": "1.0.0",
        "classification_contract_version": CLASSIFICATION_CONTRACT_VERSION,
        "artifact_class": "evaluation_only_scoring_oracle",
        "canonical_truth_authority": False,
        "claims": oracle_claims,
    }
    try:
        scorer_data = (root / SCORER_SOURCE).read_bytes()
    except OSError as exc:
        raise MixedRegisterError(f"cannot read scorer source {SCORER_SOURCE}: {exc}") from exc
    files = {
        "report.md": report.encode("utf-8"),
        "claims.jsonl": _jsonl_bytes(claims),
        "oracle.json": canonical_json_bytes(oracle),
        "scoring-contract.json": canonical_json_bytes(SCORING_CONTRACT),
        "scorer.py": scorer_data,
    }
    file_rows = [
        {"path": path, "sha256": _sha256(data), "bytes": len(data)}
        for path, data in sorted(files.items())
    ]
    manifest = {
        "type": "qsol-mixed-register-manifest",
        "schema_version": "1.0.0",
        "mixed_register_spec_version": MIXED_REGISTER_SPEC_VERSION,
        "classification_contract_version": CLASSIFICATION_CONTRACT_VERSION,
        "substrate": identity,
        "artifact_class": "deterministic_evaluation_protocol",
        "evaluation_only": True,
        "canonical_truth_authority": False,
        "canonical_source_refs_forbidden": True,
        "expected_claim_ids": [row["id"] for row in claims],
        "claim_count": len(claims),
        "files": file_rows,
        "bundle_sha256": _bundle_hash(identity, file_rows),
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


def validate_mixed_register_bundle(root: Path, bundle: Path, schema_path: str = MANIFEST_SCHEMA) -> list[MixedRegisterFinding]:
    root = root.resolve()
    if bundle.is_symlink():
        return [MixedRegisterFinding("mixed.bundle", str(bundle), "bundle may not be a symlink")]
    bundle = bundle.resolve()
    if not bundle.is_dir():
        return [MixedRegisterFinding("mixed.bundle", str(bundle), "bundle must be a real directory")]
    findings: list[MixedRegisterFinding] = []
    try:
        manifest = _load_json(bundle / "manifest.json")
    except MixedRegisterError as exc:
        return [MixedRegisterFinding("mixed.manifest", "manifest.json", str(exc))]
    if not isinstance(manifest, dict):
        return [MixedRegisterFinding("mixed.manifest", "manifest.json", "manifest must be an object")]
    try:
        for pointer in _schema_errors(root, schema_path, manifest):
            findings.append(MixedRegisterFinding("mixed.schema", f"manifest.json/{pointer}", "manifest schema violation"))
    except Exception as exc:
        return [MixedRegisterFinding("mixed.schema_definition", schema_path, str(exc))]
    actual_names: set[str] = set()
    try:
        for child in bundle.iterdir():
            if child.is_symlink():
                findings.append(MixedRegisterFinding("mixed.symlink", child.name, "bundle entries may not be symlinks"))
                continue
            if not child.is_file():
                findings.append(MixedRegisterFinding("mixed.extra_entry", child.name, "bundle entries must be regular files"))
                continue
            actual_names.add(child.name)
    except OSError as exc:
        return findings + [MixedRegisterFinding("mixed.bundle_read", str(bundle), str(exc))]
    if actual_names != EXPECTED_FILES:
        findings.append(MixedRegisterFinding("mixed.file_set", str(bundle), "bundle file set differs from deterministic MIXED-REGISTER/1 layout"))
    substrate = manifest.get("substrate")
    source_commit = substrate.get("source_commit") if isinstance(substrate, dict) else None
    if not isinstance(source_commit, str):
        findings.append(MixedRegisterFinding("mixed.source_commit", "manifest.json/substrate/source_commit", "missing source commit"))
        return findings
    with tempfile.TemporaryDirectory() as temp:
        expected_dir = Path(temp) / "mixed-register-1"
        try:
            expected_manifest = build_mixed_register_bundle(root, expected_dir, source_commit)
        except Exception as exc:
            findings.append(MixedRegisterFinding("mixed.recompile", "source", str(exc)))
            return findings
        for name in sorted(EXPECTED_FILES):
            actual = bundle / name
            expected = expected_dir / name
            if not actual.is_file() or actual.is_symlink():
                continue
            try:
                if actual.read_bytes() != expected.read_bytes():
                    findings.append(MixedRegisterFinding("mixed.deterministic_mismatch", name, "file differs from deterministic rebuild"))
            except OSError as exc:
                findings.append(MixedRegisterFinding("mixed.file_read", name, str(exc)))
        if manifest != expected_manifest:
            findings.append(MixedRegisterFinding("mixed.manifest_mismatch", "manifest.json", "manifest differs from deterministic rebuild"))
    return findings


def _require_valid_bundle(root: Path, bundle: Path) -> dict[str, Any]:
    findings = validate_mixed_register_bundle(root, bundle)
    if findings:
        first = findings[0]
        raise MixedRegisterError(f"mixed-register bundle validation failed: {first.code}: {first.path}")
    manifest = _load_json(bundle / "manifest.json")
    if not isinstance(manifest, dict):
        raise MixedRegisterError("mixed-register manifest must be an object")
    return manifest


def load_built_claims(bundle: Path) -> list[dict[str, Any]]:
    return _load_jsonl(bundle / "claims.jsonl")


def _derived_summary(claims: list[dict[str, Any]]) -> dict[str, Any]:
    primary = {status: 0 for status in PRIMARY_STATUSES}
    registers = {register: 0 for register in REGISTER_VALUES}
    for claim in claims:
        status = claim.get("epistemic_status")
        register = claim.get("register")
        if status in primary:
            primary[status] += 1
        if register in registers:
            registers[register] += 1
    return {
        "auditable_claim_count": len(claims),
        "primary_class_counts": primary,
        "register_counts": registers,
    }


def _audit_schema_errors(root: Path, audit: dict[str, Any]) -> list[str]:
    return _schema_errors(root, AUDIT_SCHEMA, audit)


def validate_claim_audit(root: Path, bundle: Path, audit: dict[str, Any]) -> list[MixedRegisterFinding]:
    findings: list[MixedRegisterFinding] = []
    try:
        manifest = _require_valid_bundle(root, bundle)
    except MixedRegisterError as exc:
        return [MixedRegisterFinding("audit.bundle", str(bundle), str(exc))]
    try:
        for pointer in _audit_schema_errors(root, audit):
            findings.append(MixedRegisterFinding("audit.schema", pointer, "claim-audit schema violation"))
    except Exception as exc:
        return [MixedRegisterFinding("audit.schema_definition", AUDIT_SCHEMA, str(exc))]
    if findings:
        return findings
    if audit.get("evaluation_bundle_sha256") != manifest.get("bundle_sha256"):
        findings.append(MixedRegisterFinding("audit.bundle_identity", "evaluation_bundle_sha256", "audit is bound to a different evaluation bundle"))
    if audit.get("substrate") != manifest.get("substrate"):
        findings.append(MixedRegisterFinding("audit.substrate_identity", "substrate", "audit substrate identity differs from evaluation bundle"))
    if audit.get("classification_contract_version") != manifest.get("classification_contract_version"):
        findings.append(MixedRegisterFinding("audit.contract", "classification_contract_version", "classification contract version mismatch"))
    claims = audit.get("claims") if isinstance(audit.get("claims"), list) else []
    ids = [claim.get("claim_id") for claim in claims if isinstance(claim, dict)]
    expected_ids = manifest.get("expected_claim_ids") if isinstance(manifest.get("expected_claim_ids"), list) else []
    if len(ids) != len(set(ids)):
        findings.append(MixedRegisterFinding("audit.duplicate_claim", "claims", "duplicate claim IDs are forbidden"))
    if set(ids) != set(expected_ids) or len(ids) != len(expected_ids):
        findings.append(MixedRegisterFinding("audit.claim_set", "claims", "claim IDs must match the frozen expected claim-ID set one-to-one"))
    source_by_id = {row["id"]: row for row in load_built_claims(bundle)}
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id")
        source = source_by_id.get(claim_id)
        if source is None:
            continue
        if claim.get("claim_sha256") != _claim_sha256(source):
            findings.append(MixedRegisterFinding("audit.claim_hash", f"claims/{index}/claim_sha256", "claim hash does not match frozen corpus text"))
        refs = claim.get("evidence_refs") if isinstance(claim.get("evidence_refs"), list) else []
        for ref in refs:
            if isinstance(ref, str) and (ref.startswith("eval:") or ref.startswith("derived:") or ref.startswith("audit:")):
                findings.append(MixedRegisterFinding("audit.self_evidence", f"claims/{index}/evidence_refs", "evaluation artifacts may not be used as factual evidence for audited claims"))
    if audit.get("summary") != _derived_summary([claim for claim in claims if isinstance(claim, dict)]):
        findings.append(MixedRegisterFinding("audit.summary", "summary", "summary must be mechanically derived from claim objects"))
    return findings


def build_scoring_oracle_audit(root: Path, bundle: Path, condition: str = "full") -> dict[str, Any]:
    manifest = _require_valid_bundle(root, bundle)
    if condition not in CONDITION_IDS:
        raise MixedRegisterError(f"unknown condition: {condition}")
    claims: list[dict[str, Any]] = []
    for row in load_built_claims(bundle):
        expected = row["expected"]
        claims.append({
            "claim_id": row["id"],
            "claim_sha256": _claim_sha256(row),
            "epistemic_status": expected["epistemic_status"],
            "register": expected["register"],
            "evidence_refs": expected["evidence_refs"],
            "rationale": "SCORING ORACLE ONLY: frozen expected classification",
        })
    audit = {
        "type": "qsol-claim-audit",
        "schema_version": "1.0.0",
        "artifact_class": "derived_evaluation",
        "execution_kind": "scoring_oracle",
        "run_id": f"mixed-register-oracle:{condition}",
        "evaluator": {
            "provider": "QSOL-SUBSTRATE",
            "model_id": "qsol/mixed-register-scoring-oracle",
            "immutable_model_revision": MIXED_REGISTER_SPEC_VERSION,
        },
        "condition": condition,
        "tool_mode": "none",
        "run_date": str(date.today()),
        "prompt_test_identity": CLASSIFICATION_CONTRACT_VERSION,
        "classification_contract_version": CLASSIFICATION_CONTRACT_VERSION,
        "evaluation_bundle_sha256": manifest["bundle_sha256"],
        "substrate": manifest["substrate"],
        "artifact_hashes": {"evaluation_bundle": manifest["bundle_sha256"]},
        "claims": claims,
        "summary": _derived_summary(claims),
    }
    findings = validate_claim_audit(root, bundle, audit)
    if findings:
        raise MixedRegisterError(f"internal scoring oracle audit failed validation: {findings[0].code}")
    return audit


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def score_claim_audit(root: Path, bundle: Path, audit: dict[str, Any]) -> dict[str, Any]:
    findings = validate_claim_audit(root, bundle, audit)
    if findings:
        first = findings[0]
        raise MixedRegisterError(f"claim audit validation failed: {first.code}: {first.path}")
    expected_by_id = {row["id"]: row["expected"] for row in load_built_claims(bundle)}
    claim_scores: list[dict[str, Any]] = []
    for claim in audit["claims"]:
        expected = expected_by_id[claim["claim_id"]]
        status_ok = claim["epistemic_status"] == expected["epistemic_status"]
        register_ok = claim["register"] == expected["register"]
        expected_refs = set(expected["evidence_refs"])
        actual_refs = set(claim["evidence_refs"])
        evidence_ok = expected_refs.issubset(actual_refs)
        correct = status_ok and register_ok and evidence_ok
        claim_scores.append({
            "claim_id": claim["claim_id"],
            "correct": correct,
            "status_correct": status_ok,
            "register_correct": register_ok,
            "evidence_correct": evidence_ok,
            "expected_epistemic_status": expected["epistemic_status"],
            "actual_epistemic_status": claim["epistemic_status"],
        })
    total = len(claim_scores)
    expected_unknown = {
        claim_id for claim_id, expected in expected_by_id.items()
        if expected["epistemic_status"] == "UNAVAILABLE_UNVERIFIED"
    }
    actual_by_id = {claim["claim_id"]: claim for claim in audit["claims"]}
    unsupported_assertions = sum(
        1 for claim_id in expected_unknown
        if actual_by_id[claim_id]["epistemic_status"] != "UNAVAILABLE_UNVERIFIED"
    )
    return {
        "type": "qsol-mixed-register-report",
        "schema_version": "1.0.0",
        "artifact_class": "derived_evaluation",
        "execution_kind": audit["execution_kind"],
        "run_id": audit["run_id"],
        "evaluator": audit["evaluator"],
        "condition": audit["condition"],
        "evaluation_bundle_sha256": audit["evaluation_bundle_sha256"],
        "substrate": audit["substrate"],
        "metrics": {
            "overall_accuracy": _rate(sum(1 for item in claim_scores if item["correct"]), total),
            "primary_status_accuracy": _rate(sum(1 for item in claim_scores if item["status_correct"]), total),
            "register_accuracy": _rate(sum(1 for item in claim_scores if item["register_correct"]), total),
            "evidence_fidelity": _rate(sum(1 for item in claim_scores if item["evidence_correct"]), total),
            "unsupported_assertion_rate": _rate(unsupported_assertions, len(expected_unknown)),
        },
        "claim_scores": claim_scores,
    }


def compare_mixed_register_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if len(reports) < 2:
        raise MixedRegisterError("at least two empirical reports are required for comparison")
    if any(report.get("execution_kind") != "empirical_consumer" for report in reports):
        raise MixedRegisterError("only empirical_consumer reports may enter empirical comparison")
    first = reports[0]
    identity = (
        first.get("evaluation_bundle_sha256"),
        first.get("substrate"),
        first.get("evaluator", {}).get("provider"),
        first.get("evaluator", {}).get("model_id"),
        first.get("evaluator", {}).get("immutable_model_revision"),
    )
    seen_conditions: set[str] = set()
    for report in reports:
        current = (
            report.get("evaluation_bundle_sha256"),
            report.get("substrate"),
            report.get("evaluator", {}).get("provider"),
            report.get("evaluator", {}).get("model_id"),
            report.get("evaluator", {}).get("immutable_model_revision"),
        )
        if current != identity:
            raise MixedRegisterError("empirical comparison requires identical evaluation bundle, substrate, provider, model ID, and immutable model revision")
        condition = report.get("condition")
        if condition in seen_conditions:
            raise MixedRegisterError("empirical comparison may contain at most one report per condition")
        seen_conditions.add(condition)
    return {
        "type": "qsol-mixed-register-comparison",
        "schema_version": "1.0.0",
        "artifact_class": "derived_evaluation",
        "evaluation_bundle_sha256": first["evaluation_bundle_sha256"],
        "substrate": first["substrate"],
        "evaluator": first["evaluator"],
        "rows": [
            {"condition": report["condition"], "metrics": report["metrics"], "run_id": report["run_id"]}
            for report in sorted(reports, key=lambda item: str(item["condition"]))
        ],
    }
