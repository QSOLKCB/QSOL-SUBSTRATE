#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


class ExportError(RuntimeError):
    pass


CANONICAL_JSON_NAME = "qsol-canonical-json-v1"
CANONICAL_JSONL_NAME = "qsol-canonical-jsonl-v1"
CANONICAL_RECORD_TYPES = {
    "identity",
    "organization",
    "project",
    "repository",
    "publication",
    "research_topic",
    "term",
    "event",
    "relationship",
    "source",
    "claim",
    "adapter",
    "probe",
}
CANONICAL_EPISTEMIC_STATES = {
    "known",
    "retrieved",
    "inferred",
    "unknown",
    "conflict",
    "fiction",
}
NORMATIVE_IMMUTABLE_PAYLOAD_FILES = {"sources/index.json"}

# Writable record collections are an explicit part of the public export boundary.
# The exporter must never infer writability merely because an arbitrary JSON
# pointer happens to resolve to a list.
ALLOWED_TARGET_COLLECTIONS: dict[str, dict[str, set[str]]] = {
    "identity/public.json": {"/records": {"identity", "organization"}},
    "context/public.json": {"/claims": {"claim"}},
    "terminology/index.json": {"/records": {"term"}},
    "projects/index.json": {"/records": {"project"}},
    "publications/index.json": {"/records": {"publication"}},
    "relationships/graph.json": {
        "/nodes": {"research_topic"},
        "/edges": {"relationship"},
    },
    "chronology/current.jsonl": {"": {"event"}},
}


