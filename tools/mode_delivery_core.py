from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from adapter_core import ADAPTER_DEFINITIONS
from mode_core import ModeError, _load_json as _load_mode_json, validate_mode_bundle
from substrate_integrity import canonical_json_bytes
from toolless_core import (
    PROFILE_SPECS,
    _canonical_items,
    _closure,
    _dependencies,
    _identity,
    _item_sort_key,
    _render_capsule,
    portable_token_count,
)
from vector_core import validate_vector_bundle
from projection_core import validate_projection_bundle
from adapter_core import validate_adapter_bundle
from toolless_core import validate_toolless_bundle

MODE_DELIVERY_SPEC_VERSION = "1.0.0"
EXPECTED_TOP_LEVEL = {"toolless", "vector", "latent", "hybrid", "manifest.json"}


class ModeDeliveryError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModeDeliveryError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ModeDeliveryError(f"JSON object required: {path}")
    return value


def _safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise ModeDeliveryError("refusing symlinked mode-delivery output")
    output = output.resolve()
    if output == root or output in root.parents:
        raise ModeDeliveryError("mode-delivery output may not replace or contain repository root")
    if root in output.parents and output != root / "dist" / "mode-delivery":
        raise ModeDeliveryError("in-repository output is restricted to dist/mode-delivery")
    if output.exists() and not output.is_dir():
        raise ModeDeliveryError("refusing non-directory mode-delivery output")
    return root, output


def _component_identity(manifest: dict[str, Any], *, bundle_key: str) -> tuple[str, str, str]:
    substrate = manifest.get("substrate")
    if not isinstance(substrate, dict):
        raise ModeDeliveryError("component manifest is missing substrate identity")
    source_commit = substrate.get("source_commit")
    substrate_sha = substrate.get("substrate_sha256")
    bundle_sha = manifest.get(bundle_key)
    if not all(isinstance(value, str) and value for value in (source_commit, substrate_sha, bundle_sha)):
        raise ModeDeliveryError("component manifest has incomplete identity")
    return source_commit, substrate_sha, bundle_sha


def _require_same_identity(label: str, manifest: dict[str, Any], source_commit: str, substrate_sha: str, *, bundle_key: str) -> str:
    component_commit, component_sha, bundle_sha = _component_identity(manifest, bundle_key=bundle_key)
    if component_commit != source_commit:
        raise ModeDeliveryError(f"{label} source_commit does not match mode bundle")
    if component_sha != substrate_sha:
        raise ModeDeliveryError(f"{label} substrate_sha256 does not match mode bundle")
    return bundle_sha


def _mode_prefix(mode_bundle: Path) -> str:
    text = (mode_bundle / "delivery-contract.txt").read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    return text


def _select_mode_capsule(profile: dict[str, Any], identity: dict[str, Any], items: list[Any], prefix: str) -> tuple[set[str], str]:
    lookup = {item.item_id: item for item in items}
    dependencies = {item.item_id: _dependencies(item, lookup) for item in items}
    ordered = sorted(items, key=_item_sort_key)
    selected: set[str] = set()

    if profile["name"] == "FULL":
        selected = set(lookup)
        body = _render_capsule(profile, identity, selected, items)
        text = prefix + body
        count = portable_token_count(text)
        if count > profile["budget"]:
            raise ModeDeliveryError(
                f"FULL mode-aware capsule requires {count} portable tokens, above budget {profile['budget']}"
            )
        return selected, text

    for candidate in ordered:
        if candidate.item_id in selected:
            continue
        addition = _closure(candidate.item_id, lookup, dependencies, selected)
        trial = selected | addition
        body = _render_capsule(profile, identity, trial, items)
        text = prefix + body
        if portable_token_count(text) <= profile["budget"]:
            selected = trial
    body = _render_capsule(profile, identity, selected, items)
    text = prefix + body
    if portable_token_count(text) > profile["budget"]:
        raise ModeDeliveryError(f"{profile['name']} mode-aware capsule exceeded deterministic token budget")
    return selected, text


