from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import canonical_json_bytes
from toolless_core import _identity

PROJECTION_SPEC_VERSION = "1.0.0"
PROJECTION_MANIFEST_SCHEMA = "schema/projection-manifest.schema.json"
COMPATIBILITY_SCHEMA = "schema/model-projection-compatibility.schema.json"
EXPECTED_FILES = {"epistemic-prefix.txt", "projection-recipes.json", "delivery-matrix.json", "manifest.json"}

EPISTEMIC_RULES = (
    "UNKNOWN != FALSE",
    "INFERENCE != FACT",
    "SATIRE != BIOGRAPHY",
    "REPLAY != EMPIRICAL_VALIDATION",
    "FORMALIZATION != PHYSICAL_TRUTH",
    "PRESERVE_PROVENANCE",
    "RESOLVE_CANONICAL_IDS_BEFORE_ALIASES",
)

YEAH_NAH_EXPERIMENTAL_RULES = (
    "SURFACE_MEANING != NECESSARILY_INTENDED_MEANING",
    "SARCASM = INFERRED UNLESS SPEAKER_CONFIRMED",
    "UNCERTAIN != SARCASTIC",
    "BANTER != HOSTILITY",
    "UNDERSTATEMENT != LOW_SEVERITY",
    "CONTEXT > TOKEN_POLARITY",
)

COMPATIBILITY_FIELDS = (
    "projection_kind",
    "model_id",
    "model_revision",
    "architecture",
    "tokenizer_id",
    "tokenizer_sha256",
    "context_length",
    "hidden_size",
    "num_hidden_layers",
    "num_attention_heads",
    "kv_layout_version",
)


class ProjectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectionFinding:
    code: str
    path: str
    message: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"cannot load JSON {path}: {exc}") from exc


def _safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise ProjectionError("refusing to replace symlinked projection output")
    output = output.resolve()
    if output == root or output in root.parents:
        raise ProjectionError("projection output may not replace or contain repository root")
    if root in output.parents and output != root / "dist" / "projections":
        raise ProjectionError("in-repository projection output is restricted to dist/projections")
    if output.exists() and not output.is_dir():
        raise ProjectionError("refusing to replace non-directory projection output")
    return root, output


def render_epistemic_prefix(identity: dict[str, Any]) -> str:
    lines = [
        "QSOL-SUBSTRATE/EPISTEMIC-PREFIX/1",
        f"SUBSTRATE_VERSION={identity['version']}",
        f"SNAPSHOT_DATE={identity['snapshot_date']}",
        f"SOURCE_COMMIT={identity['source_commit']}",
        f"SUBSTRATE_SHA256={identity['substrate_sha256']}",
        "CARRIER=INTERPRETATION_RULES_NOT_CANONICAL_FACTS",
        "CANONICAL_TRUTH_AUTHORITY=false",
        "",
        "[CORE_EPISTEMIC_RULES]",
        *EPISTEMIC_RULES,
        "",
        "[EXPERIMENTAL_PRAGMATIC_RULES_YEAH_NAH_1]",
        "These rules are an experimental interpretation probe contract, not biographical or cultural facts.",
        *YEAH_NAH_EXPERIMENTAL_RULES,
        "",
        "[FACTUAL_PAYLOAD_POLICY]",
        "Mutable identity/project/publication/chronology facts remain textual or retrieval-selected.",
        "Do not promote a latent/prefix state into an independent source of truth.",
        "If model compatibility changes, invalidate the model-specific projection and regenerate.",
        "",
    ]
    return "\n".join(lines)


