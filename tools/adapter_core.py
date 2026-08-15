from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import build_fingerprint, canonical_json_bytes

ADAPTER_SPEC_VERSION = "1.0.0"
ADAPTER_MANIFEST_SCHEMA = "schema/adapter-manifest.schema.json"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

ADAPTER_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"id": "adapter:generic-single-file", "transport": "generic_single_file", "identity": "generic-single-file/1.0.0", "knowledge_files": ["generic/QSOL-SUBSTRATE.txt"]},
    {"id": "adapter:grok-chat", "transport": "grok_chat_bootstrap", "identity": "grok-chat/1.0.0", "knowledge_files": ["grok/chat-bootstrap.txt"]},
    {"id": "adapter:xai-retrieval", "transport": "xai_collections_retrieval", "identity": "xai-retrieval/1.0.0", "knowledge_files": ["xai-retrieval/QSOL-SUBSTRATE.md"]},
    {"id": "adapter:grok-build", "transport": "grok_build_project_rules_skill", "identity": "grok-build/1.0.0", "knowledge_files": ["grok-build/knowledge/QSOL-SUBSTRATE.txt"]},
    {"id": "adapter:sider", "transport": "sider_prompt_knowledge_base", "identity": "sider/1.0.0", "knowledge_files": ["sider/knowledge-base.md"]},
    {"id": "adapter:ollama", "transport": "ollama_modelfile_system_context", "identity": "ollama/1.0.0", "knowledge_files": ["ollama/system-context.txt"]},
    {"id": "adapter:openai-compatible", "transport": "openai_responses_context", "identity": "openai-compatible/1.0.0", "knowledge_files": ["openai/developer-instructions.txt"]},
    {"id": "adapter:anthropic-compatible", "transport": "anthropic_messages_context", "identity": "anthropic-compatible/1.0.0", "knowledge_files": ["anthropic/system-prompt.txt"]},
)
REQUIRED_ADAPTER_IDS = tuple(item["id"] for item in ADAPTER_DEFINITIONS)