def _verify_adapter_embedding(root: Path, mode_policy: dict[str, Any]) -> None:
    canonical_policy = canonical_json_bytes(mode_policy).decode("utf-8").rstrip("\n")
    for definition in ADAPTER_DEFINITIONS:
        for relative in definition["knowledge_files"]:
            path = root / "dist/adapters" / relative
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ModeDeliveryError(f"cannot read adapter knowledge file {relative}: {exc}") from exc
            if canonical_policy not in text:
                raise ModeDeliveryError(
                    f"adapter {definition['id']} does not embed ai/mode-delivery.json; "
                    "ensure it is listed in normative_machine_files"
                )


def build_mode_delivery_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _safe_output(root, output)

    component_checks = (
        ("modes", validate_mode_bundle, root / "dist/modes"),
        ("adapters", validate_adapter_bundle, root / "dist/adapters"),
        ("toolless", validate_toolless_bundle, root / "dist/toolless"),
        ("vectors", validate_vector_bundle, root / "dist/vectors"),
        ("projections", validate_projection_bundle, root / "dist/projections"),
    )
    for label, validator, bundle in component_checks:
        findings = validator(root, bundle)
        if findings:
            first = findings[0]
            raise ModeDeliveryError(f"{label} prerequisite bundle is invalid: {getattr(first, 'code', first)}")

    mode_manifest = _load_json(root / "dist/modes/manifest.json")
    mode_substrate = mode_manifest.get("substrate")
    if not isinstance(mode_substrate, dict):
        raise ModeDeliveryError("mode manifest lacks substrate identity")
    if mode_substrate.get("source_commit") != source_commit:
        raise ModeDeliveryError("declared source_commit does not match mode bundle")
    substrate_sha = mode_substrate.get("substrate_sha256")
    if not isinstance(substrate_sha, str):
        raise ModeDeliveryError("mode bundle lacks substrate fingerprint")

    adapters = _load_json(root / "dist/adapters/manifest.json")
    toolless = _load_json(root / "dist/toolless/manifest.json")
    vectors = _load_json(root / "dist/vectors/manifest.json")
    projections = _load_json(root / "dist/projections/manifest.json")
    adapter_sha = _require_same_identity("adapters", adapters, source_commit, substrate_sha, bundle_key="adapter_bundle_sha256")
    toolless_sha = _require_same_identity("toolless", toolless, source_commit, substrate_sha, bundle_key="bundle_sha256")
    vector_sha = _require_same_identity("vectors", vectors, source_commit, substrate_sha, bundle_key="bundle_sha256")
    projection_sha = _require_same_identity("projections", projections, source_commit, substrate_sha, bundle_key="bundle_sha256")

    mode_policy = _load_json(root / "ai/mode-delivery.json")
    if mode_policy.get("policy_version") != mode_manifest.get("policy_version"):
        raise ModeDeliveryError("source mode-delivery policy version disagrees with mode bundle")
    _verify_adapter_embedding(root, mode_policy)

    prefix = _mode_prefix(root / "dist/modes")
    identity, source_manifest = _identity(root, source_commit)
    items = _canonical_items(root, source_manifest)

    generated: dict[str, bytes] = {}
    profile_rows: list[dict[str, Any]] = []
    for profile in PROFILE_SPECS:
        selected, text = _select_mode_capsule(profile, identity, items, prefix)
        filename = f"QSOL-SUBSTRATE-{profile['name']}-MODE.txt"
        relative = f"toolless/{filename}"
        data = text.encode("utf-8")
        generated[relative] = data
        profile_rows.append(
            {
                "name": profile["name"],
                "path": relative,
                "token_budget": profile["budget"],
                "portable_tokens": portable_token_count(text),
                "included_items": len(selected),
                "omitted_items": len(items) - len(selected),
                "sha256": _sha256(data),
            }
        )

    vector_prefix = (
        prefix
        + "VECTOR_DELIVERY=prepend_this_block_to_every_vector-selected_context\n"
        + "VECTOR_FACTS_REMAIN_INSPECTABLE_TEXT=true\n"
    )
    generated["vector/mode-prefix.txt"] = vector_prefix.encode("utf-8")

    epistemic_prefix = (root / "dist/projections/epistemic-prefix.txt").read_text(encoding="utf-8")
    latent = (
        prefix
        + "LATENT_POLICY=stable_mode_guards_only\n"
        + "MUTABLE_PRIMARY_AUTHORITY_OR_FRESHNESS_FACTS_IN_LATENT_STATE=forbidden\n\n"
        + epistemic_prefix
    )
    generated["latent/epistemic-mode-prefix.txt"] = latent.encode("utf-8")
    generated["hybrid/mode-prefix.txt"] = (
        prefix
        + "HYBRID_DELIVERY=mode_guard_prefix_plus_vector_or_fixed_inspectable_factual_text\n"
    ).encode("utf-8")

    file_rows = [
        {"path": path, "sha256": _sha256(data), "bytes": len(data)}
        for path, data in sorted(generated.items())
    ]
    material = b"".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n".encode("utf-8")
        for row in file_rows
    )
    manifest = {
        "type": "qsol-mode-delivery-binding-manifest",
        "schema_version": "1.0.0",
        "mode_delivery_spec_version": MODE_DELIVERY_SPEC_VERSION,
        "substrate": {
            "version": mode_substrate["version"],
            "snapshot_date": mode_substrate["snapshot_date"],
            "source_commit": source_commit,
            "substrate_sha256": substrate_sha,
        },
        "mode_policy": {
            "policy_version": mode_manifest["policy_version"],
            "mode_policy_sha256": mode_manifest["mode_policy_sha256"],
            "mode_bundle_sha256": mode_manifest["bundle_sha256"],
        },
        "bound_components": {
            "adapters": adapter_sha,
            "toolless": toolless_sha,
            "vectors": vector_sha,
            "projections": projection_sha,
        },
        "adapter_mode_policy_embedded": True,
        "tool_less_profiles": profile_rows,
        "vector_delivery": "prepend vector/mode-prefix.txt to every retrieved context",
        "latent_delivery": "use latent/epistemic-mode-prefix.txt; mutable authority/freshness facts remain textual",
        "hybrid_delivery": "use hybrid/mode-prefix.txt plus inspectable factual context",
        "files": file_rows,
        "bundle_sha256": _sha256(material),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir: Path | None = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        for relative, data in generated.items():
            path = temp_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (temp_dir / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        if output.exists():
            shutil.rmtree(output)
        temp_dir.replace(output)
        temp_dir = None
        return manifest
    finally:
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def validate_mode_delivery_bundle(root: Path, bundle: Path) -> list[str]:
    root = root.resolve()
    candidate = bundle if bundle.is_absolute() else root / bundle
    findings: list[str] = []
    try:
        if candidate.is_symlink():
            raise ModeDeliveryError("mode-delivery bundle may not be a symlink")
        bundle = candidate.resolve()
        manifest = _load_json(bundle / "manifest.json")
        source_commit = manifest.get("substrate", {}).get("source_commit")
        if not isinstance(source_commit, str):
            raise ModeDeliveryError("mode-delivery manifest missing source_commit")
        with tempfile.TemporaryDirectory() as temp:
            expected_dir = Path(temp) / "mode-delivery"
            expected = build_mode_delivery_bundle(root, expected_dir, source_commit)
            expected_paths = {
                path.relative_to(expected_dir).as_posix()
                for path in expected_dir.rglob("*")
                if path.is_file()
            }
            actual_paths = {
                path.relative_to(bundle).as_posix()
                for path in bundle.rglob("*")
                if path.is_file()
            }
            if actual_paths != expected_paths:
                raise ModeDeliveryError("mode-delivery file set mismatch")
            for relative in sorted(expected_paths):
                if (bundle / relative).read_bytes() != (expected_dir / relative).read_bytes():
                    raise ModeDeliveryError(f"deterministic mode-delivery mismatch: {relative}")
            if manifest != expected:
                raise ModeDeliveryError("mode-delivery manifest mismatch")
    except (OSError, KeyError, TypeError, ModeError, ModeDeliveryError) as exc:
        findings.append(str(exc))
    return findings