def projection_recipes(identity: dict[str, Any]) -> dict[str, Any]:
    common = {
        "source_substrate_version": identity["version"],
        "source_commit": identity["source_commit"],
        "source_substrate_sha256": identity["substrate_sha256"],
        "canonical_truth_authority": False,
        "model_specific_execution_required": True,
        "compatibility_fields": list(COMPATIBILITY_FIELDS),
    }
    recipes = [
        dict(common, id="soft-prompt-prefix-tuning", carrier="trainable_prefix_embeddings", status="experimental_recipe", factual_payload_policy="epistemic_rules_only_recommended"),
        dict(common, id="prompt-tuned-virtual-tokens", carrier="trainable_virtual_tokens", status="experimental_recipe", factual_payload_policy="epistemic_rules_only_recommended"),
        dict(common, id="lora-epistemic-adapter", carrier="lora_adapter_weights", status="experimental_recipe", factual_payload_policy="epistemic_rules_only_recommended"),
        dict(common, id="prefilled-kv-cache", carrier="model_kv_cache", status="experimental_recipe", factual_payload_policy="epistemic_prefix_plus_explicit_factual_text"),
        dict(common, id="reusable-prefix-state", carrier="model_prefix_state", status="experimental_recipe", factual_payload_policy="epistemic_prefix_plus_explicit_factual_text"),
        dict(common, id="hybrid-epistemic-prefix-factual-text", carrier="epistemic_prefix_plus_vector_or_text_context", status="reference_delivery_recipe", factual_payload_policy="mutable_facts_must_remain_inspectable_text"),
    ]
    return {
        "type": "qsol-model-projection-recipes",
        "schema_version": "1.0.0",
        "projection_spec_version": PROJECTION_SPEC_VERSION,
        "source": identity,
        "recipes": recipes,
        "non_claim": "This file defines reproducible experiment recipes and compatibility requirements; it does not claim that model-specific weights or KV states were trained in repository CI.",
    }


def delivery_matrix(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "qsol-projection-delivery-matrix",
        "schema_version": "1.0.0",
        "source": {
            "version": identity["version"],
            "source_commit": identity["source_commit"],
            "substrate_sha256": identity["substrate_sha256"],
        },
        "epistemic_rules": list(EPISTEMIC_RULES),
        "yeah_nah_1_rules": list(YEAH_NAH_EXPERIMENTAL_RULES),
        "modes": [
            {
                "id": "textual",
                "epistemic_carrier": "plain_text",
                "factual_carrier": "fixed_toolless_or_retrieved_text",
                "model_specific": False,
            },
            {
                "id": "epistemic-prefix",
                "epistemic_carrier": "model_specific_prefix_recipe",
                "factual_carrier": "none_for_rule_preservation_probe",
                "model_specific": True,
            },
            {
                "id": "hybrid",
                "epistemic_carrier": "model_specific_prefix_recipe",
                "factual_carrier": "vector_selected_or_fixed_text",
                "model_specific": True,
            },
        ],
        "phase7_measurement_required": True,
        "interpretation": "Phase 6 fixes the delivery conditions and rule payloads; Phase 7 measures whether models actually preserve them better in one carrier than another.",
    }


def compatibility_fingerprint(manifest: dict[str, Any]) -> str:
    critical = {field: manifest.get(field) for field in COMPATIBILITY_FIELDS}
    return _sha256(canonical_json_bytes(critical))