def _json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ExportError(f"cannot canonicalise JSON value: {exc}") from exc
    return (text + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExportError(f"required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExportError(f"invalid JSON in {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ExportError(f"required file not found: {path}") from exc
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ExportError(f"invalid JSONL in {path}:{lineno}: {exc}") from exc
    return rows


def _write_canonical(path: Path, value: Any, kind: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "json":
        path.write_bytes(_json_bytes(value))
    elif kind == "jsonl":
        path.write_bytes(b"".join(_json_bytes(row) for row in value))
    else:
        raise ExportError(f"unsupported canonical output kind: {kind}")


def _kind_for_path(path: str) -> str:
    if path.endswith(".jsonl"):
        return "jsonl"
    if path.endswith(".json"):
        return "json"
    raise ExportError(f"canonical payload file must be .json or .jsonl: {path}")


def _decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _pointer_parts(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise ExportError(f"JSON pointer must be empty or start with '/': {pointer!r}")
    return [_decode_pointer_token(p) for p in pointer[1:].split("/")]


def _pointer_get(value: Any, pointer: str) -> Any:
    current = value
    for token in _pointer_parts(pointer):
        if isinstance(current, list):
            try:
                index = int(token)
            except ValueError as exc:
                raise ExportError(f"list pointer segment must be an integer: {pointer!r}") from exc
            if index < 0 or index >= len(current):
                raise ExportError(f"JSON pointer index out of range: {pointer!r}")
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                raise ExportError(f"JSON pointer not found: {pointer!r}")
            current = current[token]
        else:
            raise ExportError(f"JSON pointer traverses a scalar: {pointer!r}")
    return current


def _pointer_set(obj: dict[str, Any], pointer: str, value: Any) -> None:
    parts = _pointer_parts(pointer)
    if not parts:
        raise ExportError("field target pointer may not replace the entire record")
    current: dict[str, Any] = obj
    for token in parts[:-1]:
        child = current.get(token)
        if child is None:
            child = {}
            current[token] = child
        if not isinstance(child, dict):
            raise ExportError(f"target pointer collides with non-object field: {pointer!r}")
        current = child
    current[parts[-1]] = value


def _safe_relative(path_text: str, label: str) -> Path:
    path = Path(path_text)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ExportError(f"{label} must be a safe relative path: {path_text!r}")
    return path


def _within(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _paths_overlap(a: Path, b: Path) -> bool:
    a = a.resolve()
    b = b.resolve()
    return _within(a, b) or _within(b, a)


def _compile_patterns(
    items: list[dict[str, str]], label: str
) -> list[tuple[str, re.Pattern[str]]]:
    if not isinstance(items, list):
        raise ExportError(f"{label} patterns must be an array")
    compiled = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"id", "regex"}:
            raise ExportError(f"{label} pattern entries require exactly id and regex")
        try:
            compiled.append((item["id"], re.compile(item["regex"])))
        except (TypeError, re.error) as exc:
            raise ExportError(f"invalid regex for {label}:{item.get('id')}: {exc}") from exc
    return compiled


def _scan_text(
    text: str,
    *,
    secret_patterns: list[tuple[str, re.Pattern[str]]],
    private_patterns: list[tuple[str, re.Pattern[str]]],
    label: str,
) -> None:
    for pattern_id, regex in secret_patterns:
        if regex.search(text):
            raise ExportError(f"secret pattern {pattern_id!r} detected in {label}")
    for pattern_id, regex in private_patterns:
        if regex.search(text):
            raise ExportError(f"private-reference pattern {pattern_id!r} detected in {label}")


def _scan_value(
    value: Any,
    *,
    secret_patterns: list[tuple[str, re.Pattern[str]]],
    private_patterns: list[tuple[str, re.Pattern[str]]],
    forbidden_field_names: set[str],
    label: str,
) -> None:
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                if key_text.lower() in forbidden_field_names:
                    raise ExportError(
                        f"forbidden field name {key!r} encountered in {label}{path}"
                    )
                # JSON object keys are data too. Applying the same patterns to
                # keys prevents a credential/private reference from bypassing
                # scanning by being used as a map key instead of a value.
                _scan_text(
                    key_text,
                    secret_patterns=secret_patterns,
                    private_patterns=private_patterns,
                    label=f"{label}{path}/<key>",
                )
                walk(item, path + "/" + key_text)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                walk(item, path + f"/{idx}")
        elif isinstance(node, str):
            _scan_text(
                node,
                secret_patterns=secret_patterns,
                private_patterns=private_patterns,
                label=f"{label}{path}",
            )

    walk(value, "")


def _validate_source_root(source_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    source_contract = policy.get("source_contract")
    if not isinstance(source_contract, dict):
        raise ExportError("policy.source_contract must be an object")
    manifest_rel = _safe_relative(
        source_contract.get("manifest_path", ""), "source manifest path"
    )
    manifest_path = (source_root / manifest_rel).resolve()
    if not _within(source_root, manifest_path):
        raise ExportError("source manifest escapes source root")
    manifest = _load_json(manifest_path)
    pointer = source_contract.get("protocol_pointer")
    expected = source_contract.get("protocol_equals")
    if not isinstance(pointer, str) or not isinstance(expected, str):
        raise ExportError("source contract protocol_pointer/protocol_equals must be strings")
    actual = _pointer_get(manifest, pointer)
    if actual != expected:
        raise ExportError(
            f"source protocol mismatch: expected {expected!r}, got {actual!r}"
        )
    return manifest


def _load_payload(substrate_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _load_json(substrate_root / "ai/manifest.json")
    payload_files = manifest.get("canonical_payload_files")
    if (
        not isinstance(payload_files, list)
        or not payload_files
        or not all(isinstance(p, str) for p in payload_files)
    ):
        raise ExportError("ai/manifest.json must define non-empty canonical_payload_files")
    payload: dict[str, Any] = {}
    for rel in payload_files:
        safe = _safe_relative(rel, "canonical payload path")
        source = (substrate_root / safe).resolve()
        if not _within(substrate_root, source):
            raise ExportError(f"canonical payload path escapes repository: {rel}")
        kind = _kind_for_path(rel)
        payload[rel] = _load_json(source) if kind == "json" else _load_jsonl(source)
    return manifest, payload


def _public_source_ids(payload: dict[str, Any]) -> set[str]:
    registry = payload.get("sources/index.json")
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        raise ExportError("sources/index.json is required and must contain a sources array")
    return {
        record["id"]
        for record in registry["sources"]
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }


def _find_source_record(
    source_doc: Any, source_spec: dict[str, Any]
) -> tuple[Any, str]:
    if "pointer" in source_spec:
        if "collection_pointer" in source_spec or "match" in source_spec:
            raise ExportError(
                "source spec may use pointer or collection_pointer+match, not both"
            )
        pointer = source_spec["pointer"]
        if not isinstance(pointer, str):
            raise ExportError("source.pointer must be a string")
        return _pointer_get(source_doc, pointer), pointer

    collection_pointer = source_spec.get("collection_pointer")
    match = source_spec.get("match")
    if not isinstance(collection_pointer, str) or not isinstance(match, dict):
        raise ExportError("source spec requires pointer or collection_pointer plus match")
    collection = _pointer_get(source_doc, collection_pointer)
    if not isinstance(collection, list):
        raise ExportError("source.collection_pointer must resolve to a list")
    if set(match) != {"pointer", "equals"} or not isinstance(match["pointer"], str):
        raise ExportError("source.match requires exactly pointer and equals")
    matches = []
    for item in collection:
        try:
            candidate = _pointer_get(item, match["pointer"])
        except ExportError:
            continue
        if candidate == match["equals"]:
            matches.append(item)
    if len(matches) != 1:
        raise ExportError(
            f"source match for {match['pointer']}={match['equals']!r} returned {len(matches)} records; expected exactly one"
        )
    return matches[0], f"{collection_pointer}[{match['pointer']}={match['equals']!r}]"


def _validate_field_rule(rule: dict[str, Any], entry_id: str) -> None:
    if rule.get("visibility") != "public":
        raise ExportError(f"{entry_id}: every exported field requires visibility='public'")
    target = rule.get("to")
    if not isinstance(target, str):
        raise ExportError(f"{entry_id}: field rule requires string 'to'")
    modes = [key for key in ("from", "value", "redact_from") if key in rule]
    if len(modes) != 1:
        raise ExportError(
            f"{entry_id}: field rule requires exactly one of from, value, redact_from"
        )
    if "from" in rule and not isinstance(rule["from"], str):
        raise ExportError(f"{entry_id}: field 'from' must be a JSON pointer")
    if "redact_from" in rule and not isinstance(rule["redact_from"], str):
        raise ExportError(f"{entry_id}: field 'redact_from' must be a JSON pointer")
    if "replacement" in rule and "redact_from" not in rule:
        raise ExportError(f"{entry_id}: replacement is valid only with redact_from")


def _forbidden_source_path(path: str, globs: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in globs)


def _source_has_symlink_component(source_root: Path, rel: Path) -> bool:
    current = source_root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _build_record(
    *,
    entry: dict[str, Any],
    source_record: Any,
    public_source_ids: set[str],
    secret_patterns: list[tuple[str, re.Pattern[str]]],
    private_patterns: list[tuple[str, re.Pattern[str]]],
    forbidden_field_names: set[str],
) -> tuple[dict[str, Any], int]:
    entry_id = entry["id"]
    if entry.get("visibility") != "public":
        raise ExportError(f"{entry_id}: directive visibility must be explicitly 'public'")

    record_spec = entry.get("record")
    if not isinstance(record_spec, dict):
        raise ExportError(f"{entry_id}: record must be an object")
    for key in ("id", "record_type", "epistemic_state", "public_source_refs", "fields"):
        if key not in record_spec:
            raise ExportError(f"{entry_id}: record.{key} is required")

    refs = record_spec["public_source_refs"]
    if not isinstance(refs, list) or not refs or not all(
        isinstance(ref, str) for ref in refs
    ):
        raise ExportError(f"{entry_id}: public_source_refs must be a non-empty string array")
    for ref in refs:
        if not ref.startswith("src:") or ref not in public_source_ids:
            raise ExportError(f"{entry_id}: unknown or non-public provenance ref: {ref!r}")

    record_id = record_spec["id"]
    record_type = record_spec["record_type"]
    epistemic_state = record_spec["epistemic_state"]
    if not all(
        isinstance(v, str) and v for v in (record_id, record_type, epistemic_state)
    ):
        raise ExportError(
            f"{entry_id}: record id/type/epistemic_state must be non-empty strings"
        )
    if record_type not in CANONICAL_RECORD_TYPES:
        raise ExportError(f"{entry_id}: unsupported record_type: {record_type!r}")
    if epistemic_state not in CANONICAL_EPISTEMIC_STATES:
        raise ExportError(
            f"{entry_id}: unsupported epistemic_state: {epistemic_state!r}"
        )

    fields = record_spec["fields"]
    if not isinstance(fields, list):
        raise ExportError(f"{entry_id}: record.fields must be an array")

    reserved_targets = {
        "/id",
        "/record_type",
        "/visibility",
        "/epistemic_state",
        "/source_refs",
    }
    output: dict[str, Any] = {
        "id": record_id,
        "record_type": record_type,
        "visibility": "public",
        "epistemic_state": epistemic_state,
        "source_refs": refs,
    }
    redactions = 0

    for rule in fields:
        if not isinstance(rule, dict):
            raise ExportError(f"{entry_id}: field rules must be objects")
        _validate_field_rule(rule, entry_id)
        target = rule["to"]
        if target in reserved_targets:
            raise ExportError(f"{entry_id}: {target} is reserved and generated by the exporter")

        if "from" in rule:
            raw = _pointer_get(source_record, rule["from"])
            _scan_value(
                raw,
                secret_patterns=secret_patterns,
                private_patterns=private_patterns,
                forbidden_field_names=forbidden_field_names,
                label=f"{entry_id}:selected{rule['from']}",
            )
            value = raw
        elif "value" in rule:
            value = rule["value"]
            _scan_value(
                value,
                secret_patterns=secret_patterns,
                private_patterns=private_patterns,
                forbidden_field_names=forbidden_field_names,
                label=f"{entry_id}:constant{target}",
            )
        else:
            raw = _pointer_get(source_record, rule["redact_from"])
            _scan_value(
                raw,
                secret_patterns=secret_patterns,
                private_patterns=[],
                forbidden_field_names=forbidden_field_names,
                label=f"{entry_id}:redacted-source{rule['redact_from']}",
            )
            value = rule.get("replacement", "[REDACTED]")
            redactions += 1

        _pointer_set(output, target, value)

    _scan_value(
        output,
        secret_patterns=secret_patterns,
        private_patterns=private_patterns,
        forbidden_field_names=forbidden_field_names,
        label=f"{entry_id}:output",
    )
    return output, redactions


def _validate_target_collection(
    entry: dict[str, Any], record: dict[str, Any], payload: dict[str, Any]
) -> tuple[str, str, bool]:
    target = entry.get("target")
    if not isinstance(target, dict):
        raise ExportError(f"{entry['id']}: target must be an object")
    target_path = target.get("path")
    collection_pointer = target.get("collection_pointer")
    allow_create = target.get("allow_create")
    if (
        not isinstance(target_path, str)
        or not isinstance(collection_pointer, str)
        or not isinstance(allow_create, bool)
    ):
        raise ExportError(
            f"{entry['id']}: target requires path, collection_pointer, and boolean allow_create"
        )
    if target_path not in payload:
        raise ExportError(
            f"{entry['id']}: target path is not a canonical payload file: {target_path}"
        )

    collections = ALLOWED_TARGET_COLLECTIONS.get(target_path)
    if collections is None or collection_pointer not in collections:
        raise ExportError(
            f"{entry['id']}: target collection is not an approved canonical record collection: {target_path}:{collection_pointer}"
        )
    if record["record_type"] not in collections[collection_pointer]:
        raise ExportError(
            f"{entry['id']}: record_type {record['record_type']!r} is not allowed in {target_path}:{collection_pointer}"
        )
    return target_path, collection_pointer, allow_create


def _apply_record(
    payload: dict[str, Any], entry: dict[str, Any], record: dict[str, Any]
) -> None:
    target_path, collection_pointer, allow_create = _validate_target_collection(
        entry, record, payload
    )
    collection = _pointer_get(payload[target_path], collection_pointer)
    if not isinstance(collection, list):
        raise ExportError(
            f"{entry['id']}: approved target collection does not resolve to an array"
        )

    record_id = record["id"]
    indexes = [
        idx
        for idx, item in enumerate(collection)
        if isinstance(item, dict) and item.get("id") == record_id
    ]
    if len(indexes) > 1:
        raise ExportError(
            f"{entry['id']}: target contains duplicate record id {record_id!r}"
        )
    if indexes:
        collection[indexes[0]] = record
    elif allow_create:
        collection.append(record)
    else:
        raise ExportError(
            f"{entry['id']}: target record {record_id!r} does not exist and allow_create=false"
        )

    sort_by = entry["target"].get("sort_by")
    if sort_by is not None:
        if not isinstance(sort_by, str):
            raise ExportError(f"{entry['id']}: target.sort_by must be a JSON pointer")
        try:
            collection.sort(key=lambda item: _pointer_get(item, sort_by))
        except TypeError as exc:
            raise ExportError(
                f"{entry['id']}: target.sort_by values are not mutually sortable"
            ) from exc


def _canonical_config_fingerprint(
    policy: dict[str, Any], include: dict[str, Any], exclude: dict[str, Any]
) -> str:
    return _sha256_bytes(
        _json_bytes({"policy": policy, "include": include, "exclude": exclude})
    )


def _build_public_manifest(
    *,
    output_root: Path,
    payload_files: list[str],
    config_fingerprint: str,
    source_protocol: str,
    applied_directives: list[str],
) -> dict[str, Any]:
    files = []
    for rel in sorted(payload_files):
        path = output_root / rel
        files.append(
            {"path": rel, "sha256": _sha256_file(path), "bytes": path.stat().st_size}
        )
    material = "".join(
        f"{item['path']}\0{item['sha256']}\0{item['bytes']}\n" for item in files
    ).encode("utf-8")
    return {
        "type": "qsol-substrate-export-manifest",
        "schema_version": "1.0.0",
        "export_policy": "explicit_allow_only",
        "source_protocol": source_protocol,
        "canonicalization": {
            "json": CANONICAL_JSON_NAME,
            "jsonl": CANONICAL_JSONL_NAME,
            "utf8": True,
            "trailing_newline": True,
        },
        "omission_semantics": "unavailable_not_false",
        "config_sha256": config_fingerprint,
        "applied_directives": applied_directives,
        "files": files,
        "bundle_sha256": _sha256_bytes(material),
    }


def _write_private_audit(
    *,
    path: Path,
    source_root: Path,
    directive_audit: list[dict[str, Any]],
    public_manifest: dict[str, Any],
) -> None:
    audit = {
        "type": "qsol-substrate-private-export-audit",
        "schema_version": "1.0.0",
        "source_root": str(source_root.resolve()),
        "directives": directive_audit,
        "public_bundle_sha256": public_manifest["bundle_sha256"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(audit))


def run_export(
    *,
    source_root: Path,
    substrate_root: Path,
    output_root: Path,
    policy_path: Path,
    include_path: Path,
    exclude_path: Path,
    audit_manifest: Path | None = None,
    allow_output_inside_repo: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    substrate_root = substrate_root.resolve()
    output_root = output_root.resolve()

    if not source_root.is_dir():
        raise ExportError(f"source root is not a directory: {source_root}")
    if not substrate_root.is_dir():
        raise ExportError(f"substrate root is not a directory: {substrate_root}")
    if source_root == substrate_root:
        raise ExportError("source root and substrate root must be different")

    # Destructive replacement is never allowed to overlap either input root in
    # either direction. Neither --force nor the legacy repository-output flag
    # can override this safety boundary.
    if _paths_overlap(source_root, output_root) or _paths_overlap(
        substrate_root, output_root
    ):
        raise ExportError(
            "export output must not overlap the private source root or public substrate root"
        )
    if allow_output_inside_repo:
        raise ExportError(
            "--allow-output-inside-repo is no longer permitted; output must be disjoint from both input roots"
        )

    if audit_manifest is not None:
        audit_manifest = audit_manifest.resolve()
        if _within(output_root, audit_manifest):
            raise ExportError(
                "private audit manifest may not be written inside the public export output"
            )

    policy = _load_json(policy_path)
    include = _load_json(include_path)
    exclude = _load_json(exclude_path)

    if policy.get("export_policy") != "explicit_allow_only":
        raise ExportError("policy export_policy must be explicit_allow_only")
    if include.get("default") != "deny":
        raise ExportError("include allowlist default must be deny")
    if exclude.get("default") != "deny_on_match":
        raise ExportError("exclude policy default must be deny_on_match")

    source_manifest = _validate_source_root(source_root, policy)
    substrate_manifest, payload = _load_payload(substrate_root)
    payload_files = substrate_manifest["canonical_payload_files"]
    public_source_ids = _public_source_ids(payload)

    immutable_cfg = policy.get("immutable_payload_files", [])
    if not isinstance(immutable_cfg, list) or not all(
        isinstance(x, str) for x in immutable_cfg
    ):
        raise ExportError("policy.immutable_payload_files must be a string array")
    immutable = set(immutable_cfg) | NORMATIVE_IMMUTABLE_PAYLOAD_FILES

    source_path_globs = exclude.get("forbidden_source_path_globs", [])
    if not isinstance(source_path_globs, list) or not all(
        isinstance(x, str) for x in source_path_globs
    ):
        raise ExportError("exclude.forbidden_source_path_globs must be a string array")
    forbidden_field_names = {
        str(x).lower() for x in exclude.get("forbidden_field_names", [])
    }
    secret_patterns = _compile_patterns(exclude.get("secret_patterns", []), "secret")
    private_patterns = _compile_patterns(
        exclude.get("private_reference_patterns", []), "private-reference"
    )

    entries = include.get("entries")
    if not isinstance(entries, list):
        raise ExportError("include.entries must be an array")

    manifest_rel = _safe_relative(
        policy.get("output_manifest", "export-manifest.json"), "output manifest"
    )
    manifest_rel_text = manifest_rel.as_posix()
    if manifest_rel_text in payload_files:
        raise ExportError(
            f"output manifest must not collide with canonical payload file: {manifest_rel_text}"
        )

    output_root.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=str(output_root.parent))
    )
    applied: list[str] = []
    directive_audit: list[dict[str, Any]] = []
    total_redactions = 0

    try:
        for rel in payload_files:
            _write_canonical(temp_root / rel, payload[rel], _kind_for_path(rel))

        for entry in entries:
            if not isinstance(entry, dict):
                raise ExportError("include entries must be objects")
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not entry_id:
                raise ExportError("every include entry requires a non-empty id")
            if entry.get("enabled") is not True:
                continue
            if entry.get("visibility") != "public":
                raise ExportError(
                    f"{entry_id}: enabled directive requires visibility='public'"
                )

            source_spec = entry.get("source")
            target_spec = entry.get("target")
            if not isinstance(source_spec, dict) or not isinstance(target_spec, dict):
                raise ExportError(f"{entry_id}: source and target must be objects")

            source_rel_text = source_spec.get("path")
            if not isinstance(source_rel_text, str):
                raise ExportError(f"{entry_id}: source.path must be a string")
            if _forbidden_source_path(source_rel_text, source_path_globs):
                raise ExportError(
                    f"{entry_id}: source path is forbidden by policy: {source_rel_text}"
                )
            source_rel = _safe_relative(source_rel_text, f"{entry_id}: source.path")
            if _source_has_symlink_component(source_root, source_rel):
                raise ExportError(f"{entry_id}: symlinked source paths are forbidden")
            source_path = (source_root / source_rel).resolve()
            if not _within(source_root, source_path):
                raise ExportError(f"{entry_id}: source path escapes source root")
            resolved_rel = source_path.relative_to(source_root).as_posix()
            if _forbidden_source_path(resolved_rel, source_path_globs):
                raise ExportError(
                    f"{entry_id}: resolved source path is forbidden by policy: {resolved_rel}"
                )
            if source_path.suffix != ".json":
                raise ExportError(
                    f"{entry_id}: Phase 2 directives currently require JSON source files"
                )

            target_path = target_spec.get("path")
            if not isinstance(target_path, str):
                raise ExportError(f"{entry_id}: target.path must be a string")
            if target_path in immutable:
                raise ExportError(
                    f"{entry_id}: target file is immutable under private export policy: {target_path}"
                )
            if target_path not in payload:
                raise ExportError(
                    f"{entry_id}: target is not a canonical payload file: {target_path}"
                )

            source_doc = _load_json(source_path)
            selected, selected_locator = _find_source_record(source_doc, source_spec)
            record, redactions = _build_record(
                entry=entry,
                source_record=selected,
                public_source_ids=public_source_ids,
                secret_patterns=secret_patterns,
                private_patterns=private_patterns,
                forbidden_field_names=forbidden_field_names,
            )
            _apply_record(payload, entry, record)
            _write_canonical(
                temp_root / target_path,
                payload[target_path],
                _kind_for_path(target_path),
            )
            applied.append(entry_id)
            total_redactions += redactions
            directive_audit.append(
                {
                    "id": entry_id,
                    "source_path": source_rel_text,
                    "source_locator": selected_locator,
                    "source_file_sha256": _sha256_file(source_path),
                    "target_path": target_path,
                    "output_record_id": record["id"],
                    "output_record_sha256": _sha256_bytes(_json_bytes(record)),
                    "redactions": redactions,
                }
            )

        for rel in payload_files:
            path = temp_root / rel
            parsed = (
                _load_json(path)
                if _kind_for_path(rel) == "json"
                else _load_jsonl(path)
            )
            _scan_value(
                parsed,
                secret_patterns=secret_patterns,
                private_patterns=private_patterns,
                forbidden_field_names=forbidden_field_names,
                label=f"output:{rel}",
            )

        config_fingerprint = _canonical_config_fingerprint(policy, include, exclude)
        source_protocol = _pointer_get(
            source_manifest, policy["source_contract"]["protocol_pointer"]
        )
        public_manifest = _build_public_manifest(
            output_root=temp_root,
            payload_files=payload_files,
            config_fingerprint=config_fingerprint,
            source_protocol=source_protocol,
            applied_directives=applied,
        )
        public_manifest["redaction_applied"] = bool(total_redactions)
        (temp_root / manifest_rel).parent.mkdir(parents=True, exist_ok=True)
        (temp_root / manifest_rel).write_bytes(_json_bytes(public_manifest))

        _scan_value(
            public_manifest,
            secret_patterns=secret_patterns,
            private_patterns=private_patterns,
            forbidden_field_names=forbidden_field_names,
            label="public-export-manifest",
        )

        if output_root.exists():
            if not force:
                raise ExportError(
                    f"output already exists; use --force to replace: {output_root}"
                )
            if output_root.is_dir():
                shutil.rmtree(output_root)
            else:
                output_root.unlink()
        os.replace(temp_root, output_root)
        temp_root = None

        if audit_manifest is not None:
            _write_private_audit(
                path=audit_manifest,
                source_root=source_root,
                directive_audit=directive_audit,
                public_manifest=public_manifest,
            )
        return public_manifest
    finally:
        if temp_root is not None and Path(temp_root).exists():
            shutil.rmtree(temp_root, ignore_errors=True)


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    repo_root = _default_repo_root()
    parser = argparse.ArgumentParser(
        description="Fail-closed explicit-allow exporter from QSOL-CONTEXT into a reviewable QSOL-SUBSTRATE bundle."
    )
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="Local checkout/root of private QSOL-CONTEXT.",
    )
    parser.add_argument(
        "--substrate-root",
        type=Path,
        default=repo_root,
        help="QSOL-SUBSTRATE repository root.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination directory for the reviewable public bundle; must be disjoint from both input roots.",
    )
    parser.add_argument(
        "--policy", type=Path, default=repo_root / "public_export/policy.json"
    )
    parser.add_argument(
        "--include", type=Path, default=repo_root / "public_export/include.json"
    )
    parser.add_argument(
        "--exclude", type=Path, default=repo_root / "public_export/exclude.json"
    )
    parser.add_argument(
        "--audit-manifest",
        type=Path,
        help="Optional PRIVATE audit manifest path; must be outside public output.",
    )
    parser.add_argument("--allow-output-inside-repo", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing disjoint output directory."
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        manifest = run_export(
            source_root=args.source_root,
            substrate_root=args.substrate_root,
            output_root=args.output,
            policy_path=args.policy,
            include_path=args.include,
            exclude_path=args.exclude,
            audit_manifest=args.audit_manifest,
            allow_output_inside_repo=args.allow_output_inside_repo,
            force=args.force,
        )
    except ExportError as exc:
        print(f"EXPORT REFUSED: {exc}", file=os.sys.stderr)
        return 2
    print(f"bundle_sha256={manifest['bundle_sha256']}")
    print(f"config_sha256={manifest['config_sha256']}")
    print(f"applied_directives={len(manifest['applied_directives'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
