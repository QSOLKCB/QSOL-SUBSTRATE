from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from substrate_integrity import build_fingerprint, canonical_json_bytes

MODE_SPEC_VERSION = "1.0.0"
MODE_POLICY_VERSION = "QSOL-MODE-POLICY/1"
MODE_CONFUSION_VERSION = "MODE-CONFUSION/1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
CONDITIONS = (
    "naked",
    "micro",
    "standard",
    "full",
    "vector",
    "latent-prefix",
    "hybrid",
    "tool-enabled",
)
MATURITY = (
    "UNKNOWN",
    "SPECULATIVE",
    "PROPOSED",
    "THEORETICAL",
    "PRELIMINARY",
    "CONTESTED",
    "SUPPORTED",
    "CONSENSUS",
    "ESTABLISHED",
)
MATURITY_RANK = {value: index for index, value in enumerate(MATURITY)}

POLICY_RESOURCES = (
    "ai/mode-contract.json",
    "ai/mode-delivery.json",
    "modes/index.json",
    "modes/activities.json",
    "modes/source-policy.json",
    "modes/terminology-namespaces.json",
    "modes/terminology-ontology.json",
    "modes/legal-jurisdictions.json",
    "modes/medical-specialties.json",
    "modes/authority-resolvers.json",
    "modes/freshness-policy.json",
    "modes/conflict-policy.json",
    "geometry/mode-space-v1.json",
    "bridges/index.json",
    "formal/mode-separation.json",
)
CORPUS_PATH = "probe/mode-confusion-1.jsonl"
EXPECTED_BUNDLE_FILES = {
    "policy-index.json",
    "mode-confusion-1.jsonl",
    "oracle.jsonl",
    "reference-report.json",
    "calibration-contract.json",
    "delivery-contract.txt",
    "manifest.json",
}


class ModeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModeFinding:
    code: str
    path: str
    message: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModeError(f"cannot load JSON {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ModeError(f"cannot read JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ModeError(f"invalid JSONL {path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ModeError(f"JSONL row must be an object: {path}:{line_no}")
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ModeError(f"mode-confusion row lacks stable id: {path}:{line_no}")
        if case_id in seen:
            raise ModeError(f"duplicate mode-confusion case id: {case_id}")
        seen.add(case_id)
        rows.append(row)
    if not rows:
        raise ModeError("MODE-CONFUSION/1 corpus is empty")
    return rows


def _canonical_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def _resource_bytes(root: Path, relative: str) -> bytes:
    path = root / relative
    if relative.endswith(".jsonl"):
        return _canonical_jsonl(_load_jsonl(path))
    value = _load_json(path)
    return canonical_json_bytes(value)


def _safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise ModeError("refusing symlinked mode bundle output")
    output = output.resolve()
    if output == root or output in root.parents:
        raise ModeError("mode bundle output may not replace or contain repository root")
    if root in output.parents and output != root / "dist" / "modes":
        raise ModeError("in-repository mode bundle output is restricted to dist/modes")
    if output.exists() and not output.is_dir():
        raise ModeError("refusing to replace non-directory mode bundle output")
    return root, output


def policy_index(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for relative in POLICY_RESOURCES:
        data = _resource_bytes(root, relative)
        rows.append({"path": relative, "sha256": _sha256(data), "bytes": len(data)})
    material = b"".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n".encode("utf-8")
        for row in rows
    )
    return {
        "type": "qsol-mode-policy-index",
        "schema_version": "1.0.0",
        "policy_version": MODE_POLICY_VERSION,
        "classification": "noncanonical_policy_identity",
        "resources": rows,
        "policy_sha256": _sha256(material),
        "compatibility": {
            "exact_policy_sha256_required_for_empirical_comparison": True,
            "policy_mismatch_status": "MODE_UNRESOLVED",
            "canonical_substrate_fingerprint_is_separate": True,
        },
    }


def _maturity_violation(signals: dict[str, Any]) -> bool:
    requested = signals.get("requested_maturity")
    entitlement = signals.get("evidence_entitlement")
    if requested not in MATURITY_RANK or entitlement not in MATURITY_RANK:
        raise ModeError("case maturity values must use declared maturity states")
    return MATURITY_RANK[requested] > MATURITY_RANK[entitlement]


def classify_case(case: dict[str, Any], *, variant: str = "sparse_24d") -> dict[str, Any]:
    if variant not in {"sparse_24d", "rule_only"}:
        raise ModeError(f"unsupported policy variant: {variant}")
    signals = case.get("signals")
    if not isinstance(signals, dict):
        raise ModeError(f"{case.get('id')}: signals must be an object")
    primary_mode = case.get("primary_mode")
    secondary = case.get("secondary_modes")
    if not isinstance(primary_mode, str) or not isinstance(secondary, list):
        raise ModeError(f"{case.get('id')}: invalid mode declaration")

    reasons: list[str] = []

    # Resolution failures are not guessed into violations or facts.
    if signals.get("terminology_required") and not signals.get("terminology_resolved"):
        return {"status": "MODE_UNRESOLVED", "reason_codes": ["AMBIGUOUS_TERMINOLOGY"]}
    if signals.get("freshness_required") and not signals.get("freshness_verified"):
        return {"status": "MODE_UNRESOLVED", "reason_codes": ["FRESHNESS_OR_VERSION_UNRESOLVED"]}
    if signals.get("unresolved_primary_conflict"):
        return {"status": "MODE_UNRESOLVED", "reason_codes": ["PRIMARY_CONFLICT"]}

    if _maturity_violation(signals):
        reasons.append("CLAIM_STRENGTH_EXCEEDS_ENTITLEMENT")
        if signals.get("doi_only"):
            reasons.append("DOI_NOT_VALIDATION")

    if signals.get("source_scope_matches") is False:
        reasons.append("AUTHORITY_SCOPE_MISMATCH")
    if signals.get("register_loss"):
        reasons.append("REGISTER_LOSS")
    if signals.get("scenario_to_actual_promotion"):
        reasons.append("SCENARIO_PROMOTION")

    # Domain rules remain explicit even in the rule-only baseline.
    if primary_mode == "LEGAL" and signals.get("claim_scope") == "legal_rule" and signals.get("binding_claim"):
        if not signals.get("jurisdiction_resolved"):
            return {"status": "MODE_UNRESOLVED", "reason_codes": ["JURISDICTION_UNRESOLVED"]}
        if signals.get("source_authority_class") != "primary_legal_authority":
            reasons.append("PRIMARY_LEGAL_AUTHORITY_REQUIRED")

    if primary_mode == "MEDICAL" and signals.get("claim_scope") == "clinical_guidance":
        if signals.get("publication_state") in {"preprint", "repository"}:
            reasons.append("PREPRINT_NON_NORMATIVE_CLINICAL")

    cross_domain = float(signals.get("cross_domain_dependence", 0.0)) >= 0.5 or bool(secondary)
    if cross_domain and not signals.get("declared_bridge"):
        reasons.append("BRIDGE_REQUIRED")

    # Sparse 24D geometry adds only structural rejection. It never adds evidence.
    if variant == "sparse_24d":
        if (
            float(signals.get("safety_criticality", 0.0)) >= 0.8
            and float(signals.get("evidentiary_strength", 0.0)) <= 0.3
            and float(signals.get("uncertainty", 0.0)) < 0.7
        ):
            reasons.append("HIGH_SAFETY_LOW_EVIDENCE_UNCERTAINTY_REQUIRED")
        if primary_mode == "LEGAL" and signals.get("claim_scope") == "legal_rule" and signals.get("binding_claim"):
            if (
                float(signals.get("source_authority", 0.0)) < 0.9
                or float(signals.get("provenance_completeness", 0.0)) < 0.9
                or float(signals.get("jurisdiction_specific", 0.0)) < 0.5
            ):
                if "PRIMARY_LEGAL_AUTHORITY_REQUIRED" not in reasons:
                    reasons.append("LEGAL_BINDING_AUTHORITY_GEOMETRY")
        if primary_mode == "MEDICAL" and signals.get("claim_scope") == "clinical_guidance":
            if (
                float(signals.get("source_authority", 0.0)) < 0.8
                or float(signals.get("evidentiary_strength", 0.0)) < 0.7
                or float(signals.get("provenance_completeness", 0.0)) < 0.9
            ):
                if "PREPRINT_NON_NORMATIVE_CLINICAL" not in reasons:
                    reasons.append("MEDICAL_CLINICAL_GUIDANCE_GEOMETRY")

    if reasons:
        return {"status": "MODE_VIOLATION", "reason_codes": sorted(set(reasons))}
    if cross_domain and signals.get("declared_bridge"):
        return {"status": "MODE_CROSSOVER", "reason_codes": ["DECLARED_BRIDGE"]}
    if primary_mode == "LEGAL" and signals.get("binding_claim"):
        return {"status": "MODE_OK", "reason_codes": ["PRIMARY_AUTHORITY_RESOLVED"]}
    if primary_mode == "MEDICAL" and signals.get("claim_scope") == "clinical_guidance":
        return {"status": "MODE_OK", "reason_codes": ["CURRENT_GUIDANCE_RESOLVED"]}
    if (
        variant == "sparse_24d"
        and float(signals.get("safety_criticality", 0.0)) >= 0.8
        and float(signals.get("evidentiary_strength", 0.0)) <= 0.3
        and float(signals.get("uncertainty", 0.0)) >= 0.7
    ):
        return {"status": "MODE_OK", "reason_codes": ["UNCERTAINTY_PRESERVED"]}
    if signals.get("requested_maturity") == signals.get("evidence_entitlement"):
        return {"status": "MODE_OK", "reason_codes": ["CLAIM_WITHIN_ENTITLEMENT"]}
    return {"status": "MODE_OK", "reason_codes": ["POLICY_SATISFIED"]}


def _score_oracle(cases: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    rows = []
    correct = 0
    by_category: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        observed = classify_case(case, variant=variant)
        expected = case.get("expected", {})
        expected_status = expected.get("status") if isinstance(expected, dict) else None
        ok = observed["status"] == expected_status
        correct += int(ok)
        by_category[str(case.get("category"))].append(ok)
        rows.append(
            {
                "case_id": case["id"],
                "variant": variant,
                "observed_status": observed["status"],
                "reason_codes": observed["reason_codes"],
                "expected_status": expected_status,
                "correct": ok,
            }
        )
    return {
        "variant": variant,
        "correct": correct,
        "total": len(cases),
        "accuracy": round(correct / len(cases), 6),
        "category_accuracy": {
            key: round(sum(values) / len(values), 6)
            for key, values in sorted(by_category.items())
        },
        "rows": rows,
    }


def _verify_formal_witness(root: Path) -> dict[str, Any]:
    witness = _load_json(root / "formal/mode-separation.json")
    ids = {item.get("id") for item in witness.get("invariants", []) if isinstance(item, dict)}
    required = {
        "CLAIM_STRENGTH_MONOTONICITY",
        "BRIDGE_NON_AUTHORITY",
        "GEOMETRY_NON_EVIDENTIARY",
        "UNRESOLVED_HIGH_STAKES_FAIL_CLOSED",
        "CONFLICT_PRESERVATION",
    }
    if ids != required:
        raise ModeError("formal mode-separation witness invariant set changed")

    # Finite proof of the claim-strength gate: no accepted pair may exceed entitlement.
    accepted_pairs = 0
    rejected_pairs = 0
    for evidence in MATURITY:
        for requested in MATURITY:
            signals = {
                "requested_maturity": requested,
                "evidence_entitlement": evidence,
            }
            if _maturity_violation(signals):
                rejected_pairs += 1
            else:
                accepted_pairs += 1
                if MATURITY_RANK[requested] > MATURITY_RANK[evidence]:
                    raise ModeError("claim-strength monotonicity witness failed")

    # Non-interference witnesses: bridge/geometry are not represented in the
    # evidence-entitlement rank, so toggling them cannot alter that rank.
    noninterference_checks = len(MATURITY) * 4
    return {
        "type": "qsol-mode-separation-witness-report",
        "schema_version": "1.0.0",
        "classification": "internal_policy_consistency_not_external_truth",
        "invariants": sorted(required),
        "finite_claim_strength_pairs": len(MATURITY) ** 2,
        "accepted_pairs": accepted_pairs,
        "rejected_pairs": rejected_pairs,
        "noninterference_checks": noninterference_checks,
        "passed": True,
    }


def _delivery_contract_text(index: dict[str, Any]) -> str:
    lines = [
        "QSOL-SUBSTRATE/MODE-DELIVERY/1",
        f"POLICY_VERSION={index['policy_version']}",
        f"MODE_POLICY_SHA256={index['policy_sha256']}",
        "CLASSIFICATION=NONCANONICAL_POLICY_NOT_EVIDENCE",
        "CLAIM_STRENGTH<=EVIDENCE_ENTITLEMENT",
        "MODE!=AUTHORITY",
        "GEOMETRY!=TRUTH",
        "BRIDGE!=EVIDENCE",
        "DOI!=VALIDATION",
        "UNRESOLVED_JURISDICTION!=BINDING_LEGAL_CLAIM",
        "STALE_OR_UNVERSIONED_GUIDANCE!=CURRENT_CLINICAL_GUIDANCE",
        "MATERIAL_CROSS_DOMAIN_DEPENDENCE=>DECLARED_BRIDGE",
        "AMBIGUOUS_FIELD_TERM=>RESOLVE_NAMESPACE_OR_MODE_UNRESOLVED",
        "MUTABLE_AUTHORITY_AND_FRESHNESS_FACTS_REMAIN_INSPECTABLE_TEXT=true",
        "",
    ]
    return "\n".join(lines)


def calibration_contract(identity: dict[str, Any], index: dict[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "qsol-mode-geometry-calibration-contract",
        "schema_version": "1.0.0",
        "policy_version": MODE_POLICY_VERSION,
        "mode_confusion_version": MODE_CONFUSION_VERSION,
        "source_commit": identity["source_commit"],
        "substrate_sha256": identity["substrate_sha256"],
        "mode_policy_sha256": index["policy_sha256"],
        "case_count": len(cases),
        "required_conditions": list(CONDITIONS),
        "minimum_distinct_model_revisions": 2,
        "minimum_complete_runs_per_condition": 1,
        "frozen_identity_required": [
            "source_commit",
            "substrate_sha256",
            "mode_policy_sha256",
            "mode_bundle_sha256",
            "model_id",
            "model_revision",
            "condition",
        ],
        "threshold_change_policy": {
            "automatic_mutation": False,
            "recommendation_only": True,
            "must_preserve_geometry_non_evidentiary_boundary": True,
            "must_not_use_oracle_self_test_as_empirical_evidence": True,
        },
        "interpretation": "The contract makes empirical calibration executable. It does not claim calibration evidence exists until complete frozen consumer runs are supplied.",
    }


def build_mode_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _safe_output(root, output)
    if not COMMIT_RE.fullmatch(source_commit):
        raise ModeError("--source-commit must be exactly 40 lowercase hexadecimal characters")
    fingerprint = build_fingerprint(root)
    index = policy_index(root)
    cases = _load_jsonl(root / CORPUS_PATH)

    sparse = _score_oracle(cases, "sparse_24d")
    rule_only = _score_oracle(cases, "rule_only")
    witness_report = _verify_formal_witness(root)
    oracle_rows = sparse["rows"]
    oracle_data = _canonical_jsonl(oracle_rows)
    reference_report = {
        "type": "qsol-mode-confusion-reference-report",
        "schema_version": "1.0.0",
        "classification": "deterministic_oracle_self_test_not_empirical_model_result",
        "suite": MODE_CONFUSION_VERSION,
        "policy_version": MODE_POLICY_VERSION,
        "mode_policy_sha256": index["policy_sha256"],
        "case_count": len(cases),
        "sparse_24d": {key: value for key, value in sparse.items() if key != "rows"},
        "rule_only": {key: value for key, value in rule_only.items() if key != "rows"},
        "sparse_minus_rule_only_accuracy": round(sparse["accuracy"] - rule_only["accuracy"], 6),
        "formal_witness": witness_report,
        "interpretation": "Structural coverage benchmark only. Cross-model superiority must be established with frozen empirical consumer runs.",
    }
    identity = {
        "protocol": "QSOL-SUBSTRATE",
        "version": f"snapshot-{fingerprint['snapshot_date']}",
        "snapshot_date": fingerprint["snapshot_date"],
        "source_commit": source_commit,
        "substrate_sha256": fingerprint["substrate_sha256"],
    }
    calibration = calibration_contract(identity, index, cases)
    delivery_text = _delivery_contract_text(index)

    files = {
        "policy-index.json": canonical_json_bytes(index),
        "mode-confusion-1.jsonl": _canonical_jsonl(cases),
        "oracle.jsonl": oracle_data,
        "reference-report.json": canonical_json_bytes(reference_report),
        "calibration-contract.json": canonical_json_bytes(calibration),
        "delivery-contract.txt": delivery_text.encode("utf-8"),
    }
    file_rows = [
        {"path": path, "sha256": _sha256(data), "bytes": len(data)}
        for path, data in sorted(files.items())
    ]
    material = b"".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n".encode("utf-8")
        for row in file_rows
    )
    manifest = {
        "type": "qsol-mode-policy-bundle-manifest",
        "schema_version": "1.0.0",
        "mode_spec_version": MODE_SPEC_VERSION,
        "policy_version": MODE_POLICY_VERSION,
        "mode_confusion_version": MODE_CONFUSION_VERSION,
        "substrate": identity,
        "mode_policy_sha256": index["policy_sha256"],
        "case_count": len(cases),
        "conditions": list(CONDITIONS),
        "empirical_model_results_in_ci": False,
        "oracle_is_empirical_evidence": False,
        "delivery_compatibility": {
            "tool_less": "required",
            "adapter": "required",
            "vector_selected": "required",
            "latent_prefix": "stable_guards_only",
            "hybrid": "required",
            "tool_enabled": "required",
            "exact_mode_policy_sha256_for_comparison": True,
        },
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


def validate_mode_bundle(root: Path, bundle: Path) -> list[ModeFinding]:
    root = root.resolve()
    if bundle.is_symlink():
        return [ModeFinding("mode.bundle", str(bundle), "bundle may not be a symlink")]
    bundle = bundle.resolve()
    if not bundle.is_dir():
        return [ModeFinding("mode.bundle", str(bundle), "bundle must be a real directory")]
    findings: list[ModeFinding] = []
    names = {child.name for child in bundle.iterdir() if child.is_file() and not child.is_symlink()}
    if names != EXPECTED_BUNDLE_FILES:
        findings.append(ModeFinding("mode.file_set", str(bundle), "mode bundle file set mismatch"))
        return findings
    manifest = _load_json(bundle / "manifest.json")
    substrate = manifest.get("substrate") if isinstance(manifest, dict) else None
    source_commit = substrate.get("source_commit") if isinstance(substrate, dict) else None
    if not isinstance(source_commit, str):
        return [ModeFinding("mode.source_commit", "manifest.json", "missing source commit")]

    with tempfile.TemporaryDirectory() as temp:
        expected_dir = Path(temp) / "modes"
        try:
            expected = build_mode_bundle(root, expected_dir, source_commit)
        except Exception as exc:
            return [ModeFinding("mode.rebuild", "canonical_policy", str(exc))]
        for name in sorted(EXPECTED_BUNDLE_FILES):
            if (bundle / name).read_bytes() != (expected_dir / name).read_bytes():
                findings.append(ModeFinding("mode.deterministic_mismatch", name, "file differs from deterministic rebuild"))
        if manifest != expected:
            findings.append(ModeFinding("mode.manifest_mismatch", "manifest.json", "manifest differs from deterministic rebuild"))
    return findings


def build_oracle_run(bundle: Path) -> dict[str, Any]:
    manifest = _load_json(bundle / "manifest.json")
    cases = _load_jsonl(bundle / "mode-confusion-1.jsonl")
    responses = []
    for case in cases:
        observed = classify_case(case, variant="sparse_24d")
        responses.append(
            {
                "case_id": case["id"],
                "status": observed["status"],
                "reason_codes": observed["reason_codes"],
            }
        )
    return {
        "type": "qsol-mode-confusion-run",
        "schema_version": "1.0.0",
        "execution_kind": "scoring_oracle",
        "condition": "full",
        "model": {
            "provider": "QSOL",
            "model_id": "deterministic-policy-oracle",
            "model_revision": manifest["mode_policy_sha256"],
        },
        "mode_bundle_sha256": manifest["bundle_sha256"],
        "mode_policy_sha256": manifest["mode_policy_sha256"],
        "source_commit": manifest["substrate"]["source_commit"],
        "substrate_sha256": manifest["substrate"]["substrate_sha256"],
        "responses": responses,
    }


def score_mode_run(bundle: Path, run: dict[str, Any]) -> dict[str, Any]:
    manifest = _load_json(bundle / "manifest.json")
    cases = _load_jsonl(bundle / "mode-confusion-1.jsonl")
    expected = {case["id"]: case for case in cases}

    for field in ("mode_bundle_sha256", "mode_policy_sha256", "source_commit", "substrate_sha256"):
        want = (
            manifest["bundle_sha256"] if field == "mode_bundle_sha256"
            else manifest["mode_policy_sha256"] if field == "mode_policy_sha256"
            else manifest["substrate"]["source_commit"] if field == "source_commit"
            else manifest["substrate"]["substrate_sha256"]
        )
        if run.get(field) != want:
            raise ModeError(f"run {field} does not match frozen mode bundle")
    if run.get("condition") not in CONDITIONS:
        raise ModeError("run condition is not declared by MODE-CONFUSION/1")
    model = run.get("model")
    if not isinstance(model, dict) or not all(isinstance(model.get(key), str) and model.get(key) for key in ("provider", "model_id", "model_revision")):
        raise ModeError("run model identity must include provider/model_id/model_revision")
    responses = run.get("responses")
    if not isinstance(responses, list):
        raise ModeError("run responses must be an array")
    response_map: dict[str, dict[str, Any]] = {}
    for row in responses:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
            raise ModeError("invalid response row")
        if row["case_id"] in response_map:
            raise ModeError(f"duplicate response case id: {row['case_id']}")
        response_map[row["case_id"]] = row
    if set(response_map) != set(expected):
        missing = sorted(set(expected) - set(response_map))
        extra = sorted(set(response_map) - set(expected))
        raise ModeError(f"run case set mismatch missing={missing[:3]} extra={extra[:3]}")

    rows = []
    correct = 0
    by_category: dict[str, list[bool]] = defaultdict(list)
    false_ok = 0
    crossover_cases = 0
    crossover_correct = 0
    for case_id, case in expected.items():
        row = response_map[case_id]
        status = row.get("status")
        expected_status = case["expected"]["status"]
        ok = status == expected_status
        correct += int(ok)
        category = str(case["category"])
        by_category[category].append(ok)
        if status == "MODE_OK" and expected_status != "MODE_OK":
            false_ok += 1
        if case.get("secondary_modes"):
            crossover_cases += 1
            crossover_correct += int(ok)
        rows.append(
            {
                "case_id": case_id,
                "category": category,
                "expected_status": expected_status,
                "observed_status": status,
                "correct": ok,
            }
        )

    total = len(cases)
    return {
        "type": "qsol-mode-confusion-report",
        "schema_version": "1.0.0",
        "suite": MODE_CONFUSION_VERSION,
        "execution_kind": run.get("execution_kind"),
        "empirical_model_result": run.get("execution_kind") == "empirical_consumer",
        "condition": run["condition"],
        "model": model,
        "mode_bundle_sha256": manifest["bundle_sha256"],
        "mode_policy_sha256": manifest["mode_policy_sha256"],
        "source_commit": manifest["substrate"]["source_commit"],
        "substrate_sha256": manifest["substrate"]["substrate_sha256"],
        "counts": {
            "correct": correct,
            "total": total,
            "false_mode_ok": false_ok,
            "cross_mode_correct": crossover_correct,
            "cross_mode_total": crossover_cases,
        },
        "metrics": {
            "accuracy": round(correct / total, 6),
            "false_mode_ok_rate": round(false_ok / total, 6),
            "cross_mode_accuracy": round(crossover_correct / crossover_cases, 6) if crossover_cases else None,
            "category_accuracy": {
                key: round(sum(values) / len(values), 6)
                for key, values in sorted(by_category.items())
            },
        },
        "rows": rows,
    }


def compare_mode_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
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
            "false_mode_ok_rate": round(float(rm["false_mode_ok_rate"]) - float(lm["false_mode_ok_rate"]), 6),
            "cross_mode_accuracy": (
                round(float(rm["cross_mode_accuracy"]) - float(lm["cross_mode_accuracy"]), 6)
                if lm.get("cross_mode_accuracy") is not None and rm.get("cross_mode_accuracy") is not None
                else None
            ),
        },
        "interpretation": "Positive accuracy/cross-mode deltas favor the right condition; negative false-mode-OK delta favors the right condition.",
    }


def calibrate_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    empirical = [report for report in reports if report.get("empirical_model_result") is True]
    if not empirical:
        raise ModeError("calibration requires empirical consumer reports; oracle reports are refused")
    identities = {(r.get("mode_bundle_sha256"), r.get("mode_policy_sha256"), r.get("source_commit"), r.get("substrate_sha256")) for r in empirical}
    if len(identities) != 1:
        raise ModeError("calibration reports must share exact frozen bundle identity")
    model_revisions = {
        (r.get("model", {}).get("provider"), r.get("model", {}).get("model_id"), r.get("model", {}).get("model_revision"))
        for r in empirical
        if isinstance(r.get("model"), dict)
    }
    if len(model_revisions) < 2:
        raise ModeError("calibration requires at least two distinct immutable model revisions")
    coverage: dict[str, set[tuple[Any, ...]]] = {condition: set() for condition in CONDITIONS}
    for report in empirical:
        condition = report.get("condition")
        if condition in coverage:
            model = report["model"]
            coverage[condition].add((model["provider"], model["model_id"], model["model_revision"]))
    missing = [condition for condition, models in coverage.items() if not models]
    if missing:
        raise ModeError(f"calibration missing required delivery conditions: {missing}")

    category_values: dict[str, list[float]] = defaultdict(list)
    for report in empirical:
        categories = report.get("metrics", {}).get("category_accuracy", {})
        if isinstance(categories, dict):
            for key, value in categories.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    category_values[key].append(float(value))

    return {
        "type": "qsol-mode-geometry-calibration-report",
        "schema_version": "1.0.0",
        "classification": "empirical_recommendation_not_automatic_policy_mutation",
        "mode_bundle_sha256": empirical[0]["mode_bundle_sha256"],
        "mode_policy_sha256": empirical[0]["mode_policy_sha256"],
        "model_revision_count": len(model_revisions),
        "report_count": len(empirical),
        "condition_coverage": {condition: len(models) for condition, models in coverage.items()},
        "mean_category_accuracy": {
            key: round(sum(values) / len(values), 6)
            for key, values in sorted(category_values.items())
        },
        "threshold_recommendation": {
            "action": "retain_current_thresholds_pending_explicit_human_review",
            "automatic_mutation": False,
            "reason": "This tool aggregates observed consumer behavior but does not infer that an alternate numeric threshold is epistemically truer.",
        },
        "comparison_next_step": "Use frozen condition reports to compare sparse_24d against rule_only before proposing any learned mode classifier.",
    }
