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

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import build_fingerprint, canonical_json_bytes

MODE_SPEC_VERSION = "1.0.0"
MODE_POLICY_VERSION = "QSOL-MODE-POLICY/1"
MODE_CONFUSION_VERSION = "MODE-CONFUSION/1"
MODE_BUNDLE_SCHEMA = "schema/mode-policy-manifest.schema.json"
MODE_RUN_SCHEMA = "schema/mode-run.schema.json"
MODE_REPORT_SCHEMA = "schema/mode-report.schema.json"
MODE_POLICY_RESOURCE_SCHEMA = "schema/mode-policy-resource.schema.json"
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
    "schema/mode-policy-resource.schema.json",
)
EXTENDED_POLICY_RESOURCES = (
    "ai/mode-delivery.json",
    "modes/terminology-ontology.json",
    "modes/legal-jurisdictions.json",
    "modes/medical-specialties.json",
    "modes/authority-resolvers.json",
    "modes/freshness-policy.json",
    "modes/conflict-policy.json",
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
FORMAL_INVARIANTS = {
    "CLAIM_STRENGTH_MONOTONICITY",
    "BRIDGE_NON_AUTHORITY",
    "GEOMETRY_NON_EVIDENTIARY",
    "UNRESOLVED_HIGH_STAKES_FAIL_CLOSED",
    "CONFLICT_PRESERVATION",
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
    return canonical_json_bytes(_load_json(path))


def _schema_errors(root: Path, relative: str, value: Any) -> list[str]:
    schema = _load_json(root / relative)
    try:
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
    except Exception as exc:
        raise ModeError(f"invalid JSON Schema {relative}: {exc}") from exc
    errors = []
    for error in validator.iter_errors(value):
        pointer = "/".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{pointer}: {error.message}")
    return errors


def _require_schema_valid(root: Path, relative: str, value: Any, label: str) -> None:
    errors = _schema_errors(root, relative, value)
    if errors:
        raise ModeError(f"{label} violates {relative}: {errors[0]}")


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


def _require_unique_strings(values: Any, label: str) -> list[str]:
    if not isinstance(values, list) or not values or any(not isinstance(value, str) or not value for value in values):
        raise ModeError(f"{label} must be a non-empty string array")
    if len(values) != len(set(values)):
        raise ModeError(f"{label} contains duplicate values")
    return values


def _validate_policy_resources(root: Path) -> None:
    """Validate extended Phase 10 policy bytes before they can be fingerprinted."""
    root = root.resolve()
    for relative in EXTENDED_POLICY_RESOURCES:
        value = _load_json(root / relative)
        _require_schema_valid(root, MODE_POLICY_RESOURCE_SCHEMA, value, relative)

    modes = _load_json(root / "modes/index.json")
    mode_ids = {
        row.get("id")
        for row in modes.get("modes", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    if not mode_ids:
        raise ModeError("mode registry contains no domain modes")

    source_policy = _load_json(root / "modes/source-policy.json")
    authority_classes = set(source_policy.get("source_axes", {}).get("authority_class", []))
    if not authority_classes:
        raise ModeError("source policy contains no authority classes")

    legal = _load_json(root / "modes/legal-jurisdictions.json")
    jurisdictions = legal.get("jurisdictions", [])
    jurisdiction_ids = [row.get("id") for row in jurisdictions if isinstance(row, dict)]
    if len(jurisdiction_ids) != len(set(jurisdiction_ids)) or any(not isinstance(value, str) for value in jurisdiction_ids):
        raise ModeError("legal jurisdiction IDs must be unique strings")
    jurisdiction_set = set(jurisdiction_ids)

    resolver_registry = _load_json(root / "modes/authority-resolvers.json")
    resolver_rows = resolver_registry.get("resolvers", [])
    resolver_ids = [row.get("id") for row in resolver_rows if isinstance(row, dict)]
    if len(resolver_ids) != len(set(resolver_ids)) or any(not isinstance(value, str) for value in resolver_ids):
        raise ModeError("resolver IDs must be unique strings")
    resolvers = {row["id"]: row for row in resolver_rows if isinstance(row, dict) and isinstance(row.get("id"), str)}
    for resolver_id, resolver in resolvers.items():
        if resolver.get("domain") not in mode_ids:
            raise ModeError(f"resolver {resolver_id} references unknown mode {resolver.get('domain')!r}")
        if resolver.get("authority_class") not in authority_classes:
            raise ModeError(f"resolver {resolver_id} references unknown authority class {resolver.get('authority_class')!r}")
        jurisdiction = resolver.get("jurisdiction")
        if jurisdiction is not None and jurisdiction not in jurisdiction_set:
            raise ModeError(f"resolver {resolver_id} references unknown jurisdiction {jurisdiction!r}")

    for row in jurisdictions:
        if not isinstance(row, dict):
            raise ModeError("legal jurisdiction row must be an object")
        jurisdiction_id = row["id"]
        for resolver_id in _require_unique_strings(row.get("primary_authority_resolvers"), f"{jurisdiction_id}.primary_authority_resolvers"):
            resolver = resolvers.get(resolver_id)
            if resolver is None:
                raise ModeError(f"jurisdiction {jurisdiction_id} references unknown resolver {resolver_id}")
            if resolver.get("domain") != "LEGAL" or resolver.get("jurisdiction") != jurisdiction_id:
                raise ModeError(f"jurisdiction {jurisdiction_id} resolver {resolver_id} has incompatible domain/jurisdiction")

    medical = _load_json(root / "modes/medical-specialties.json")
    specialties = medical.get("specialties", [])
    specialty_ids = [row.get("id") for row in specialties if isinstance(row, dict)]
    if len(specialty_ids) != len(set(specialty_ids)) or any(not isinstance(value, str) for value in specialty_ids):
        raise ModeError("medical specialty IDs must be unique strings")
    for row in specialties:
        if not isinstance(row, dict):
            raise ModeError("medical specialty row must be an object")
        specialty_id = row["id"]
        for resolver_id in _require_unique_strings(row.get("required_resolvers"), f"{specialty_id}.required_resolvers"):
            if resolver_id not in resolvers:
                raise ModeError(f"medical specialty {specialty_id} references unknown resolver {resolver_id}")

    freshness = _load_json(root / "modes/freshness-policy.json")
    freshness_classes = set(freshness.get("freshness_classes", {}))
    if not freshness_classes:
        raise ModeError("freshness policy contains no freshness classes")
    profiles = freshness.get("profiles", {})
    if not isinstance(profiles, dict):
        raise ModeError("freshness profiles must be an object")
    for mode_id, profile in profiles.items():
        if mode_id not in mode_ids:
            raise ModeError(f"freshness policy references unknown mode {mode_id!r}")
        if not isinstance(profile, dict):
            raise ModeError(f"freshness profile {mode_id} must be an object")
        for key, value in profile.items():
            if key == "required_metadata":
                _require_unique_strings(value, f"freshness profiles.{mode_id}.required_metadata")
            elif isinstance(value, str) and value not in freshness_classes:
                raise ModeError(f"freshness profile {mode_id}.{key} references unknown class {value!r}")

    ontology = _load_json(root / "modes/terminology-ontology.json")
    terms = ontology.get("terms", [])
    term_names = [row.get("term") for row in terms if isinstance(row, dict)]
    if len(term_names) != len(set(term_names)) or any(not isinstance(value, str) for value in term_names):
        raise ModeError("terminology ontology terms must be unique strings")
    for row in terms:
        if not isinstance(row, dict) or not isinstance(row.get("senses"), dict):
            raise ModeError("terminology ontology row must include senses")
        unknown = sorted(set(row["senses"]) - mode_ids)
        if unknown:
            raise ModeError(f"terminology term {row.get('term')!r} uses unknown mode senses: {unknown}")

    conflict = _load_json(root / "modes/conflict-policy.json")
    high_stakes = conflict.get("high_stakes_guards", {})
    if not isinstance(high_stakes, dict) or not high_stakes:
        raise ModeError("conflict policy high_stakes_guards must be a non-empty object")
    unknown_conflict_modes = sorted(set(high_stakes) - mode_ids)
    if unknown_conflict_modes:
        raise ModeError(f"conflict policy references unknown modes: {unknown_conflict_modes}")

    delivery = _load_json(root / "ai/mode-delivery.json")
    resources = delivery.get("resources", {})
    if not isinstance(resources, dict) or not resources:
        raise ModeError("mode-delivery resources must be a non-empty object")
    for resource_name, relative in resources.items():
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ModeError(f"mode-delivery resource {resource_name} has unsafe path")
        if not (root / relative).is_file():
            raise ModeError(f"mode-delivery resource {resource_name} target does not exist: {relative}")

    witness = _load_json(root / "formal/mode-separation.json")
    witness_ids = {row.get("id") for row in witness.get("invariants", []) if isinstance(row, dict)}
    if witness_ids != FORMAL_INVARIANTS:
        raise ModeError("formal mode-separation witness invariant set changed")


def policy_index(root: Path) -> dict[str, Any]:
    _validate_policy_resources(root)
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

    if signals.get("terminology_required") and not signals.get("terminology_resolved"):
        return {"status": "MODE_UNRESOLVED", "reason_codes": ["AMBIGUOUS_TERMINOLOGY"]}
    if signals.get("freshness_required") and not signals.get("freshness_verified"):
        return {"status": "MODE_UNRESOLVED", "reason_codes": ["FRESHNESS_OR_VERSION_UNRESOLVED"]}
    if signals.get("unresolved_primary_conflict"):
        return {"status": "MODE_UNRESOLVED", "reason_codes": ["PRIMARY_CONFLICT"]}

    # A scenario-to-actual promotion is classified on its specific boundary;
    # do not double-count the resulting maturity gap as a second rationale.
    if _maturity_violation(signals) and not signals.get("scenario_to_actual_promotion"):
        reasons.append("CLAIM_STRENGTH_EXCEEDS_ENTITLEMENT")
        if signals.get("doi_only"):
            reasons.append("DOI_NOT_VALIDATION")

    if signals.get("source_scope_matches") is False:
        reasons.append("AUTHORITY_SCOPE_MISMATCH")
    if signals.get("register_loss"):
        reasons.append("REGISTER_LOSS")
    if signals.get("scenario_to_actual_promotion"):
        reasons.append("SCENARIO_PROMOTION")

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


def _expected_reason_codes(case: dict[str, Any]) -> list[str]:
    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise ModeError(f"{case.get('id')}: expected must be an object")
    reasons = expected.get("reason_codes")
    if not isinstance(reasons, list) or any(not isinstance(value, str) or not value for value in reasons):
        raise ModeError(f"{case.get('id')}: expected.reason_codes must be a string array")
    return sorted(set(reasons))


def _observed_reason_codes(row: dict[str, Any]) -> list[str]:
    reasons = row.get("reason_codes")
    if not isinstance(reasons, list) or any(not isinstance(value, str) or not value for value in reasons):
        raise ModeError("mode response reason_codes must be a non-empty string array")
    return sorted(set(reasons))


def _score_oracle(cases: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    rows = []
    correct = 0
    reason_correct = 0
    by_category: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        observed = classify_case(case, variant=variant)
        expected = case.get("expected", {})
        expected_status = expected.get("status") if isinstance(expected, dict) else None
        expected_reasons = _expected_reason_codes(case)
        observed_reasons = sorted(observed["reason_codes"])
        status_ok = observed["status"] == expected_status
        reasons_ok = observed_reasons == expected_reasons
        ok = status_ok and reasons_ok
        correct += int(ok)
        reason_correct += int(reasons_ok)
        by_category[str(case.get("category"))].append(ok)
        rows.append(
            {
                "case_id": case["id"],
                "variant": variant,
                "observed_status": observed["status"],
                "observed_reason_codes": observed_reasons,
                "expected_status": expected_status,
                "expected_reason_codes": expected_reasons,
                "status_correct": status_ok,
                "reason_codes_correct": reasons_ok,
                "correct": ok,
            }
        )
    total = len(cases)
    return {
        "variant": variant,
        "correct": correct,
        "reason_codes_correct": reason_correct,
        "total": total,
        "accuracy": round(correct / total, 6),
        "reason_code_accuracy": round(reason_correct / total, 6),
        "category_accuracy": {
            key: round(sum(values) / len(values), 6)
            for key, values in sorted(by_category.items())
        },
        "rows": rows,
    }


def _base_witness_signals(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "binding_claim": False,
        "claim_scope": "fact",
        "cross_domain_dependence": 0.0,
        "declared_bridge": False,
        "doi_only": False,
        "evidence_entitlement": "SUPPORTED",
        "evidentiary_strength": 0.8,
        "freshness_required": False,
        "freshness_verified": True,
        "jurisdiction_resolved": True,
        "jurisdiction_specific": 0.9,
        "provenance_completeness": 0.95,
        "publication_state": "official",
        "register_loss": False,
        "requested_maturity": "SUPPORTED",
        "safety_criticality": 0.2,
        "scenario_to_actual_promotion": False,
        "source_authority": 0.95,
        "source_authority_class": "official",
        "source_scope_matches": True,
        "terminology_required": False,
        "terminology_resolved": True,
        "uncertainty": 0.4,
        "unresolved_primary_conflict": False,
    }
    value.update(overrides)
    return value


def _verify_formal_witness(root: Path) -> dict[str, Any]:
    witness = _load_json(root / "formal/mode-separation.json")
    ids = {item.get("id") for item in witness.get("invariants", []) if isinstance(item, dict)}
    if ids != FORMAL_INVARIANTS:
        raise ModeError("formal mode-separation witness invariant set changed")

    results: dict[str, dict[str, Any]] = {}

    accepted_pairs = 0
    rejected_pairs = 0
    monotonic_checks = 0
    for evidence in MATURITY:
        for requested in MATURITY:
            monotonic_checks += 1
            signals = {"requested_maturity": requested, "evidence_entitlement": evidence}
            violated = _maturity_violation(signals)
            if violated:
                rejected_pairs += 1
                if MATURITY_RANK[requested] <= MATURITY_RANK[evidence]:
                    raise ModeError("claim-strength monotonicity witness rejected an entitled pair")
            else:
                accepted_pairs += 1
                if MATURITY_RANK[requested] > MATURITY_RANK[evidence]:
                    raise ModeError("claim-strength monotonicity witness accepted an overstrong pair")
    results["CLAIM_STRENGTH_MONOTONICITY"] = {
        "passed": True,
        "checks": monotonic_checks,
        "accepted_pairs": accepted_pairs,
        "rejected_pairs": rejected_pairs,
    }

    bridge_checks = 0
    for maturity in MATURITY:
        base = _base_witness_signals(
            requested_maturity=maturity,
            evidence_entitlement=maturity,
            cross_domain_dependence=0.8,
            declared_bridge=False,
            source_authority=0.6,
            source_authority_class="scholarly",
        )
        without_bridge = {"id": "W-BRIDGE-0", "primary_mode": "SCIENCE", "secondary_modes": ["FORMAL"], "signals": dict(base)}
        with_signals = dict(base, declared_bridge=True)
        with_bridge = {"id": "W-BRIDGE-1", "primary_mode": "SCIENCE", "secondary_modes": ["FORMAL"], "signals": with_signals}
        left = classify_case(without_bridge)
        right = classify_case(with_bridge)
        bridge_checks += 1
        if left != {"status": "MODE_VIOLATION", "reason_codes": ["BRIDGE_REQUIRED"]}:
            raise ModeError("bridge non-authority witness failed on undeclared bridge")
        if right != {"status": "MODE_CROSSOVER", "reason_codes": ["DECLARED_BRIDGE"]}:
            raise ModeError("bridge non-authority witness failed on declared bridge")
        if base["evidence_entitlement"] != with_signals["evidence_entitlement"] or base["source_authority"] != with_signals["source_authority"]:
            raise ModeError("declaring a bridge changed evidence entitlement or source authority")
    results["BRIDGE_NON_AUTHORITY"] = {"passed": True, "checks": bridge_checks}

    geometry_checks = 0
    for maturity in MATURITY:
        low_uncertainty_signals = _base_witness_signals(
            requested_maturity=maturity,
            evidence_entitlement=maturity,
            safety_criticality=0.95,
            evidentiary_strength=0.2,
            uncertainty=0.1,
            source_authority=0.6,
            source_authority_class="scholarly",
        )
        high_uncertainty_signals = dict(low_uncertainty_signals, uncertainty=0.9)
        low_case = {"id": "W-GEO-LOW", "primary_mode": "ENGINEERING", "secondary_modes": [], "signals": low_uncertainty_signals}
        high_case = {"id": "W-GEO-HIGH", "primary_mode": "ENGINEERING", "secondary_modes": [], "signals": high_uncertainty_signals}
        low = classify_case(low_case)
        high = classify_case(high_case)
        geometry_checks += 2
        if low != {"status": "MODE_VIOLATION", "reason_codes": ["HIGH_SAFETY_LOW_EVIDENCE_UNCERTAINTY_REQUIRED"]}:
            raise ModeError("geometry witness failed to reject high-safety/low-evidence confidence")
        if high != {"status": "MODE_OK", "reason_codes": ["UNCERTAINTY_PRESERVED"]}:
            raise ModeError("geometry witness failed to preserve uncertainty")
        if low_uncertainty_signals["evidence_entitlement"] != high_uncertainty_signals["evidence_entitlement"]:
            raise ModeError("geometry coordinates changed evidence entitlement")
    results["GEOMETRY_NON_EVIDENTIARY"] = {"passed": True, "checks": geometry_checks}

    legal_case = {
        "id": "W-HIGH-LEGAL",
        "primary_mode": "LEGAL",
        "secondary_modes": [],
        "signals": _base_witness_signals(
            binding_claim=True,
            claim_scope="legal_rule",
            jurisdiction_resolved=False,
            source_authority_class="primary_legal_authority",
        ),
    }
    medical_case = {
        "id": "W-HIGH-MEDICAL",
        "primary_mode": "MEDICAL",
        "secondary_modes": [],
        "signals": _base_witness_signals(
            claim_scope="clinical_guidance",
            freshness_required=True,
            freshness_verified=False,
            source_authority_class="current_clinical_guideline",
        ),
    }
    legal_observed = classify_case(legal_case)
    medical_observed = classify_case(medical_case)
    if legal_observed != {"status": "MODE_UNRESOLVED", "reason_codes": ["JURISDICTION_UNRESOLVED"]}:
        raise ModeError("unresolved high-stakes witness failed for legal jurisdiction")
    if medical_observed != {"status": "MODE_UNRESOLVED", "reason_codes": ["FRESHNESS_OR_VERSION_UNRESOLVED"]}:
        raise ModeError("unresolved high-stakes witness failed for medical currentness")
    results["UNRESOLVED_HIGH_STAKES_FAIL_CLOSED"] = {"passed": True, "checks": 2}

    conflict_checks = 0
    for primary_mode, claim_scope, binding in (
        ("LEGAL", "legal_rule", True),
        ("MEDICAL", "clinical_guidance", False),
    ):
        conflict_case = {
            "id": f"W-CONFLICT-{primary_mode}",
            "primary_mode": primary_mode,
            "secondary_modes": [],
            "signals": _base_witness_signals(
                binding_claim=binding,
                claim_scope=claim_scope,
                unresolved_primary_conflict=True,
                source_authority_class=("primary_legal_authority" if primary_mode == "LEGAL" else "current_clinical_guideline"),
            ),
        }
        observed = classify_case(conflict_case)
        conflict_checks += 1
        if observed != {"status": "MODE_UNRESOLVED", "reason_codes": ["PRIMARY_CONFLICT"]}:
            raise ModeError(f"conflict preservation witness failed for {primary_mode}")
    results["CONFLICT_PRESERVATION"] = {"passed": True, "checks": conflict_checks}

    passed = set(results) == FORMAL_INVARIANTS and all(row.get("passed") is True for row in results.values())
    if not passed:
        raise ModeError("formal witness did not execute and pass every declared invariant")
    return {
        "type": "qsol-mode-separation-witness-report",
        "schema_version": "1.0.0",
        "classification": "internal_policy_consistency_not_external_truth",
        "invariants": sorted(FORMAL_INVARIANTS),
        "invariant_results": {key: results[key] for key in sorted(results)},
        "finite_claim_strength_pairs": len(MATURITY) ** 2,
        "accepted_pairs": accepted_pairs,
        "rejected_pairs": rejected_pairs,
        "noninterference_checks": bridge_checks + geometry_checks,
        "high_stakes_checks": 2,
        "conflict_checks": conflict_checks,
        "passed": True,
    }


def _delivery_contract_text(index: dict[str, Any]) -> str:
    return "\n".join([
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
    ])


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
    oracle_data = _canonical_jsonl(sparse["rows"])
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
    files = {
        "policy-index.json": canonical_json_bytes(index),
        "mode-confusion-1.jsonl": _canonical_jsonl(cases),
        "oracle.jsonl": oracle_data,
        "reference-report.json": canonical_json_bytes(reference_report),
        "calibration-contract.json": canonical_json_bytes(calibration),
        "delivery-contract.txt": _delivery_contract_text(index).encode("utf-8"),
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
    _require_schema_valid(root, MODE_BUNDLE_SCHEMA, manifest, "mode bundle manifest")

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
    try:
        children = list(bundle.iterdir())
    except OSError as exc:
        return [ModeFinding("mode.bundle_read", str(bundle), str(exc))]
    if any(child.is_symlink() for child in children):
        findings.append(ModeFinding("mode.symlink", str(bundle), "mode bundle may not contain symlinks"))
    names = {child.name for child in children if child.is_file() and not child.is_symlink()}
    if names != EXPECTED_BUNDLE_FILES:
        findings.append(ModeFinding("mode.file_set", str(bundle), "mode bundle file set mismatch"))
        return findings
    try:
        manifest = _load_json(bundle / "manifest.json")
        _require_schema_valid(root, MODE_BUNDLE_SCHEMA, manifest, "mode bundle manifest")
    except ModeError as exc:
        return [ModeFinding("mode.manifest", "manifest.json", str(exc))]
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
            try:
                if (bundle / name).read_bytes() != (expected_dir / name).read_bytes():
                    findings.append(ModeFinding("mode.deterministic_mismatch", name, "file differs from deterministic rebuild"))
            except OSError as exc:
                findings.append(ModeFinding("mode.file_read", name, str(exc)))
        if manifest != expected:
            findings.append(ModeFinding("mode.manifest_mismatch", "manifest.json", "manifest differs from deterministic rebuild"))
    return findings


def _validate_bundle_for_scoring(bundle: Path) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    root = Path(__file__).resolve().parents[1]
    candidate = bundle if bundle.is_absolute() else root / bundle
    findings = validate_mode_bundle(root, candidate)
    if findings:
        first = findings[0]
        raise ModeError(f"mode bundle validation failed [{first.code}] {first.path}: {first.message}")
    resolved = candidate.resolve()
    manifest = _load_json(resolved / "manifest.json")
    cases = _load_jsonl(resolved / "mode-confusion-1.jsonl")
    return root, manifest, cases


def build_oracle_run(bundle: Path) -> dict[str, Any]:
    root, manifest, cases = _validate_bundle_for_scoring(bundle)
    responses = []
    for case in cases:
        observed = classify_case(case, variant="sparse_24d")
        responses.append({"case_id": case["id"], "status": observed["status"], "reason_codes": observed["reason_codes"]})
    run = {
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
    _require_schema_valid(root, MODE_RUN_SCHEMA, run, "mode oracle run")
    return run


def score_mode_run(bundle: Path, run: dict[str, Any]) -> dict[str, Any]:
    root, manifest, cases = _validate_bundle_for_scoring(bundle)
    _require_schema_valid(root, MODE_RUN_SCHEMA, run, "mode run")
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

    model = run["model"]
    response_map: dict[str, dict[str, Any]] = {}
    for row in run["responses"]:
        if row["case_id"] in response_map:
            raise ModeError(f"duplicate response case id: {row['case_id']}")
        response_map[row["case_id"]] = row
    if set(response_map) != set(expected):
        missing = sorted(set(expected) - set(response_map))
        extra = sorted(set(response_map) - set(expected))
        raise ModeError(f"run case set mismatch missing={missing[:3]} extra={extra[:3]}")

    rows = []
    correct = 0
    reason_correct = 0
    by_category: dict[str, list[bool]] = defaultdict(list)
    false_ok = 0
    crossover_cases = 0
    crossover_correct = 0
    for case_id, case in expected.items():
        row = response_map[case_id]
        status = row["status"]
        observed_reasons = _observed_reason_codes(row)
        expected_status = case["expected"]["status"]
        expected_reasons = _expected_reason_codes(case)
        status_ok = status == expected_status
        reasons_ok = observed_reasons == expected_reasons
        ok = status_ok and reasons_ok
        correct += int(ok)
        reason_correct += int(reasons_ok)
        category = str(case["category"])
        by_category[category].append(ok)
        if status == "MODE_OK" and expected_status != "MODE_OK":
            false_ok += 1
        if case.get("secondary_modes"):
            crossover_cases += 1
            crossover_correct += int(ok)
        rows.append({
            "case_id": case_id,
            "category": category,
            "expected_status": expected_status,
            "observed_status": status,
            "expected_reason_codes": expected_reasons,
            "observed_reason_codes": observed_reasons,
            "status_correct": status_ok,
            "reason_codes_correct": reasons_ok,
            "correct": ok,
        })

    total = len(cases)
    report = {
        "type": "qsol-mode-confusion-report",
        "schema_version": "1.0.0",
        "suite": MODE_CONFUSION_VERSION,
        "execution_kind": run["execution_kind"],
        "empirical_model_result": run["execution_kind"] == "empirical_consumer",
        "condition": run["condition"],
        "model": model,
        "mode_bundle_sha256": manifest["bundle_sha256"],
        "mode_policy_sha256": manifest["mode_policy_sha256"],
        "source_commit": manifest["substrate"]["source_commit"],
        "substrate_sha256": manifest["substrate"]["substrate_sha256"],
        "counts": {
            "correct": correct,
            "reason_codes_correct": reason_correct,
            "total": total,
            "false_mode_ok": false_ok,
            "cross_mode_correct": crossover_correct,
            "cross_mode_total": crossover_cases,
        },
        "metrics": {
            "accuracy": round(correct / total, 6),
            "reason_code_accuracy": round(reason_correct / total, 6),
            "false_mode_ok_rate": round(false_ok / total, 6),
            "cross_mode_accuracy": round(crossover_correct / crossover_cases, 6) if crossover_cases else None,
            "category_accuracy": {
                key: round(sum(values) / len(values), 6)
                for key, values in sorted(by_category.items())
            },
        },
        "rows": rows,
    }
    _require_schema_valid(root, MODE_REPORT_SCHEMA, report, "mode report")
    return report


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


def calibrate_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    for report in reports:
        if report.get("empirical_model_result") is True and report.get("execution_kind") != "empirical_consumer":
            raise ModeError("non-empirical execution kind may not claim empirical model evidence")
    empirical = [
        report
        for report in reports
        if report.get("execution_kind") == "empirical_consumer"
        and report.get("empirical_model_result") is True
    ]
    if not empirical:
        raise ModeError("calibration requires empirical consumer reports; oracle reports are refused")
    identities = {
        (r.get("mode_bundle_sha256"), r.get("mode_policy_sha256"), r.get("source_commit"), r.get("substrate_sha256"))
        for r in empirical
    }
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
