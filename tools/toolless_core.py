from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import build_fingerprint, canonical_json_bytes

CAPSULE_SPEC_VERSION = "1.0.0"
CAPSULE_MANIFEST_SCHEMA = "schema/toolless-manifest.schema.json"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PORTABLE_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
CANONICAL_ID_RE = re.compile(r"^(?:person|org|project|publication|term|topic|claim):")

PROFILE_SPECS: tuple[dict[str, Any], ...] = (
    {"name": "MICRO", "budget": 8192, "filename": "QSOL-SUBSTRATE-MICRO.txt", "redundant_guards": True},
    {"name": "STANDARD", "budget": 24576, "filename": "QSOL-SUBSTRATE-STANDARD.txt", "redundant_guards": False},
    {"name": "FULL", "budget": 131072, "filename": "QSOL-SUBSTRATE-FULL.txt", "redundant_guards": False},
)
PROFILE_NAMES = tuple(item["name"] for item in PROFILE_SPECS)

CORE_GUARDS = (
    "UNKNOWN != FALSE",
    "INFERENCE != FACT",
    "SATIRE != BIOGRAPHY",
    "FORMALIZATION != PHYSICAL_TRUTH",
)

COLLECTION_KEYS = {"sources", "records", "claims", "nodes", "edges"}
SECTION_ORDER = {
    "wrapper": 0,
    "identity": 1,
    "organization": 1,
    "term": 2,
    "claim": 3,
    "project": 4,
    "publication": 5,
    "research_topic": 6,
    "relationship": 7,
    "event": 8,
    "source": 9,
}


