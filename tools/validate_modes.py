#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

EXPECTED_MODES = {
    "FORMAL", "SCIENCE", "LIFE_SCIENCE", "MEDICAL", "ENGINEERING", "COMPUTING", "SECURITY",
    "LEGAL", "GOVERNANCE", "ECONOMICS", "BUSINESS", "SOCIAL_SCIENCE", "HISTORY", "PHILOSOPHY",
    "HUMANITIES", "EDUCATION", "ARTS_MEDIA", "ENVIRONMENT", "EVERYDAY",
}
EXPECTED_ACTIVITIES = {
    "RESEARCH", "DIAGNOSTIC", "DESIGN", "DECISION", "EDUCATIONAL", "FORENSIC", "HISTORICAL",
    "PREDICTIVE", "NORMATIVE", "CREATIVE",
}
EXPECTED_MATURITY_STATES = {
    "ESTABLISHED", "CONSENSUS", "SUPPORTED", "CONTESTED", "PRELIMINARY", "THEORETICAL", "PROPOSED",
    "SPECULATIVE", "UNKNOWN",
}
EXPECTED_SCENARIO_STATES = {"ACTUAL", "HYPOTHETICAL", "COUNTERFACTUAL"}
EXPECTED_REGISTER_STATES = {"LITERAL", "FICTIONAL", "SATIRICAL"}
EXPECTED_HARD_CONSTRAINTS = {
    "LEGAL_BINDING_AUTHORITY": "modes/source-policy.json#profiles.LEGAL",
    "MEDICAL_CLINICAL_GUIDANCE": "modes/source-policy.json#profiles.MEDICAL.clinical",
    "HIGH_SAFETY_LOW_EVIDENCE": "ai/mode-contract.json#geometry",
    "CROSS_DOMAIN_BRIDGE": "bridges/index.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_preferred_by_axis(node: Any, source_axes: dict[str, Any], label: str, errors: list[str]) -> None:
    if not isinstance(node, dict):
        return
    preferred = node.get("preferred_by_axis")
    if preferred is not None:
        require(isinstance(preferred, dict) and bool(preferred), f"{label}.preferred_by_axis must be a non-empty object", errors)
        if isinstance(preferred, dict):
            for axis, values in preferred.items():
                require(axis in source_axes, f"{label}.preferred_by_axis uses undeclared axis {axis!r}", errors)
                declared = source_axes.get(axis, [])
                require(isinstance(values, list) and bool(values), f"{label}.preferred_by_axis.{axis} must be a non-empty array", errors)
                if isinstance(values, list) and isinstance(declared, list):
                    unknown = sorted({value for value in values if value not in declared})
                    require(not unknown, f"{label}.preferred_by_axis.{axis} contains undeclared values: {unknown}", errors)
    require("preferred" not in node, f"{label} must not use untyped preferred source values", errors)
    require("preferred_authority_classes" not in node, f"{label} must use preferred_by_axis instead of preferred_authority_classes", errors)
    for key, value in node.items():
        if key != "preferred_by_axis" and isinstance(value, dict):
            validate_preferred_by_axis(value, source_axes, f"{label}.{key}", errors)


def validate_threshold_map(
    values: Any,
    *,
    label: str,
    axis_ids: set[str],
    minimum: float,
    maximum: float,
    errors: list[str],
    allow_selectors: bool,
) -> None:
    require(isinstance(values, dict) and bool(values), f"{label} must be a non-empty object", errors)
    if not isinstance(values, dict):
        return
    for key, value in values.items():
        if key.endswith("_min") or key.endswith("_max"):
            suffix = "_min" if key.endswith("_min") else "_max"
            axis = key[:-len(suffix)]
            require(axis in axis_ids, f"{label}.{key} references unknown geometry axis {axis!r}", errors)
            require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label}.{key} threshold must be numeric", errors)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                require(minimum <= float(value) <= maximum, f"{label}.{key} threshold must be inside geometry range", errors)
            continue
        if allow_selectors and key == "mode":
            require(value in EXPECTED_MODES, f"{label}.mode references unknown mode {value!r}", errors)
        elif allow_selectors and key == "claim_scope":
            continue
        elif allow_selectors and key == "binding_claim":
            require(isinstance(value, bool), f"{label}.binding_claim must be boolean", errors)
        elif key == "declared_bridge":
            require(isinstance(value, bool), f"{label}.declared_bridge must be boolean", errors)
        else:
            errors.append(f"{label}.{key} is not a declared selector or geometry threshold")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the noncanonical QSOL-SUBSTRATE mode policy layer.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    required = {
        "contract": root / "ai/mode-contract.json",
        "epistemic_contract": root / "ai/epistemic-contract.json",
        "modes": root / "modes/index.json",
        "activities": root / "modes/activities.json",
        "policy": root / "modes/source-policy.json",
        "terms": root / "modes/terminology-namespaces.json",
        "geometry": root / "geometry/mode-space-v1.json",
        "bridges": root / "bridges/index.json",
        "schema": root / "schema/substrate-modes.schema.json",
        "epistemic_schema": root / "schema/epistemic-contract.schema.json",
    }
    values: dict[str, Any] = {}
    for key, path in required.items():
        try:
            values[key] = load_json(path)
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: cannot load JSON: {exc}")

    if errors:
        for error in errors:
            print(f"MODE VALIDATION REFUSED: {error}", file=sys.stderr)
        return 1

    contract = values["contract"]
    epistemic_contract = values["epistemic_contract"]
    modes = values["modes"]
    activities = values["activities"]
    policy = values["policy"]
    terms = values["terms"]
    geometry = values["geometry"]
    bridges = values["bridges"]
    schema = values["schema"]
    epistemic_schema = values["epistemic_schema"]

    try:
        Draft202012Validator.check_schema(schema)
        schema_errors = list(Draft202012Validator(schema).iter_errors(modes))
        require(not schema_errors, f"modes/index.json violates schema: {schema_errors[0].message if schema_errors else ''}", errors)
    except Exception as exc:
        errors.append(f"schema/substrate-modes.schema.json invalid: {exc}")

    try:
        Draft202012Validator.check_schema(epistemic_schema)
        epistemic_errors = list(Draft202012Validator(epistemic_schema).iter_errors(epistemic_contract))
        require(not epistemic_errors, f"ai/epistemic-contract.json violates schema: {epistemic_errors[0].message if epistemic_errors else ''}", errors)
    except Exception as exc:
        errors.append(f"schema/epistemic-contract.schema.json invalid: {exc}")

    mode_items = modes.get("modes", []) if isinstance(modes, dict) else []
    mode_ids = [item.get("id") for item in mode_items if isinstance(item, dict)]
    require(set(mode_ids) == EXPECTED_MODES, f"domain mode set mismatch: {sorted(set(mode_ids) ^ EXPECTED_MODES)}", errors)
    require(len(mode_ids) == len(set(mode_ids)), "duplicate domain mode IDs", errors)

    activity_items = activities.get("activities", []) if isinstance(activities, dict) else []
    activity_ids = [item.get("id") for item in activity_items if isinstance(item, dict)]
    require(set(activity_ids) == EXPECTED_ACTIVITIES, f"activity mode set mismatch: {sorted(set(activity_ids) ^ EXPECTED_ACTIVITIES)}", errors)
    require(len(activity_ids) == len(set(activity_ids)), "duplicate activity mode IDs", errors)

    profiles = policy.get("profiles", {}) if isinstance(policy, dict) else {}
    require(set(profiles) == EXPECTED_MODES, f"source-policy profiles must match mode set: {sorted(set(profiles) ^ EXPECTED_MODES)}", errors)
    source_axes = policy.get("source_axes", {}) if isinstance(policy, dict) else {}
    require(isinstance(source_axes, dict), "source_axes must be an object", errors)
    if not isinstance(source_axes, dict):
        source_axes = {}
    maturity = set(source_axes.get("claim_maturity", []))
    scenarios = set(source_axes.get("scenario_status", []))
    registers = set(source_axes.get("register", []))
    require(maturity == EXPECTED_MATURITY_STATES, f"claim maturity set mismatch: {sorted(maturity ^ EXPECTED_MATURITY_STATES)}", errors)
    require(scenarios == EXPECTED_SCENARIO_STATES, f"scenario status set mismatch: {sorted(scenarios ^ EXPECTED_SCENARIO_STATES)}", errors)
    require(registers == EXPECTED_REGISTER_STATES, f"register set mismatch: {sorted(registers ^ EXPECTED_REGISTER_STATES)}", errors)
    require("FICTIONAL" not in maturity and "SATIRICAL" not in maturity, "fiction/satire must not occupy claim maturity axis", errors)
    require(set(epistemic_contract.get("claim_maturity_states", {})) == EXPECTED_MATURITY_STATES, "epistemic contract claim maturity states disagree with source policy", errors)
    require(set(epistemic_contract.get("scenario_states", {})) == EXPECTED_SCENARIO_STATES, "epistemic contract scenario states disagree with source policy", errors)
    require(set(epistemic_contract.get("register_states", {})) == EXPECTED_REGISTER_STATES, "epistemic contract register states disagree with source policy", errors)
    require(policy.get("core_invariant") == "CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT", "source policy core invariant changed", errors)
    validate_preferred_by_axis(profiles, source_axes, "profiles", errors)

    doi_policy = policy.get("repository_doi_policy", {}) if isinstance(policy, dict) else {}
    entitles = set(doi_policy.get("entitles", [])) if isinstance(doi_policy, dict) else set()
    does_not_entitle = set(doi_policy.get("does_not_entitle", [])) if isinstance(doi_policy, dict) else set()
    defaults = set(doi_policy.get("default_claim_statuses_when_no_stronger_evidence_exists", [])) if isinstance(doi_policy, dict) else set()
    require("artifact_identity" in entitles, "repository DOI policy must entitle artifact identity", errors)
    require({"peer_review", "established_truth", "binding_legal_authority"}.issubset(does_not_entitle), "repository DOI policy must deny peer review, established truth, and binding legal authority", errors)
    require(defaults == {"THEORETICAL", "PROPOSED", "SPECULATIVE", "UNKNOWN"}, "repository DOI default statuses changed", errors)

    legal = profiles.get("LEGAL", {}) if isinstance(profiles, dict) else {}
    binding = legal.get("binding_claim", {}) if isinstance(legal, dict) else {}
    require(binding.get("required_authority_classes") == ["primary_legal_authority"], "LEGAL binding claims must require primary_legal_authority", errors)
    require(binding.get("secondary_authority_permitted_as_final_support") is False, "LEGAL secondary authority must not be final support for binding claims", errors)
    require(binding.get("jurisdiction_must_be_resolved_when_material") is True, "LEGAL jurisdiction resolution guard missing", errors)

    medical = profiles.get("MEDICAL", {}) if isinstance(profiles, dict) else {}
    clinical = medical.get("clinical", {}) if isinstance(medical, dict) else {}
    preferred_authority = set(clinical.get("preferred_by_axis", {}).get("authority_class", [])) if isinstance(clinical, dict) else set()
    require(clinical.get("preprints_normative") is False, "MEDICAL clinical preprints must remain non-normative", errors)
    require({"regulator", "current_clinical_guideline", "systematic_evidence"}.issubset(preferred_authority), "MEDICAL clinical authority hierarchy incomplete", errors)

    axes = geometry.get("axes", []) if isinstance(geometry, dict) else []
    axis_ids_list = [axis.get("id") for axis in axes if isinstance(axis, dict)]
    axis_ids = {axis for axis in axis_ids_list if isinstance(axis, str)}
    axis_indexes = [axis.get("index") for axis in axes if isinstance(axis, dict)]
    require(geometry.get("dimension_count") == 24, "geometry dimension_count must be 24", errors)
    require(len(axes) == 24, "geometry must define exactly 24 axes", errors)
    require(len(axis_ids_list) == len(set(axis_ids_list)), "geometry axis IDs must be unique", errors)
    require(axis_indexes == list(range(1, 25)), "geometry axis indexes must be 1..24 in order", errors)
    require(geometry.get("classification") == "validation_geometry_not_evidence", "geometry must be labelled non-evidentiary", errors)
    require("coordinates_do_not_prove_truth" in geometry.get("validation_principles", []), "geometry truth boundary missing", errors)

    range_spec = geometry.get("range", {}) if isinstance(geometry, dict) else {}
    range_min = range_spec.get("min") if isinstance(range_spec, dict) else None
    range_max = range_spec.get("max") if isinstance(range_spec, dict) else None
    require(isinstance(range_min, (int, float)) and not isinstance(range_min, bool), "geometry range.min must be numeric", errors)
    require(isinstance(range_max, (int, float)) and not isinstance(range_max, bool), "geometry range.max must be numeric", errors)
    minimum = float(range_min) if isinstance(range_min, (int, float)) and not isinstance(range_min, bool) else 0.0
    maximum = float(range_max) if isinstance(range_max, (int, float)) and not isinstance(range_max, bool) else 1.0
    require(minimum < maximum, "geometry range must have min < max", errors)

    constraints = geometry.get("hard_constraints", []) if isinstance(geometry, dict) else []
    constraint_ids = [item.get("id") for item in constraints if isinstance(item, dict)]
    require(set(constraint_ids) == set(EXPECTED_HARD_CONSTRAINTS), f"hard constraint set mismatch: {sorted(set(constraint_ids) ^ set(EXPECTED_HARD_CONSTRAINTS))}", errors)
    require(len(constraint_ids) == len(set(constraint_ids)), "duplicate hard constraint IDs", errors)
    claim_scopes = set(source_axes.get("claim_scope", []))
    for constraint in constraints:
        if not isinstance(constraint, dict):
            errors.append("hard constraint must be an object")
            continue
        cid = constraint.get("id")
        label = f"hard_constraints[{cid}]"
        require(isinstance(constraint.get("meaning"), str) and bool(constraint.get("meaning")), f"{label}.meaning is required", errors)
        expected_ref = EXPECTED_HARD_CONSTRAINTS.get(cid)
        require(constraint.get("policy_reference") == expected_ref, f"{label}.policy_reference must equal {expected_ref!r}", errors)
        if isinstance(expected_ref, str):
            rel = expected_ref.split("#", 1)[0]
            require((root / rel).is_file(), f"{label}.policy_reference target {rel!r} does not exist", errors)
        when = constraint.get("when")
        require_map = constraint.get("require")
        validate_threshold_map(when, label=f"{label}.when", axis_ids=axis_ids, minimum=minimum, maximum=maximum, errors=errors, allow_selectors=True)
        validate_threshold_map(require_map, label=f"{label}.require", axis_ids=axis_ids, minimum=minimum, maximum=maximum, errors=errors, allow_selectors=False)
        if isinstance(when, dict) and "claim_scope" in when:
            require(when.get("claim_scope") in claim_scopes, f"{label}.when.claim_scope is undeclared", errors)

    bridge_items = bridges.get("bridges", []) if isinstance(bridges, dict) else []
    bridge_ids = [bridge.get("id") for bridge in bridge_items if isinstance(bridge, dict)]
    require(len(bridge_ids) == len(set(bridge_ids)), "duplicate bridge IDs", errors)
    for bridge in bridge_items:
        if not isinstance(bridge, dict):
            errors.append("bridge must be an object")
            continue
        require(bridge.get("from") in EXPECTED_MODES, f"bridge {bridge.get('id')} has unknown source mode", errors)
        require(bridge.get("to") in EXPECTED_MODES, f"bridge {bridge.get('id')} has unknown target mode", errors)
        require(bool(bridge.get("non_equivalences")), f"bridge {bridge.get('id')} must declare non-equivalences", errors)

    ambiguous = terms.get("ambiguous_terms", []) if isinstance(terms, dict) else []
    for item in ambiguous:
        if not isinstance(item, dict):
            errors.append("terminology entry must be an object")
            continue
        candidates = item.get("candidates", [])
        require(len(candidates) >= 2, f"ambiguous term {item.get('term')} must have at least two candidates", errors)
        for candidate in candidates:
            namespace = candidate.split(":", 1)[0] if isinstance(candidate, str) and ":" in candidate else None
            require(namespace in EXPECTED_MODES, f"term {item.get('term')} uses unknown namespace {namespace}", errors)

    require(contract.get("core_invariant") == policy.get("core_invariant"), "mode contract and source policy invariant disagree", errors)
    require(contract.get("geometry", {}).get("dimensions") == 24, "mode contract geometry dimension mismatch", errors)
    require(contract.get("geometry", {}).get("not_a_truth_engine") is True, "mode contract must deny geometry-as-truth", errors)
    require(contract.get("source_policy", {}).get("legal_binding_claims_require_primary_legal_authority") is True, "mode contract legal guard missing", errors)
    require(contract.get("source_policy", {}).get("medical_preprints_are_non_normative_for_clinical_guidance") is True, "mode contract medical guard missing", errors)

    if errors:
        print(f"MODE VALIDATION REFUSED: {len(errors)} finding(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"VALID MODES domains={len(mode_ids)} activities={len(activity_ids)} axes={len(axes)} constraints={len(constraints)} bridges={len(bridge_items)} ambiguous_terms={len(ambiguous)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
