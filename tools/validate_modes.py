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
EXPECTED_STATUSES = {
    "ESTABLISHED", "CONSENSUS", "SUPPORTED", "CONTESTED", "PRELIMINARY", "THEORETICAL", "PROPOSED",
    "SPECULATIVE", "UNKNOWN", "HYPOTHETICAL", "COUNTERFACTUAL", "FICTIONAL", "SATIRICAL",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the noncanonical QSOL-SUBSTRATE mode policy layer.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []

    required = {
        "contract": root / "ai/mode-contract.json",
        "modes": root / "modes/index.json",
        "activities": root / "modes/activities.json",
        "policy": root / "modes/source-policy.json",
        "terms": root / "modes/terminology-namespaces.json",
        "geometry": root / "geometry/mode-space-v1.json",
        "bridges": root / "bridges/index.json",
        "schema": root / "schema/substrate-modes.schema.json",
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
    modes = values["modes"]
    activities = values["activities"]
    policy = values["policy"]
    terms = values["terms"]
    geometry = values["geometry"]
    bridges = values["bridges"]
    schema = values["schema"]

    try:
        Draft202012Validator.check_schema(schema)
        schema_errors = list(Draft202012Validator(schema).iter_errors(modes))
        require(not schema_errors, f"modes/index.json violates schema: {schema_errors[0].message if schema_errors else ''}", errors)
    except Exception as exc:
        errors.append(f"schema/substrate-modes.schema.json invalid: {exc}")

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
    statuses = set(policy.get("source_axes", {}).get("epistemic_status", [])) if isinstance(policy, dict) else set()
    require(statuses == EXPECTED_STATUSES, f"epistemic status set mismatch: {sorted(statuses ^ EXPECTED_STATUSES)}", errors)
    require(policy.get("core_invariant") == "CLAIM_STRENGTH <= EVIDENCE_ENTITLEMENT", "source policy core invariant changed", errors)

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
    preferred = set(clinical.get("preferred_authority_classes", [])) if isinstance(clinical, dict) else set()
    require(clinical.get("preprints_normative") is False, "MEDICAL clinical preprints must remain non-normative", errors)
    require({"regulator", "current_clinical_guideline", "systematic_evidence"}.issubset(preferred), "MEDICAL clinical authority hierarchy incomplete", errors)

    axes = geometry.get("axes", []) if isinstance(geometry, dict) else []
    axis_ids = [axis.get("id") for axis in axes if isinstance(axis, dict)]
    axis_indexes = [axis.get("index") for axis in axes if isinstance(axis, dict)]
    require(geometry.get("dimension_count") == 24, "geometry dimension_count must be 24", errors)
    require(len(axes) == 24, "geometry must define exactly 24 axes", errors)
    require(len(axis_ids) == len(set(axis_ids)), "geometry axis IDs must be unique", errors)
    require(axis_indexes == list(range(1, 25)), "geometry axis indexes must be 1..24 in order", errors)
    require(geometry.get("classification") == "validation_geometry_not_evidence", "geometry must be labelled non-evidentiary", errors)
    require("coordinates_do_not_prove_truth" in geometry.get("validation_principles", []), "geometry truth boundary missing", errors)

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

    print(f"VALID MODES domains={len(mode_ids)} activities={len(activity_ids)} axes={len(axes)} bridges={len(bridge_items)} ambiguous_terms={len(ambiguous)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