class CapsuleError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapsuleFinding:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class CapsuleItem:
    item_id: str
    kind: str
    source_path: str
    payload: dict[str, Any]
    priority: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(path: str) -> str:
    value = Path(path)
    if value.is_absolute() or ".." in value.parts or path in {"", "."}:
        raise CapsuleError(f"unsafe relative path: {path!r}")
    return value.as_posix()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapsuleError(f"required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapsuleError(f"invalid JSON in {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CapsuleError(f"required file not found: {path}") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CapsuleError(f"invalid JSONL in {path}:{line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise CapsuleError(f"JSONL record must be an object: {path}:{line_no}")
        rows.append(row)
    return rows


def portable_token_count(text: str) -> int:
    """Model-independent deterministic token accounting.

    qsol-portable-token-v1 normalizes text with NFKC, splits it into Unicode word
    runs and single non-whitespace punctuation/symbols, then charges each word run
    ceil(UTF-8 bytes / 4) portable tokens and each punctuation/symbol one token.
    This is a reproducible budgeting contract, not a claim about any model's
    tokenizer.
    """
    normalized = unicodedata.normalize("NFKC", text)
    total = 0
    for match in PORTABLE_TOKEN_RE.finditer(normalized):
        token = match.group(0)
        if re.fullmatch(r"\w+", token, re.UNICODE):
            total += max(1, math.ceil(len(token.encode("utf-8")) / 4))
        else:
            total += 1
    return total


def _priority(kind: str, source_path: str, item_id: str) -> int:
    if kind in {"identity", "organization", "term"}:
        return 0
    if kind == "wrapper" and source_path in {"identity/public.json", "terminology/index.json", "context/public.json"}:
        return 0
    if kind in {"claim", "project", "publication", "research_topic"}:
        return 1
    if kind == "wrapper" and source_path in {"projects/index.json", "publications/index.json"}:
        return 1
    if kind in {"relationship", "event"}:
        return 2
    if kind == "wrapper":
        return 2
    if kind == "source":
        return 3
    return 3


def _wrapper_payload(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key not in COLLECTION_KEYS}


def _record_kind(record: dict[str, Any], fallback: str) -> str:
    value = record.get("record_type")
    return value if isinstance(value, str) and value else fallback


def _canonical_items(root: Path, manifest: dict[str, Any]) -> list[CapsuleItem]:
    payload_files = manifest.get("canonical_payload_files")
    if not isinstance(payload_files, list) or not payload_files or not all(isinstance(v, str) for v in payload_files):
        raise CapsuleError("manifest canonical_payload_files must be a non-empty string array")

    items: list[CapsuleItem] = []
    seen: set[str] = set()

    def add(item_id: str, kind: str, source_path: str, payload: dict[str, Any]) -> None:
        if not item_id:
            raise CapsuleError(f"canonical item in {source_path} has no stable identity")
        if item_id in seen:
            raise CapsuleError(f"duplicate canonical item identity: {item_id}")
        seen.add(item_id)
        items.append(CapsuleItem(item_id, kind, source_path, payload, _priority(kind, source_path, item_id)))

    for raw_rel in payload_files:
        rel = _safe_relative(raw_rel)
        path = root / rel
        if rel.endswith(".jsonl"):
            for index, row in enumerate(_load_jsonl(path)):
                item_id = row.get("id")
                if not isinstance(item_id, str) or not item_id:
                    item_id = f"event:{rel}:{index:06d}"
                add(item_id, _record_kind(row, "event"), rel, row)
            continue

        document = _load_json(path)
        if not isinstance(document, dict):
            raise CapsuleError(f"canonical JSON payload must be an object: {rel}")

        wrapper = _wrapper_payload(document)
        if wrapper:
            add(f"wrapper:{rel}", "wrapper", rel, wrapper)

        collection_map = (
            ("sources", "source"),
            ("records", "record"),
            ("claims", "claim"),
            ("nodes", "research_topic"),
            ("edges", "relationship"),
        )
        for key, fallback in collection_map:
            values = document.get(key, [])
            if values is None:
                continue
            if not isinstance(values, list):
                raise CapsuleError(f"canonical collection {rel}/{key} must be an array")
            for index, record in enumerate(values):
                if not isinstance(record, dict):
                    raise CapsuleError(f"canonical collection item {rel}/{key}/{index} must be an object")
                item_id = record.get("id")
                if not isinstance(item_id, str) or not item_id:
                    raise CapsuleError(f"canonical record {rel}/{key}/{index} has no id")
                add(item_id, _record_kind(record, fallback), rel, record)

    return items


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _walk_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_strings(nested)


def _dependencies(item: CapsuleItem, lookup: dict[str, CapsuleItem]) -> set[str]:
    deps: set[str] = set()
    payload = item.payload
    source_refs = payload.get("source_refs")
    if isinstance(source_refs, list):
        for ref in source_refs:
            if isinstance(ref, str) and ref in lookup:
                deps.add(ref)
    if item.kind == "relationship":
        for key in ("source", "target"):
            value = payload.get(key)
            if isinstance(value, str) and value in lookup:
                deps.add(value)
    for text in _walk_strings(payload):
        if CANONICAL_ID_RE.match(text) and text in lookup and text != item.item_id:
            deps.add(text)
    return deps


def _closure(seed: str, lookup: dict[str, CapsuleItem], dependencies: dict[str, set[str]], selected: set[str]) -> set[str]:
    pending = [seed]
    result: set[str] = set()
    while pending:
        item_id = pending.pop()
        if item_id in selected or item_id in result:
            continue
        if item_id not in lookup:
            raise CapsuleError(f"dependency cannot be resolved: {item_id}")
        result.add(item_id)
        pending.extend(sorted(dependencies[item_id], reverse=True))
    return result


def _item_sort_key(item: CapsuleItem) -> tuple[int, int, str, str]:
    return (item.priority, SECTION_ORDER.get(item.kind, 99), item.source_path, item.item_id)


def _boundary_guards(item: CapsuleItem) -> tuple[str, ...]:
    if item.kind != "project":
        return ()
    tags = item.payload.get("tags")
    normalized = {str(tag).casefold() for tag in tags} if isinstance(tags, list) else set()
    guards: list[str] = []
    if "satire" in normalized:
        guards.append("SATIRE != BIOGRAPHY")
    if normalized.intersection({"formalization", "formal-assurance", "lean4", "formal-protocol"}):
        guards.append("FORMALIZATION != PHYSICAL_TRUTH")
    if normalized.intersection({"ai-observation", "transcript", "model-evaluation"}):
        guards.append("OBSERVED_OR_ARCHIVED_MODEL_OUTPUT != GENERAL_MODEL_IDENTITY")
    return tuple(guards)


def _line_for_item(item: CapsuleItem) -> str:
    payload = canonical_json_bytes(item.payload).decode("utf-8").rstrip("\n")
    return f"ITEM\t{item.kind}\t{item.source_path}\t{payload}"


def _render_capsule(
    profile: dict[str, Any],
    identity: dict[str, Any],
    selected_ids: set[str],
    all_items: list[CapsuleItem],
) -> str:
    lookup = {item.item_id: item for item in all_items}
    selected = sorted((lookup[item_id] for item_id in selected_ids), key=_item_sort_key)
    omitted = len(all_items) - len(selected)
    profile_name = profile["name"]
    lines = [
        "QSOL-SUBSTRATE/TOOLLESS/1",
        f"PROFILE={profile_name}",
        "NO_TOOLS=true",
        "TOOLS_AVAILABLE=false",
        f"CAPSULE_SPEC_VERSION={CAPSULE_SPEC_VERSION}",
        f"SUBSTRATE_VERSION={identity['version']}",
        f"SNAPSHOT_DATE={identity['snapshot_date']}",
        f"SOURCE_COMMIT={identity['source_commit']}",
        f"SUBSTRATE_SHA256={identity['substrate_sha256']}",
        "TOKENIZER=qsol-portable-token-v1",
        f"TOKEN_BUDGET={profile['budget']}",
        f"INCLUDED_ITEMS={len(selected)}",
        f"OMITTED_ITEMS={omitted}",
        f"TRUNCATED={'true' if omitted else 'false'}",
        "OMISSION_MEANS=UNAVAILABLE_NOT_FALSE",
        "FRESHNESS=FROZEN_AT_SNAPSHOT_DATE",
        "",
        "[COLD_BOOT]",
        "This file is the complete QSOL public substrate available in this run.",
        "You have no browsing, retrieval, filesystem, repository, or external tool access.",
        "Do not claim that you checked live state, opened a repository, searched the web, or loaded anything outside this capsule.",
        "If a question requires post-snapshot current state, state the snapshot date and return UNKNOWN for unresolved newer state.",
        "Do not reconstruct or infer private QSOL-CONTEXT from omissions.",
        "",
        "[EPISTEMIC_RULES]",
        "KNOWN=explicitly established by this capsule or stronger evidence supplied in the current task",
        "RETRIEVED=not available in a no-tools run unless evidence is supplied directly in the current task",
        "INFERRED=reasoned from evidence but not explicitly stated by it",
        "UNKNOWN=not established by available evidence",
        "CONFLICT=relevant evidence cannot be reconciled safely",
        "FICTION=deliberately fictional, satirical, simulated, or role-play material",
        *CORE_GUARDS,
        "REPLAY != EMPIRICAL_VALIDATION",
        "PRESERVE_PROVENANCE=true",
        "RESOLVE_CANONICAL_IDS_BEFORE_ALIASES=true",
        "",
        "[SERIALIZATION]",
        "ITEM lines contain: kind, canonical source path, canonical JSON object.",
        "Canonical JSON objects are copied without factual transformation.",
        "BOUNDARY lines are epistemic guards derived from explicit project tags; they are not additional project facts.",
        "All source_refs in included ITEM objects resolve to included source ITEM objects.",
        "All included relationship endpoints resolve to included ITEM objects.",
        "",
        "[ITEMS]",
    ]
    for item in selected:
        lines.append(_line_for_item(item))
        for guard in _boundary_guards(item):
            lines.append(f"BOUNDARY\t{item.item_id}\t{guard}")

    if profile.get("redundant_guards"):
        lines.extend([
            "",
            "[SMALL_MODEL_GUARD_REPEAT]",
            *CORE_GUARDS,
            "NO_TOOLS=true",
            f"SNAPSHOT_DATE={identity['snapshot_date']}",
            "IF_CURRENT_STATE_IS_NOT_RESOLVED_BY_THIS_SNAPSHOT=UNKNOWN",
        ])
    lines.extend(["", "[END_QSOL_TOOLLESS_CAPSULE]", ""])
    return "\n".join(lines)


def _identity(root: Path, source_commit: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not COMMIT_RE.fullmatch(source_commit):
        raise CapsuleError("--source-commit must be exactly 40 lowercase hexadecimal characters")
    manifest = _load_json(root / "ai/manifest.json")
    if not isinstance(manifest, dict):
        raise CapsuleError("ai/manifest.json must be an object")
    protocol = manifest.get("protocol")
    snapshot_date = manifest.get("snapshot_date")
    schema_version = manifest.get("schema_version")
    if not all(isinstance(value, str) and value for value in (protocol, snapshot_date, schema_version)):
        raise CapsuleError("manifest protocol/schema_version/snapshot_date must be non-empty strings")
    fingerprint = build_fingerprint(root)
    identity = {
        "protocol": protocol,
        "version": f"snapshot-{snapshot_date}",
        "version_kind": "snapshot",
        "schema_version": schema_version,
        "snapshot_date": snapshot_date,
        "source_commit": source_commit,
        "substrate_sha256": fingerprint["substrate_sha256"],
    }
    return identity, manifest


def _select_profile(profile: dict[str, Any], identity: dict[str, Any], items: list[CapsuleItem]) -> tuple[set[str], str]:
    lookup = {item.item_id: item for item in items}
    dependencies = {item.item_id: _dependencies(item, lookup) for item in items}
    ordered = sorted(items, key=_item_sort_key)

    if profile["name"] == "FULL":
        selected = set(lookup)
        text = _render_capsule(profile, identity, selected, items)
        count = portable_token_count(text)
        if count > profile["budget"]:
            raise CapsuleError(f"FULL capsule requires {count} portable tokens, above budget {profile['budget']}")
        return selected, text

    selected: set[str] = set()
    for candidate in ordered:
        if candidate.item_id in selected:
            continue
        addition = _closure(candidate.item_id, lookup, dependencies, selected)
        trial = selected | addition
        text = _render_capsule(profile, identity, trial, items)
        if portable_token_count(text) <= profile["budget"]:
            selected = trial

    text = _render_capsule(profile, identity, selected, items)
    if portable_token_count(text) > profile["budget"]:
        raise CapsuleError(f"{profile['name']} capsule exceeded deterministic token budget")
    return selected, text


def _ensure_safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    output = output.resolve()
    if output == root:
        raise CapsuleError("capsule output may not replace repository root")
    if output in root.parents:
        raise CapsuleError("capsule output may not be an ancestor of repository root")
    return root, output


def build_toolless_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _ensure_safe_output(root, output)
    identity, source_manifest = _identity(root, source_commit)
    items = _canonical_items(root, source_manifest)

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir: Path | None = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        profile_entries: list[dict[str, Any]] = []
        file_rows: list[tuple[str, str, int]] = []
        for profile in PROFILE_SPECS:
            selected, text = _select_profile(profile, identity, items)
            data = text.encode("utf-8")
            rel = profile["filename"]
            (temp_dir / rel).write_bytes(data)
            kind_counts: dict[str, int] = {}
            lookup = {item.item_id: item for item in items}
            for item_id in selected:
                kind = lookup[item_id].kind
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
            entry = {
                "name": profile["name"],
                "file": rel,
                "token_budget": profile["budget"],
                "portable_tokens": portable_token_count(text),
                "bytes": len(data),
                "sha256": _sha256(data),
                "included_items": len(selected),
                "omitted_items": len(items) - len(selected),
                "truncated": len(selected) != len(items),
                "kind_counts": dict(sorted(kind_counts.items())),
                "strategic_redundancy": bool(profile.get("redundant_guards")),
            }
            profile_entries.append(entry)
            file_rows.append((rel, entry["sha256"], entry["bytes"]))

        bundle_material = "".join(f"{path}\0{sha}\0{size}\n" for path, sha, size in sorted(file_rows)).encode("utf-8")
        manifest = {
            "type": "qsol-substrate-toolless-manifest",
            "schema_version": "1.0.0",
            "capsule_spec_version": CAPSULE_SPEC_VERSION,
            "substrate": identity,
            "tokenizer": {
                "id": "qsol-portable-token-v1",
                "normalization": "NFKC",
                "word_charge": "ceil(utf8_bytes/4)",
                "punctuation_charge": 1,
                "model_tokenizer_equivalence_claimed": False,
            },
            "selection": {
                "whole_record_only": True,
                "dependency_closure": True,
                "source_reference_closure": True,
                "relationship_endpoint_closure": True,
                "priority_order": ["epistemic_and_identity", "projects_publications_and_topics", "relationships_and_chronology", "unreferenced_sources"],
                "omission_semantics": "unavailable_not_false",
            },
            "profiles": profile_entries,
            "bundle_sha256": _sha256(bundle_material),
        }
        (temp_dir / "manifest.json").write_bytes(canonical_json_bytes(manifest))

        if output.exists():
            if output.is_symlink():
                raise CapsuleError("refusing to replace symlinked capsule output")
            shutil.rmtree(output)
        temp_dir.replace(output)
        temp_dir = None
        return manifest
    finally:
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _parse_capsule_items(text: str) -> tuple[dict[str, tuple[str, str, dict[str, Any]]], list[tuple[str, str]]]:
    items: dict[str, tuple[str, str, dict[str, Any]]] = {}
    boundaries: list[tuple[str, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if line.startswith("ITEM\t"):
            parts = line.split("\t", 3)
            if len(parts) != 4:
                raise CapsuleError(f"malformed ITEM line {line_no}")
            _, kind, source_path, raw_json = parts
            try:
                payload = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                raise CapsuleError(f"invalid ITEM JSON at line {line_no}: {exc}") from exc
            if not isinstance(payload, dict):
                raise CapsuleError(f"ITEM payload at line {line_no} must be an object")
            item_id = payload.get("id")
            if not isinstance(item_id, str) or not item_id:
                if kind == "wrapper":
                    item_id = f"wrapper:{source_path}"
                else:
                    raise CapsuleError(f"ITEM at line {line_no} has no canonical id")
            if item_id in items:
                raise CapsuleError(f"duplicate ITEM id in capsule: {item_id}")
            items[item_id] = (kind, source_path, payload)
        elif line.startswith("BOUNDARY\t"):
            parts = line.split("\t", 2)
            if len(parts) != 3:
                raise CapsuleError(f"malformed BOUNDARY line {line_no}")
            boundaries.append((parts[1], parts[2]))
    return items, boundaries


def validate_toolless_bundle(root: Path, bundle: Path, *, schema_path: str = CAPSULE_MANIFEST_SCHEMA) -> list[CapsuleFinding]:
    root = root.resolve()
    bundle = bundle.resolve()
    findings: list[CapsuleFinding] = []
    try:
        manifest = _load_json(bundle / "manifest.json")
    except CapsuleError as exc:
        return [CapsuleFinding("toolless.manifest", "manifest.json", str(exc))]
    if not isinstance(manifest, dict):
        return [CapsuleFinding("toolless.manifest", "manifest.json", "manifest must be an object")]

    try:
        schema = _load_json(root / schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in validator.iter_errors(manifest):
            pointer = "/".join(str(part) for part in error.absolute_path)
            findings.append(CapsuleFinding("toolless.schema", f"manifest.json/{pointer}" if pointer else "manifest.json", "toolless manifest schema violation"))
    except Exception as exc:
        return [CapsuleFinding("toolless.schema_definition", schema_path, str(exc))]

    substrate = manifest.get("substrate")
    if not isinstance(substrate, dict):
        findings.append(CapsuleFinding("toolless.substrate", "manifest.json/substrate", "substrate identity must be an object"))
        return findings
    source_commit = substrate.get("source_commit")
    if not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit):
        findings.append(CapsuleFinding("toolless.commit", "manifest.json/substrate/source_commit", "source commit must be a 40-character lowercase hexadecimal SHA"))

    try:
        expected_fp = build_fingerprint(root)["substrate_sha256"]
        source_manifest = _load_json(root / "ai/manifest.json")
        canonical_items = _canonical_items(root, source_manifest)
    except Exception as exc:
        findings.append(CapsuleFinding("toolless.canonical", "canonical_payload", str(exc)))
        return findings
    if substrate.get("substrate_sha256") != expected_fp:
        findings.append(CapsuleFinding("toolless.substrate_hash", "manifest.json/substrate/substrate_sha256", "capsule bundle does not match current canonical substrate fingerprint"))

    canonical_lookup = {item.item_id: item for item in canonical_items}
    profile_entries = manifest.get("profiles")
    if not isinstance(profile_entries, list):
        findings.append(CapsuleFinding("toolless.profiles", "manifest.json/profiles", "profiles must be an array"))
        return findings
    if [entry.get("name") for entry in profile_entries if isinstance(entry, dict)] != list(PROFILE_NAMES):
        findings.append(CapsuleFinding("toolless.profile_set", "manifest.json/profiles", "profile set/order must be MICRO, STANDARD, FULL"))

    file_rows: list[tuple[str, str, int]] = []
    for index, entry in enumerate(profile_entries):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        rel = entry.get("file")
        if not isinstance(rel, str):
            findings.append(CapsuleFinding("toolless.file", f"manifest.json/profiles/{index}/file", "profile file must be a string"))
            continue
        try:
            rel = _safe_relative(rel)
            data = (bundle / rel).read_bytes()
            text = data.decode("utf-8")
        except (CapsuleError, FileNotFoundError, UnicodeDecodeError) as exc:
            findings.append(CapsuleFinding("toolless.file", rel, str(exc)))
            continue
        actual_sha = _sha256(data)
        if actual_sha != entry.get("sha256"):
            findings.append(CapsuleFinding("toolless.file_hash", rel, "capsule SHA-256 does not match manifest"))
        if len(data) != entry.get("bytes"):
            findings.append(CapsuleFinding("toolless.file_bytes", rel, "capsule byte length does not match manifest"))
        actual_tokens = portable_token_count(text)
        if actual_tokens != entry.get("portable_tokens"):
            findings.append(CapsuleFinding("toolless.token_count", rel, "portable token count does not match manifest"))
        budget = entry.get("token_budget")
        if not isinstance(budget, int) or actual_tokens > budget:
            findings.append(CapsuleFinding("toolless.token_budget", rel, "capsule exceeds declared portable token budget"))

        required_stamps = [
            f"PROFILE={name}",
            "NO_TOOLS=true",
            f"SNAPSHOT_DATE={substrate.get('snapshot_date')}",
            f"SOURCE_COMMIT={source_commit}",
            f"SUBSTRATE_SHA256={substrate.get('substrate_sha256')}",
            "TOKENIZER=qsol-portable-token-v1",
            "OMISSION_MEANS=UNAVAILABLE_NOT_FALSE",
        ]
        for stamp in required_stamps:
            if stamp not in text:
                findings.append(CapsuleFinding("toolless.stamp", rel, f"required capsule stamp missing: {stamp}"))
        for guard in CORE_GUARDS:
            if guard not in text:
                findings.append(CapsuleFinding("toolless.guard", rel, f"required epistemic guard missing: {guard}"))
        if "If a question requires post-snapshot current state" not in text:
            findings.append(CapsuleFinding("toolless.freshness", rel, "snapshot-currentness refusal rule is missing"))

        try:
            parsed, boundaries = _parse_capsule_items(text)
        except CapsuleError as exc:
            findings.append(CapsuleFinding("toolless.serialization", rel, str(exc)))
            continue

        if len(parsed) != entry.get("included_items"):
            findings.append(CapsuleFinding("toolless.item_count", rel, "included item count does not match manifest"))
        if len(canonical_items) - len(parsed) != entry.get("omitted_items"):
            findings.append(CapsuleFinding("toolless.omitted_count", rel, "omitted item count does not match canonical item set"))
        expected_truncated = len(parsed) != len(canonical_items)
        if entry.get("truncated") is not expected_truncated:
            findings.append(CapsuleFinding("toolless.truncation", rel, "truncation flag does not match included canonical item set"))

        for item_id, (kind, source_path, payload) in parsed.items():
            canonical = canonical_lookup.get(item_id)
            if canonical is None:
                findings.append(CapsuleFinding("toolless.noncanonical_item", rel, f"capsule contains unknown canonical item: {item_id}"))
                continue
            if canonical.kind != kind or canonical.source_path != source_path or canonical.payload != payload:
                findings.append(CapsuleFinding("toolless.fact_transform", rel, f"capsule item differs from canonical substrate: {item_id}"))

        source_ids = {item_id for item_id, (kind, _, _) in parsed.items() if kind == "source"}
        for item_id, (kind, _, payload) in parsed.items():
            refs = payload.get("source_refs")
            if isinstance(refs, list):
                for ref in refs:
                    if isinstance(ref, str) and ref not in source_ids:
                        findings.append(CapsuleFinding("toolless.provenance_closure", rel, f"source_ref is not included in capsule: {item_id} -> {ref}"))
            if kind == "relationship":
                for endpoint_key in ("source", "target"):
                    endpoint = payload.get(endpoint_key)
                    if isinstance(endpoint, str) and endpoint not in parsed:
                        findings.append(CapsuleFinding("toolless.relationship_closure", rel, f"relationship endpoint is not included: {item_id} -> {endpoint}"))

        expected_boundaries: set[tuple[str, str]] = set()
        for item_id, (kind, _, _) in parsed.items():
            canonical = canonical_lookup.get(item_id)
            if canonical is not None and kind == "project":
                for guard in _boundary_guards(canonical):
                    expected_boundaries.add((item_id, guard))
        if set(boundaries) != expected_boundaries:
            findings.append(CapsuleFinding("toolless.boundaries", rel, "project claim-boundary guards do not match canonical project tags"))

        if name == "MICRO":
            if not entry.get("strategic_redundancy"):
                findings.append(CapsuleFinding("toolless.redundancy", rel, "MICRO must declare strategic semantic redundancy"))
            for guard in CORE_GUARDS:
                if text.count(guard) < 2:
                    findings.append(CapsuleFinding("toolless.redundancy", rel, f"MICRO must repeat guard: {guard}"))
        if name == "FULL" and set(parsed) != set(canonical_lookup):
            findings.append(CapsuleFinding("toolless.full_completeness", rel, "FULL capsule must include every canonical payload item"))

        file_rows.append((rel, actual_sha, len(data)))

    bundle_material = "".join(f"{path}\0{sha}\0{size}\n" for path, sha, size in sorted(file_rows)).encode("utf-8")
    if _sha256(bundle_material) != manifest.get("bundle_sha256"):
        findings.append(CapsuleFinding("toolless.bundle_hash", "manifest.json/bundle_sha256", "toolless bundle SHA-256 does not match profile files"))
    return findings