PROJECTION_BEGIN = "----- BEGIN QSOL CANONICAL PROJECTION -----"
PROJECTION_END = "----- END QSOL CANONICAL PROJECTION -----"


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterFinding:
    code: str
    path: str
    message: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(path: str) -> str:
    p = Path(path)
    if p.is_absolute() or ".." in p.parts or path in {"", "."}:
        raise AdapterError(f"unsafe adapter output path: {path!r}")
    return p.as_posix()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AdapterError(f"required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AdapterError(f"invalid JSON in {path}: {exc}") from exc


def _canonical_source_bytes(path: Path, rel: str) -> bytes:
    if rel.endswith(".jsonl"):
        rows: list[Any] = []
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise AdapterError(f"required file not found: {path}") from exc
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AdapterError(f"invalid JSONL in {rel}:{line_no}: {exc}") from exc
        return b"".join(canonical_json_bytes(row) for row in rows)
    return canonical_json_bytes(_load_json(path))


def _projection_body(root: Path, manifest: dict[str, Any]) -> str:
    normative = manifest.get("normative_machine_files")
    payload = manifest.get("canonical_payload_files")
    if not isinstance(normative, list) or not all(isinstance(v, str) for v in normative):
        raise AdapterError("manifest normative_machine_files must be a string array")
    if not isinstance(payload, list) or not all(isinstance(v, str) for v in payload):
        raise AdapterError("manifest canonical_payload_files must be a string array")

    sections: list[str] = [
        "QSOL-SUBSTRATE CANONICAL PROJECTION/1",
        "This projection is generated from canonical public machine records.",
        "Transport formatting is non-normative. Embedded machine records remain authoritative.",
        "",
        "[NORMATIVE MACHINE CONTRACTS]",
    ]
    for rel in normative:
        rel = _safe_relative(rel)
        data = _canonical_source_bytes(root / rel, rel).decode("utf-8").rstrip("\n")
        sections.extend([f"FILE={rel}", data, f"END_FILE={rel}", ""])
    sections.append("[CANONICAL PUBLIC PAYLOAD]")
    for rel in payload:
        rel = _safe_relative(rel)
        data = _canonical_source_bytes(root / rel, rel).decode("utf-8").rstrip("\n")
        sections.extend([f"FILE={rel}", data, f"END_FILE={rel}", ""])
    return "\n".join(sections).rstrip() + "\n"


def _substrate_identity(root: Path, source_commit: str) -> tuple[dict[str, Any], str, str]:
    if not COMMIT_RE.fullmatch(source_commit):
        raise AdapterError("--source-commit must be exactly 40 lowercase hexadecimal characters")
    manifest = _load_json(root / "ai/manifest.json")
    if not isinstance(manifest, dict):
        raise AdapterError("ai/manifest.json must be a JSON object")
    fingerprint = build_fingerprint(root)
    snapshot_date = manifest.get("snapshot_date")
    schema_version = manifest.get("schema_version")
    protocol = manifest.get("protocol")
    if not all(isinstance(v, str) and v for v in (snapshot_date, schema_version, protocol)):
        raise AdapterError("manifest protocol/schema_version/snapshot_date must be non-empty strings")
    version = f"snapshot-{snapshot_date}"
    identity = {
        "protocol": protocol,
        "version": version,
        "version_kind": "snapshot",
        "schema_version": schema_version,
        "snapshot_date": snapshot_date,
        "source_commit": source_commit,
        "substrate_sha256": fingerprint["substrate_sha256"],
    }
    body = _projection_body(root, manifest)
    projection_sha256 = _sha256(body.encode("utf-8"))
    return identity, body, projection_sha256


def _header(adapter_id: str, identity: dict[str, Any], projection_sha256: str) -> str:
    return "\n".join([
        "QSOL-SUBSTRATE PORTABLE ADAPTER/1",
        f"ADAPTER_ID={adapter_id}",
        f"ADAPTER_SPEC_VERSION={ADAPTER_SPEC_VERSION}",
        f"SUBSTRATE_VERSION={identity['version']}",
        f"SUBSTRATE_SCHEMA_VERSION={identity['schema_version']}",
        f"SNAPSHOT_DATE={identity['snapshot_date']}",
        f"SOURCE_COMMIT={identity['source_commit']}",
        f"SUBSTRATE_SHA256={identity['substrate_sha256']}",
        f"PROJECTION_SHA256={projection_sha256}",
        "TRANSPORT_ONLY=true",
        "FACT_REDEFINITION=FORBIDDEN",
        "ABSENCE=UNAVAILABLE_NOT_FALSE",
        "",
    ])


def _full_projection_file(adapter_id: str, identity: dict[str, Any], projection_sha256: str, body: str, preamble: str) -> str:
    return _header(adapter_id, identity, projection_sha256) + preamble.rstrip() + "\n\n" + PROJECTION_BEGIN + "\n" + body + PROJECTION_END + "\n"


def _bootstrap_text(adapter_id: str, identity: dict[str, Any], projection_sha256: str, *, knowledge_path: str | None = None) -> str:
    lines = [
        _header(adapter_id, identity, projection_sha256).rstrip(),
        "",
        "Use the QSOL public substrate as evidence, not as permission to invent missing facts.",
        "Preserve epistemic states exactly: known, retrieved, inferred, unknown, conflict, fiction.",
        "UNKNOWN != FALSE.",
        "INFERRED != KNOWN.",
        "FICTION/SATIRE != BIOGRAPHY OR EVENT HISTORY.",
        "FORMALIZATION != EMPIRICAL OR PHYSICAL TRUTH.",
        "Live primary evidence may supersede stale snapshot state; otherwise state the snapshot limit.",
        "Do not infer, request, or reconstruct private QSOL-CONTEXT.",
    ]
    if knowledge_path:
        lines.extend([
            f"Canonical adapter knowledge file: {knowledge_path}",
            "When QSOL context is relevant, read/use that file before answering.",
            "If it cannot be accessed, do not pretend its contents were loaded.",
        ])
    return "\n".join(lines) + "\n"


def _render_files(identity: dict[str, Any], body: str, projection_sha256: str) -> dict[str, tuple[str, str, str]]:
    files: dict[str, tuple[str, str, str]] = {}

    generic_id = "adapter:generic-single-file"
    files["generic/QSOL-SUBSTRATE.txt"] = (_full_projection_file(generic_id, identity, projection_sha256, body, "Single-file vendor-neutral bundle. Supply this complete file as context when no dedicated adapter exists."), generic_id, "knowledge")

    grok_id = "adapter:grok-chat"
    files["grok/chat-bootstrap.txt"] = (_full_projection_file(grok_id, identity, projection_sha256, body, "Grok chat bootstrap. Paste this file as high-priority user-provided context or attach it as a public text file."), grok_id, "knowledge")

    xai_id = "adapter:xai-retrieval"
    files["xai-retrieval/QSOL-SUBSTRATE.md"] = (_full_projection_file(xai_id, identity, projection_sha256, body, "xAI Collections retrieval document. Upload this document to a dedicated collection; retrieval is transport only."), xai_id, "knowledge")
    xai_meta = {
        "type": "qsol-xai-retrieval-upload",
        "adapter_id": xai_id,
        "adapter_spec_version": ADAPTER_SPEC_VERSION,
        "substrate": identity,
        "projection_sha256": projection_sha256,
        "document": "QSOL-SUBSTRATE.md",
        "suggested_collection_name": f"QSOL-SUBSTRATE-{identity['version']}",
        "document_fields": {"protocol": identity["protocol"], "snapshot_date": identity["snapshot_date"], "substrate_sha256": identity["substrate_sha256"], "source_commit": identity["source_commit"]},
        "search_transport": {"management_api": "https://management-api.x.ai/v1", "search_api": "https://api.x.ai/v1/documents/search", "collection_id": "REPLACE_WITH_COLLECTION_ID"},
        "fact_redefinition": "forbidden",
    }
    files["xai-retrieval/upload-manifest.json"] = (canonical_json_bytes(xai_meta).decode("utf-8"), xai_id, "transport_manifest")

    build_id = "adapter:grok-build"
    files["grok-build/knowledge/QSOL-SUBSTRATE.txt"] = (_full_projection_file(build_id, identity, projection_sha256, body, "Grok Build project knowledge file. Project rules and the qsol-substrate skill point here."), build_id, "knowledge")
    agents = _bootstrap_text(build_id, identity, projection_sha256, knowledge_path="knowledge/QSOL-SUBSTRATE.txt") + "\nProject rule: adapters are disposable transport layers and must not redefine canonical substrate facts.\nFor questions outside the loaded evidence, return UNKNOWN or explicitly label inference rather than inventing lore.\n"
    files["grok-build/AGENTS.md"] = (agents, build_id, "project_rules")
    skill = "---\nname: qsol-substrate\ndescription: Load and apply the pinned public QSOL-SUBSTRATE when a task concerns QSOL identity, projects, publications, chronology, terminology, provenance, or relationships.\n---\n\n# QSOL Substrate\n\n" + _bootstrap_text(build_id, identity, projection_sha256, knowledge_path="knowledge/QSOL-SUBSTRATE.txt") + "\n## Procedure\n\n1. Read `knowledge/QSOL-SUBSTRATE.txt` before making QSOL factual claims.\n2. Resolve canonical IDs and aliases from the substrate rather than guessing.\n3. Preserve provenance and epistemic labels.\n4. Prefer live primary repository evidence only when the task requires current state and tools are available.\n5. If evidence remains insufficient, answer UNKNOWN.\n"
    files["grok-build/.grok/skills/qsol-substrate/SKILL.md"] = (skill, build_id, "skill")

    sider_id = "adapter:sider"
    files["sider/knowledge-base.md"] = (_full_projection_file(sider_id, identity, projection_sha256, body, "Sider knowledge-base document. Add this file to the selected Sider file/knowledge workflow."), sider_id, "knowledge")
    files["sider/prompt.txt"] = (_bootstrap_text(sider_id, identity, projection_sha256, knowledge_path="knowledge-base.md"), sider_id, "prompt")

    ollama_id = "adapter:ollama"
    system_context = _full_projection_file(ollama_id, identity, projection_sha256, body, "Ollama system context. This exact text may be passed through the API `system` field or embedded in a Modelfile SYSTEM block.")
    files["ollama/system-context.txt"] = (system_context, ollama_id, "knowledge")
    modelfile = "# QSOL-SUBSTRATE Ollama adapter template\n" + f"# ADAPTER_ID={ollama_id}\n# ADAPTER_SPEC_VERSION={ADAPTER_SPEC_VERSION}\n# SUBSTRATE_VERSION={identity['version']}\n# SOURCE_COMMIT={identity['source_commit']}\n# SUBSTRATE_SHA256={identity['substrate_sha256']}\n" + "# Replace REPLACE_WITH_BASE_MODEL with an exact Ollama model tag or immutable local model reference.\nFROM REPLACE_WITH_BASE_MODEL\nSYSTEM \"\"\"\n" + system_context.replace('"""', '\\"\\"\\"') + "\"\"\"\n"
    files["ollama/Modelfile.template"] = (modelfile, ollama_id, "modelfile_template")

    openai_id = "adapter:openai-compatible"
    developer_context = _full_projection_file(openai_id, identity, projection_sha256, body, "OpenAI-compatible developer/system context. For Responses-compatible APIs, place this text in high-priority instructions/developer context.")
    files["openai/developer-instructions.txt"] = (developer_context, openai_id, "knowledge")
    files["openai/request.example.json"] = (canonical_json_bytes({"model": "REPLACE_WITH_MODEL_ID", "instructions": developer_context, "input": "REPLACE_WITH_USER_TASK"}).decode("utf-8"), openai_id, "request_template")

    anthropic_id = "adapter:anthropic-compatible"
    anthropic_context = _full_projection_file(anthropic_id, identity, projection_sha256, body, "Anthropic-compatible system context. Supply this text through the Messages API system parameter.")
    files["anthropic/system-prompt.txt"] = (anthropic_context, anthropic_id, "knowledge")
    files["anthropic/request.example.json"] = (canonical_json_bytes({"model": "REPLACE_WITH_MODEL_ID", "max_tokens": 1024, "system": anthropic_context, "messages": [{"role": "user", "content": "REPLACE_WITH_USER_TASK"}]}).decode("utf-8"), anthropic_id, "request_template")
    return files


def _ensure_safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    output = output.resolve()
    if output == root:
        raise AdapterError("adapter output may not replace repository root")
    if output in root.parents:
        raise AdapterError("adapter output may not be an ancestor of the repository")
    return root, output


def build_adapter_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _ensure_safe_output(root, output)
    identity, body, projection_sha256 = _substrate_identity(root, source_commit)
    rendered = _render_files(identity, body, projection_sha256)

    temp_parent = output.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=temp_parent))
    try:
        file_entries: list[dict[str, Any]] = []
        by_adapter: dict[str, list[dict[str, Any]]] = {item["id"]: [] for item in ADAPTER_DEFINITIONS}
        for rel in sorted(rendered):
            text, adapter_id, role = rendered[rel]
            safe = _safe_relative(rel)
            data = text.encode("utf-8")
            dest = temp_dir / safe
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            entry = {"path": safe, "role": role, "sha256": _sha256(data), "bytes": len(data)}
            file_entries.append(entry)
            by_adapter[adapter_id].append(entry)

        definitions = {item["id"]: item for item in ADAPTER_DEFINITIONS}
        adapters: list[dict[str, Any]] = []
        for adapter_id in REQUIRED_ADAPTER_IDS:
            definition = definitions[adapter_id]
            adapters.append({
                "id": adapter_id,
                "transport": definition["transport"],
                "identity": definition["identity"],
                "source_substrate_sha256": identity["substrate_sha256"],
                "projection_sha256": projection_sha256,
                "knowledge_projection_files": definition["knowledge_files"],
                "files": sorted(by_adapter[adapter_id], key=lambda item: item["path"]),
            })

        hash_material = "".join(f"{item['path']}\0{item['sha256']}\0{item['bytes']}\n" for item in sorted(file_entries, key=lambda item: item["path"])).encode("utf-8")
        manifest = {
            "type": "qsol-substrate-adapter-manifest",
            "schema_version": "1.0.0",
            "adapter_spec_version": ADAPTER_SPEC_VERSION,
            "substrate": identity,
            "projection": {"scope": "all_normative_machine_contracts_and_canonical_public_payload", "projection_sha256": projection_sha256, "fact_transform": "none", "transport_only": True, "canonical_source_of_truth": "repository canonical machine records"},
            "adapters": adapters,
            "adapter_bundle_sha256": _sha256(hash_material),
        }
        (temp_dir / "manifest.json").write_bytes(canonical_json_bytes(manifest))

        if output.exists():
            if output.is_symlink():
                raise AdapterError("refusing to replace symlinked adapter output")
            shutil.rmtree(output)
        temp_dir.replace(output)
        temp_dir = Path()
        return manifest
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _extract_projection(text: str) -> str | None:
    begin = text.find(PROJECTION_BEGIN + "\n")
    if begin < 0:
        return None
    begin += len(PROJECTION_BEGIN) + 1
    end = text.find(PROJECTION_END, begin)
    if end < 0:
        return None
    return text[begin:end]