def compatibility_mismatches(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for field in COMPATIBILITY_FIELDS:
        if expected.get(field) != actual.get(field):
            mismatches.append(field)
    return mismatches


def validate_compatibility_manifest(root: Path, manifest: dict[str, Any], schema_path: str = COMPATIBILITY_SCHEMA) -> list[str]:
    try:
        schema = _load_json(root / schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        return ["/".join(str(part) for part in error.absolute_path) or "$" for error in validator.iter_errors(manifest)]
    except Exception as exc:
        return [f"schema:{exc}"]


def build_projection_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _safe_output(root, output)
    identity, _ = _identity(root, source_commit)
    prefix_data = render_epistemic_prefix(identity).encode("utf-8")
    recipes_data = canonical_json_bytes(projection_recipes(identity))
    matrix_data = canonical_json_bytes(delivery_matrix(identity))
    files = {
        "epistemic-prefix.txt": prefix_data,
        "projection-recipes.json": recipes_data,
        "delivery-matrix.json": matrix_data,
    }
    file_rows = [
        {"path": path, "sha256": _sha256(data), "bytes": len(data)}
        for path, data in sorted(files.items())
    ]
    material = "".join(f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n" for row in file_rows).encode("utf-8")
    manifest = {
        "type": "qsol-model-projection-manifest",
        "schema_version": "1.0.0",
        "projection_spec_version": PROJECTION_SPEC_VERSION,
        "substrate": identity,
        "artifact_class": "model_specific_projection_experiment_contract",
        "canonical_truth_authority": False,
        "model_specific_binary_artifacts_in_ci": False,
        "epistemic_prefix_sha256": _sha256(prefix_data),
        "compatibility": {
            "schema": COMPATIBILITY_SCHEMA,
            "required_exact_match_fields": list(COMPATIBILITY_FIELDS),
            "invalidate_on_any_mismatch": True,
            "tokenizer_or_architecture_change_requires_regeneration": True,
        },
        "recipes": [
            "soft-prompt-prefix-tuning",
            "prompt-tuned-virtual-tokens",
            "lora-epistemic-adapter",
            "prefilled-kv-cache",
            "reusable-prefix-state",
            "hybrid-epistemic-prefix-factual-text",
        ],
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


def validate_projection_bundle(root: Path, bundle: Path, schema_path: str = PROJECTION_MANIFEST_SCHEMA) -> list[ProjectionFinding]:
    root = root.resolve()
    if bundle.is_symlink():
        return [ProjectionFinding("projection.bundle", str(bundle), "bundle may not be a symlink")]
    bundle = bundle.resolve()
    findings: list[ProjectionFinding] = []
    if not bundle.is_dir():
        return [ProjectionFinding("projection.bundle", str(bundle), "bundle must be a real directory")]
    try:
        manifest = _load_json(bundle / "manifest.json")
    except ProjectionError as exc:
        return [ProjectionFinding("projection.manifest", "manifest.json", str(exc))]
    if not isinstance(manifest, dict):
        return [ProjectionFinding("projection.manifest", "manifest.json", "manifest must be an object")]
    try:
        schema = _load_json(root / schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in validator.iter_errors(manifest):
            pointer = "/".join(str(part) for part in error.absolute_path)
            findings.append(ProjectionFinding("projection.schema", f"manifest.json/{pointer}" if pointer else "manifest.json", "projection manifest schema violation"))
    except Exception as exc:
        return [ProjectionFinding("projection.schema_definition", schema_path, str(exc))]

    actual_names: set[str] = set()
    try:
        for child in bundle.iterdir():
            if child.is_symlink():
                findings.append(ProjectionFinding("projection.symlink", child.name, "bundle entries may not be symlinks"))
                continue
            if not child.is_file():
                findings.append(ProjectionFinding("projection.extra_entry", child.name, "bundle entries must be declared regular files"))
                continue
            actual_names.add(child.name)
    except OSError as exc:
        findings.append(ProjectionFinding("projection.bundle_read", str(bundle), str(exc)))
        return findings
    if actual_names != EXPECTED_FILES:
        findings.append(ProjectionFinding("projection.file_set", str(bundle), "bundle file set must match deterministic Phase 6 layout"))

    substrate = manifest.get("substrate", {})
    source_commit = substrate.get("source_commit") if isinstance(substrate, dict) else None
    if not isinstance(source_commit, str):
        findings.append(ProjectionFinding("projection.source_commit", "manifest.json/substrate/source_commit", "missing source commit"))
        return findings

    with tempfile.TemporaryDirectory() as temp:
        expected_dir = Path(temp) / "projections"
        try:
            expected = build_projection_bundle(root, expected_dir, source_commit)
        except Exception as exc:
            findings.append(ProjectionFinding("projection.recompile", "canonical_payload", str(exc)))
            return findings
        for name in sorted(EXPECTED_FILES):
            actual_path = bundle / name
            expected_path = expected_dir / name
            if not actual_path.is_file() or actual_path.is_symlink():
                continue
            try:
                if actual_path.read_bytes() != expected_path.read_bytes():
                    findings.append(ProjectionFinding("projection.deterministic_mismatch", name, "file differs from deterministic canonical rebuild"))
            except OSError as exc:
                findings.append(ProjectionFinding("projection.file_read", name, str(exc)))
        if manifest != expected:
            findings.append(ProjectionFinding("projection.manifest_mismatch", "manifest.json", "manifest differs from deterministic canonical rebuild"))
    return findings