def validate_adapter_bundle(root: Path, bundle: Path, *, schema_path: str = ADAPTER_MANIFEST_SCHEMA) -> list[AdapterFinding]:
    root = root.resolve()
    bundle = bundle.resolve()
    findings: list[AdapterFinding] = []
    try:
        manifest = _load_json(bundle / "manifest.json")
    except AdapterError as exc:
        return [AdapterFinding("adapter.manifest", "manifest.json", str(exc))]
    if not isinstance(manifest, dict):
        return [AdapterFinding("adapter.manifest", "manifest.json", "manifest must be an object")]

    try:
        schema = _load_json(root / schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in validator.iter_errors(manifest):
            pointer = "/".join(str(p) for p in error.absolute_path)
            findings.append(AdapterFinding("adapter.schema", f"manifest.json/{pointer}" if pointer else "manifest.json", "adapter manifest schema violation"))
    except Exception as exc:
        findings.append(AdapterFinding("adapter.schema_definition", schema_path, str(exc)))
        return findings

    substrate = manifest.get("substrate")
    if not isinstance(substrate, dict):
        findings.append(AdapterFinding("adapter.substrate", "manifest.json/substrate", "substrate identity must be an object"))
        return findings
    source_commit = substrate.get("source_commit")
    if not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit):
        findings.append(AdapterFinding("adapter.commit", "manifest.json/substrate/source_commit", "source commit must be 40 lowercase hexadecimal characters"))

    try:
        expected_fp = build_fingerprint(root)["substrate_sha256"]
    except Exception as exc:
        findings.append(AdapterFinding("adapter.substrate", "canonical_payload", str(exc)))
        expected_fp = None
    if expected_fp is not None and substrate.get("substrate_sha256") != expected_fp:
        findings.append(AdapterFinding("adapter.substrate_hash", "manifest.json/substrate/substrate_sha256", "adapter bundle does not match current canonical substrate fingerprint"))

    adapters = manifest.get("adapters")
    if not isinstance(adapters, list):
        findings.append(AdapterFinding("adapter.entries", "manifest.json/adapters", "adapters must be an array"))
        return findings
    seen_ids = [a.get("id") for a in adapters if isinstance(a, dict)]
    if seen_ids != list(REQUIRED_ADAPTER_IDS):
        findings.append(AdapterFinding("adapter.set", "manifest.json/adapters", "adapter IDs/order must match the Phase 4 portable adapter set"))

    all_file_entries: list[dict[str, Any]] = []
    claimed_paths: set[str] = set()
    projection_sha256 = manifest.get("projection", {}).get("projection_sha256") if isinstance(manifest.get("projection"), dict) else None
    for adapter in adapters:
        if not isinstance(adapter, dict):
            continue
        adapter_id = adapter.get("id")
        if adapter.get("source_substrate_sha256") != substrate.get("substrate_sha256"):
            findings.append(AdapterFinding("adapter.identity", str(adapter_id), "adapter source substrate SHA-256 mismatch"))
        if adapter.get("projection_sha256") != projection_sha256:
            findings.append(AdapterFinding("adapter.projection_identity", str(adapter_id), "adapter projection SHA-256 mismatch"))
        files = adapter.get("files")
        if not isinstance(files, list):
            findings.append(AdapterFinding("adapter.files", str(adapter_id), "adapter files must be an array"))
            continue
        for entry in files:
            if not isinstance(entry, dict):
                continue
            rel = entry.get("path")
            if not isinstance(rel, str):
                continue
            try:
                rel = _safe_relative(rel)
            except AdapterError as exc:
                findings.append(AdapterFinding("adapter.path", str(adapter_id), str(exc)))
                continue
            if rel in claimed_paths:
                findings.append(AdapterFinding("adapter.path_duplicate", rel, "adapter output path is claimed more than once"))
            claimed_paths.add(rel)
            path = bundle / rel
            try:
                data = path.read_bytes()
            except FileNotFoundError:
                findings.append(AdapterFinding("adapter.file_missing", rel, "declared adapter file is missing"))
                continue
            if _sha256(data) != entry.get("sha256"):
                findings.append(AdapterFinding("adapter.file_hash", rel, "adapter file SHA-256 does not match manifest"))
            if len(data) != entry.get("bytes"):
                findings.append(AdapterFinding("adapter.file_bytes", rel, "adapter file byte length does not match manifest"))
            all_file_entries.append(entry)
        knowledge = adapter.get("knowledge_projection_files")
        if not isinstance(knowledge, list) or not knowledge:
            findings.append(AdapterFinding("adapter.knowledge", str(adapter_id), "adapter requires at least one canonical knowledge projection file"))
            continue
        for rel in knowledge:
            if not isinstance(rel, str):
                continue
            try:
                text = (bundle / rel).read_text(encoding="utf-8")
            except (FileNotFoundError, UnicodeDecodeError):
                findings.append(AdapterFinding("adapter.knowledge", rel, "knowledge projection file cannot be read"))
                continue
            projection = _extract_projection(text)
            if projection is None:
                findings.append(AdapterFinding("adapter.projection", rel, "canonical projection markers are missing"))
            elif _sha256(projection.encode("utf-8")) != projection_sha256:
                findings.append(AdapterFinding("adapter.projection_hash", rel, "embedded canonical projection does not match manifest"))
            for stamp in [f"ADAPTER_ID={adapter_id}", f"SOURCE_COMMIT={source_commit}", f"SUBSTRATE_SHA256={substrate.get('substrate_sha256')}", f"PROJECTION_SHA256={projection_sha256}"]:
                if stamp not in text:
                    findings.append(AdapterFinding("adapter.stamp", rel, "adapter identity stamp is missing or inconsistent"))

    hash_material = "".join(f"{item['path']}\0{item['sha256']}\0{item['bytes']}\n" for item in sorted(all_file_entries, key=lambda item: item.get("path", ""))).encode("utf-8")
    if _sha256(hash_material) != manifest.get("adapter_bundle_sha256"):
        findings.append(AdapterFinding("adapter.bundle_hash", "manifest.json/adapter_bundle_sha256", "adapter bundle SHA-256 does not match declared files"))
    return findings
