from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

CANONICAL_JSON_NAME = "qsol-canonical-json-v1"
CANONICAL_JSONL_NAME = "qsol-canonical-jsonl-v1"
EXPECTED_PAYLOADS: dict[str, tuple[str, tuple[str, ...]]] = {
    "sources/index.json": ("qsol-substrate-source-registry", ("sources",)),
    "identity/public.json": ("qsol-substrate-public-identity", ("records",)),
    "context/public.json": ("qsol-substrate-public-context", ("claims",)),
    "terminology/index.json": ("qsol-substrate-terminology-registry", ("records",)),
    "projects/index.json": ("qsol-substrate-project-registry", ("records",)),
    "publications/index.json": ("qsol-substrate-publication-registry", ("records",)),
    "relationships/graph.json": ("qsol-substrate-relationship-graph", ("nodes", "edges")),
    "chronology/current.jsonl": ("jsonl", ("<root>",)),
}
PREFIXES: dict[str, tuple[str, ...]] = {
    "identity": ("person:",),
    "organization": ("org:",),
    "project": ("project:",),
    "publication": ("publication:",),
    "research_topic": ("topic:",),
    "term": ("term:",),
    "event": ("event:",),
    "relationship": ("rel:",),
    "source": ("src:",),
    "claim": ("claim:",),
    "adapter": ("adapter:",),
    "probe": ("probe:",),
    "repository": ("repository:",),
}
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class IntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str


@dataclass
class ValidationReport:
    valid: bool
    snapshot_date: str | None
    record_count: int
    source_count: int
    relationship_count: int
    publication_count: int
    event_count: int
    substrate_sha256: str | None
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["type"] = "qsol-substrate-validation-report"
        value["schema_version"] = "1.0.0"
        return value


def canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise IntegrityError(f"cannot canonicalise JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IntegrityError(f"required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise IntegrityError(f"invalid JSON in {path}: {exc}") from exc


def _load_jsonl(path: Path) -> list[Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise IntegrityError(f"required file not found: {path}") from exc
    rows: list[Any] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise IntegrityError(f"invalid JSONL in {path}:{line_no}: {exc}") from exc
    return rows


def _payload_records(path: str, value: Any) -> list[dict[str, Any]]:
    if path == "chronology/current.jsonl":
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise IntegrityError("chronology/current.jsonl must contain JSON object records")
        return list(value)
    expected_type, collections = EXPECTED_PAYLOADS[path]
    if not isinstance(value, dict):
        raise IntegrityError(f"{path} must contain a JSON object")
    if value.get("type") != expected_type:
        raise IntegrityError(f"{path} type must be {expected_type!r}")
    records: list[dict[str, Any]] = []
    for collection in collections:
        items = value.get(collection)
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise IntegrityError(f"{path}:{collection} must be an array of objects")
        records.extend(items)
    return records


def load_repository(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[dict[str, Any]]]]:
    root = root.resolve()
    manifest = _load_json(root / "ai/manifest.json")
    payload_paths = manifest.get("canonical_payload_files")
    if not isinstance(payload_paths, list) or not all(isinstance(p, str) for p in payload_paths):
        raise IntegrityError("ai/manifest.json canonical_payload_files must be a string array")
    if set(payload_paths) != set(EXPECTED_PAYLOADS):
        missing = sorted(set(EXPECTED_PAYLOADS) - set(payload_paths))
        unknown = sorted(set(payload_paths) - set(EXPECTED_PAYLOADS))
        raise IntegrityError(f"canonical payload set is unresolved; missing={missing}, unknown={unknown}")
    payload: dict[str, Any] = {}
    records: dict[str, list[dict[str, Any]]] = {}
    for rel in payload_paths:
        path = root / rel
        value = _load_jsonl(path) if rel.endswith(".jsonl") else _load_json(path)
        payload[rel] = value
        records[rel] = _payload_records(rel, value)
    return manifest, payload, records


def build_fingerprint(root: Path) -> dict[str, Any]:
    manifest, payload, _ = load_repository(root)
    files: list[dict[str, Any]] = []
    for rel in sorted(payload):
        value = payload[rel]
        if rel.endswith(".jsonl"):
            data = b"".join(canonical_json_bytes(row) for row in value)
        else:
            data = canonical_json_bytes(value)
        files.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    material = "".join(
        f"{item['path']}\0{item['sha256']}\0{item['bytes']}\n" for item in files
    ).encode("utf-8")
    return {
        "type": "qsol-substrate-fingerprint",
        "schema_version": "1.0.0",
        "scope": "canonical_public_payload",
        "snapshot_date": manifest.get("snapshot_date"),
        "canonicalization": {
            "json": CANONICAL_JSON_NAME,
            "jsonl": CANONICAL_JSONL_NAME,
        },
        "files": files,
        "substrate_sha256": hashlib.sha256(material).hexdigest(),
    }


def _normalize_alias(value: str) -> str:
    return " ".join(value.casefold().split())


def _normalize_doi(value: str) -> str:
    text = value.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.casefold().startswith(prefix):
            text = text[len(prefix) :]
            break
    return text.casefold()


def _parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def _compile_patterns(items: Any, label: str, findings: list[Finding]) -> list[tuple[str, re.Pattern[str]]]:
    out: list[tuple[str, re.Pattern[str]]] = []
    if not isinstance(items, list):
        findings.append(Finding("boundary.config", label, "pattern list must be an array"))
        return out
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("regex"), str):
            findings.append(Finding("boundary.config", f"{label}[{idx}]", "pattern requires string id and regex"))
            continue
        try:
            out.append((item["id"], re.compile(item["regex"])))
        except re.error as exc:
            findings.append(Finding("boundary.config", f"{label}[{idx}]", f"invalid regex: {exc}"))
    return out


def _scan_public_value(
    value: Any,
    *,
    label: str,
    forbidden_names: set[str],
    secret_patterns: list[tuple[str, re.Pattern[str]]],
    private_patterns: list[tuple[str, re.Pattern[str]]],
    findings: list[Finding],
) -> None:
    def scan_text(text: str, path: str) -> None:
        for pattern_id, regex in secret_patterns:
            if regex.search(text):
                findings.append(Finding("boundary.secret", path, f"secret pattern {pattern_id!r} matched"))
        for pattern_id, regex in private_patterns:
            if regex.search(text):
                findings.append(Finding("boundary.private_reference", path, f"private-reference pattern {pattern_id!r} matched"))

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                key_text = str(key)
                child = f"{path}/{key_text}"
                if key_text.casefold() in forbidden_names:
                    findings.append(Finding("boundary.forbidden_field", child, f"forbidden field name {key_text!r}"))
                scan_text(key_text, child + "#key")
                walk(item, child)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                walk(item, f"{path}/{idx}")
        elif isinstance(node, str):
            scan_text(node, path)

    walk(value, label)


def _schema_errors(instance: Any, schema: dict[str, Any], label: str) -> Iterable[Finding]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
        pointer = "/".join(str(p) for p in error.absolute_path)
        path = f"{label}/{pointer}" if pointer else label
        yield Finding("schema.invalid", path, error.message)


def validate_repository(root: Path) -> ValidationReport:
    root = root.resolve()
    findings: list[Finding] = []
    try:
        manifest, payload, records_by_file = load_repository(root)
    except IntegrityError as exc:
        return ValidationReport(False, None, 0, 0, 0, 0, 0, None, [Finding("manifest.invalid", "ai/manifest.json", str(exc))])

    snapshot_date = manifest.get("snapshot_date") if isinstance(manifest.get("snapshot_date"), str) else None

    schema_paths = {manifest.get("schema")}
    export_schemas = manifest.get("export_schemas", {})
    if isinstance(export_schemas, dict):
        schema_paths.update(export_schemas.values())
    validation_schemas = manifest.get("validation_schemas", {})
    if isinstance(validation_schemas, dict):
        schema_paths.update(validation_schemas.values())
    schemas: dict[str, dict[str, Any]] = {}
    for rel in sorted(p for p in schema_paths if isinstance(p, str)):
        try:
            schema = _load_json(root / rel)
            Draft202012Validator.check_schema(schema)
            schemas[rel] = schema
        except Exception as exc:
            findings.append(Finding("schema.definition", rel, str(exc)))

    record_schema_path = manifest.get("schema")
    record_schema = schemas.get(record_schema_path) if isinstance(record_schema_path, str) else None
    if record_schema is None:
        findings.append(Finding("schema.missing", "ai/manifest.json/schema", "canonical record schema cannot be resolved"))

    contract_map = {
        "policy": "public_export/policy.json",
        "allowlist": "public_export/include.json",
        "deny_policy": "public_export/exclude.json",
    }
    if not isinstance(export_schemas, dict):
        findings.append(Finding("schema.missing", "ai/manifest.json/export_schemas", "export_schemas must be an object"))
    else:
        for key, instance_rel in contract_map.items():
            schema_rel = export_schemas.get(key)
            if not isinstance(schema_rel, str) or schema_rel not in schemas:
                findings.append(Finding("schema.missing", f"export_schemas/{key}", "schema cannot be resolved"))
                continue
            try:
                instance = _load_json(root / instance_rel)
                findings.extend(_schema_errors(instance, schemas[schema_rel], instance_rel))
            except IntegrityError as exc:
                findings.append(Finding("schema.instance", instance_rel, str(exc)))

    all_records: list[tuple[str, dict[str, Any]]] = []
    for rel, records in records_by_file.items():
        value = payload[rel]
        if rel != "chronology/current.jsonl":
            if not isinstance(value, dict) or value.get("visibility") != "public":
                findings.append(Finding("boundary.visibility", rel, "payload wrapper must declare visibility='public'"))
            if snapshot_date is not None and value.get("snapshot_date") != snapshot_date:
                findings.append(Finding("snapshot.mismatch", rel, "payload snapshot_date must match ai/manifest.json"))
        for idx, record in enumerate(records):
            label = f"{rel}#{idx}"
            all_records.append((label, record))
            if record_schema is not None:
                findings.extend(_schema_errors(record, record_schema, label))

    id_to_record: dict[str, dict[str, Any]] = {}
    id_to_label: dict[str, str] = {}
    for label, record in all_records:
        record_id = record.get("id")
        rtype = record.get("record_type")
        if not isinstance(record_id, str) or not record_id:
            findings.append(Finding("identity.missing", label, "record id must be a non-empty string"))
            continue
        if record_id in id_to_record:
            findings.append(Finding("identity.duplicate", label, f"duplicate canonical id {record_id!r}; first seen at {id_to_label[record_id]}"))
        else:
            id_to_record[record_id] = record
            id_to_label[record_id] = label
        if isinstance(rtype, str) and rtype in PREFIXES and not record_id.startswith(PREFIXES[rtype]):
            findings.append(Finding("identity.prefix", label, f"id {record_id!r} is inconsistent with record_type {rtype!r}"))
        if record.get("visibility") != "public":
            findings.append(Finding("boundary.visibility", label, "canonical record must declare visibility='public'"))

    identity_records = [r for _, r in all_records if r.get("record_type") == "identity"]
    if not identity_records:
        findings.append(Finding("identity.unresolved", "identity/public.json", "at least one canonical identity record is required"))

    sources = {
        r["id"]: r
        for r in records_by_file["sources/index.json"]
        if isinstance(r.get("id"), str)
    }
    ontology = _load_json(root / "ai/ontology.json")
    provenance_classes = set(ontology.get("provenance_classes", [])) if isinstance(ontology.get("provenance_classes"), list) else set()
    relationship_types = set(ontology.get("relationship_types", [])) if isinstance(ontology.get("relationship_types"), list) else set()

    for source_id, source in sources.items():
        label = id_to_label.get(source_id, "sources/index.json")
        source_class = source.get("class")
        if source_class not in provenance_classes:
            findings.append(Finding("provenance.class", label, f"unknown provenance class {source_class!r}"))
        snapshot = source.get("snapshot")
        if not isinstance(snapshot, dict):
            findings.append(Finding("provenance.snapshot", label, "source snapshot is required"))
            continue
        kind = snapshot.get("kind")
        if kind in {"git_commit", "release_tag_commit"}:
            commit = snapshot.get("commit")
            url = snapshot.get("url")
            if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
                findings.append(Finding("provenance.commit", label, "snapshot commit must be 40 lowercase hexadecimal characters"))
            if not isinstance(url, str) or not isinstance(commit, str) or commit not in url:
                findings.append(Finding("provenance.snapshot_url", label, "snapshot URL must pin the declared commit"))
        if kind == "release_tag_commit":
            if source_class != "release_record":
                findings.append(Finding("release.source_class", label, "release_tag_commit source must use class='release_record'"))
            if not isinstance(snapshot.get("tag"), str) or not snapshot.get("tag"):
                findings.append(Finding("release.tag", label, "release snapshot requires non-empty tag"))
            if not isinstance(snapshot.get("release_id"), int):
                findings.append(Finding("release.id", label, "release snapshot requires integer release_id"))
        elif source_class == "release_record":
            findings.append(Finding("release.snapshot", label, "release_record source must use snapshot.kind='release_tag_commit'"))
        elif kind == "api_identity":
            if not isinstance(snapshot.get("github_id"), int) or not isinstance(snapshot.get("login"), str):
                findings.append(Finding("provenance.api_identity", label, "api_identity snapshot requires github_id and login"))

    for label, record in all_records:
        rtype = record.get("record_type")
        if rtype == "source":
            continue
        refs = record.get("source_refs")
        if refs is None and rtype == "research_topic":
            continue
        if not isinstance(refs, list) or not refs:
            findings.append(Finding("provenance.missing", label, "non-source canonical record requires non-empty source_refs"))
            continue
        for ref in refs:
            if not isinstance(ref, str) or ref not in sources:
                findings.append(Finding("provenance.dangling", label, f"source_ref {ref!r} does not resolve to the public source registry"))

    alias_owner: dict[str, tuple[str, str]] = {}
    for record in records_by_file["terminology/index.json"]:
        rid = record.get("id")
        tokens: list[tuple[str, str]] = []
        if isinstance(record.get("name"), str):
            tokens.append(("name", record["name"]))
        aliases = record.get("aliases", [])
        if isinstance(aliases, list):
            tokens.extend(("alias", a) for a in aliases if isinstance(a, str))
        for kind, token in tokens:
            normalized = _normalize_alias(token)
            if not normalized:
                findings.append(Finding("alias.empty", id_to_label.get(rid, "terminology/index.json"), f"empty normalized {kind}"))
                continue
            previous = alias_owner.get(normalized)
            if previous is not None and previous[0] != rid:
                findings.append(Finding("alias.collision", id_to_label.get(rid, "terminology/index.json"), f"{token!r} collides with {previous[1]!r} owned by {previous[0]}"))
            else:
                alias_owner[normalized] = (rid, token)

    projects = records_by_file["projects/index.json"]
    project_by_repo: dict[str, dict[str, Any]] = {}
    for project in projects:
        repo = project.get("repository")
        if not isinstance(repo, str) or not repo:
            findings.append(Finding("project.repository", id_to_label.get(project.get("id"), "projects/index.json"), "project repository is required"))
        elif repo in project_by_repo:
            findings.append(Finding("project.repository_duplicate", id_to_label.get(project.get("id"), "projects/index.json"), f"repository {repo!r} is assigned to multiple projects"))
        else:
            project_by_repo[repo] = project

    publications = records_by_file["publications/index.json"]
    doi_owner: dict[str, str] = {}
    for publication in publications:
        label = id_to_label.get(publication.get("id"), "publications/index.json")
        doi = publication.get("doi")
        if not isinstance(doi, str) or not DOI_RE.fullmatch(_normalize_doi(doi)):
            findings.append(Finding("doi.invalid", label, f"invalid DOI {doi!r}"))
        else:
            norm = _normalize_doi(doi)
            if norm in doi_owner:
                findings.append(Finding("doi.duplicate", label, f"DOI {doi!r} duplicates {doi_owner[norm]}"))
            else:
                doi_owner[norm] = publication.get("id", label)
        repo = publication.get("repository")
        if not isinstance(repo, str) or repo not in project_by_repo:
            findings.append(Finding("publication.project", label, f"publication repository {repo!r} does not resolve to a canonical project"))

        refs = publication.get("source_refs") if isinstance(publication.get("source_refs"), list) else []
        release_sources = [sources[r] for r in refs if isinstance(r, str) and r in sources and sources[r].get("class") == "release_record"]
        version = publication.get("version")
        if release_sources and isinstance(version, str):
            expected_tag = version if version.startswith("v") else f"v{version}"
            if not any(src.get("snapshot", {}).get("tag") == expected_tag for src in release_sources):
                findings.append(Finding("release.version", label, f"publication version {version!r} does not resolve to release tag {expected_tag!r}"))
        commit = publication.get("commit")
        if release_sources and commit is not None:
            if not isinstance(commit, str) or not any(src.get("snapshot", {}).get("commit") == commit for src in release_sources):
                findings.append(Finding("release.commit", label, "publication commit does not match any cited release source"))

    graph = payload["relationships/graph.json"]
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    endpoint_ids = {rid for rid, record in id_to_record.items() if record.get("record_type") != "relationship"}
    publishes_targets: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        label = id_to_label.get(edge.get("id"), "relationships/graph.json")
        source_id = edge.get("source")
        target_id = edge.get("target")
        if source_id not in endpoint_ids:
            findings.append(Finding("relationship.source", label, f"source endpoint {source_id!r} is unresolved"))
        if target_id not in endpoint_ids:
            findings.append(Finding("relationship.target", label, f"target endpoint {target_id!r} is unresolved"))
        relation = edge.get("relationship")
        if relation not in relationship_types:
            findings.append(Finding("relationship.type", label, f"relationship type {relation!r} is not in ai/ontology.json"))
        if relation == "publishes" and isinstance(target_id, str):
            publishes_targets.setdefault(target_id, []).append(edge)

    for publication in publications:
        pid = publication.get("id")
        if not isinstance(pid, str):
            continue
        pub_edges = publishes_targets.get(pid, [])
        label = id_to_label.get(pid, "publications/index.json")
        if len(pub_edges) != 1:
            findings.append(Finding("publication.relationship", label, f"publication must have exactly one publishes edge; found {len(pub_edges)}"))
            continue
        project = id_to_record.get(pub_edges[0].get("source"))
        if not isinstance(project, dict) or project.get("repository") != publication.get("repository"):
            findings.append(Finding("publication.relationship_repository", label, "publishes edge project repository does not match publication repository"))

    referenced_topic_ids = {
        endpoint
        for edge in edges
        for endpoint in (edge.get("source"), edge.get("target"))
        if isinstance(endpoint, str)
    }
    for node in records_by_file["relationships/graph.json"]:
        if node.get("record_type") == "research_topic" and node.get("id") not in referenced_topic_ids:
            findings.append(Finding("provenance.topic", id_to_label.get(node.get("id"), "relationships/graph.json"), "research topic without source_refs must participate in at least one sourced relationship"))

    events = records_by_file["chronology/current.jsonl"]
    last_time: datetime | None = None
    for idx, event in enumerate(events):
        label = f"chronology/current.jsonl#{idx}"
        occurred = event.get("occurred_at")
        try:
            current = _parse_time(occurred) if isinstance(occurred, str) else None
            if current is None:
                raise ValueError("occurred_at is required")
        except ValueError as exc:
            findings.append(Finding("chronology.timestamp", label, str(exc)))
            continue
        if last_time is not None and current < last_time:
            findings.append(Finding("chronology.order", label, "events must be ordered by nondecreasing occurred_at"))
        last_time = current

        metadata = event.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("tag"), str):
            repo = metadata.get("repository")
            if not isinstance(repo, str) or repo not in project_by_repo:
                findings.append(Finding("release.event_project", label, f"release event repository {repo!r} does not resolve to a project"))
            refs = event.get("source_refs") if isinstance(event.get("source_refs"), list) else []
            release_sources = [sources[r] for r in refs if isinstance(r, str) and r in sources and sources[r].get("class") == "release_record"]
            if not release_sources:
                findings.append(Finding("release.event_source", label, "release event requires at least one release_record source"))
            else:
                matching = [s for s in release_sources if s.get("snapshot", {}).get("tag") == metadata.get("tag")]
                if not matching:
                    findings.append(Finding("release.event_tag", label, "event tag does not match any cited release source"))
                if isinstance(repo, str):
                    repo_path = "/" + repo + "/"
                    if not any(repo_path in urlparse(s.get("url", "")).path + "/" for s in matching):
                        findings.append(Finding("release.event_repository", label, "release source repository does not match event metadata.repository"))
            event_doi = metadata.get("doi")
            if isinstance(event_doi, str):
                norm = _normalize_doi(event_doi)
                publication = next((p for p in publications if isinstance(p.get("doi"), str) and _normalize_doi(p["doi"]) == norm), None)
                if publication is None or publication.get("repository") != repo:
                    findings.append(Finding("release.event_doi", label, "event DOI does not resolve to a publication in the same repository"))

    try:
        boundary = _load_json(root / "ai/public-boundary.json")
        policy = _load_json(root / "public_export/policy.json")
        include = _load_json(root / "public_export/include.json")
        exclude = _load_json(root / "public_export/exclude.json")
    except IntegrityError as exc:
        findings.append(Finding("boundary.config", "public-boundary", str(exc)))
        boundary, policy, include, exclude = {}, {}, {}, {}

    required_boundary = {
        "repository_visibility": "public",
        "publication_model": "explicit_allow_only",
        "absence_semantics": "unavailable_not_false",
        "private_source_access_required": False,
    }
    for key, expected in required_boundary.items():
        if boundary.get(key) != expected:
            findings.append(Finding("boundary.invariant", f"ai/public-boundary.json/{key}", f"must equal {expected!r}"))
    export_contract = boundary.get("export_contract")
    if not isinstance(export_contract, dict) or export_contract.get("public_source_registry_is_immutable_to_private_export") is not True:
        findings.append(Finding("boundary.immutability", "ai/public-boundary.json/export_contract", "public source registry immutability must be true"))
    if not isinstance(export_contract, dict) or export_contract.get("default_publication_grants") != 0:
        findings.append(Finding("boundary.default_deny", "ai/public-boundary.json/export_contract", "default_publication_grants must remain 0"))
    if policy.get("export_policy") != "explicit_allow_only":
        findings.append(Finding("boundary.policy", "public_export/policy.json", "export_policy must be explicit_allow_only"))
    immutable_files = policy.get("immutable_payload_files")
    if not isinstance(immutable_files, list) or "sources/index.json" not in immutable_files:
        findings.append(Finding("boundary.immutability", "public_export/policy.json", "sources/index.json must be declared immutable"))
    if include.get("default") != "deny":
        findings.append(Finding("boundary.allowlist", "public_export/include.json", "default must be deny"))
    if exclude.get("default") != "deny_on_match":
        findings.append(Finding("boundary.deny_policy", "public_export/exclude.json", "default must be deny_on_match"))

    forbidden_names = {str(v).casefold() for v in exclude.get("forbidden_field_names", [])} if isinstance(exclude.get("forbidden_field_names"), list) else set()
    secret_patterns = _compile_patterns(exclude.get("secret_patterns"), "secret_patterns", findings)
    private_patterns = _compile_patterns(exclude.get("private_reference_patterns"), "private_reference_patterns", findings)
    for rel, value in payload.items():
        _scan_public_value(value, label=rel, forbidden_names=forbidden_names, secret_patterns=secret_patterns, private_patterns=private_patterns, findings=findings)
    for rel in manifest.get("normative_machine_files", []):
        if not isinstance(rel, str) or rel == "ai/public-boundary.json":
            continue
        try:
            value = _load_json(root / rel)
        except IntegrityError as exc:
            findings.append(Finding("boundary.machine_file", str(rel), str(exc)))
            continue
        _scan_public_value(value, label=rel, forbidden_names=forbidden_names, secret_patterns=secret_patterns, private_patterns=private_patterns, findings=findings)
    _scan_public_value(include, label="public_export/include.json", forbidden_names=forbidden_names, secret_patterns=secret_patterns, private_patterns=private_patterns, findings=findings)

    fingerprint: dict[str, Any] | None = None
    try:
        fingerprint = build_fingerprint(root)
    except IntegrityError as exc:
        findings.append(Finding("fingerprint.failed", "canonical_payload", str(exc)))

    return ValidationReport(
        valid=not findings,
        snapshot_date=snapshot_date,
        record_count=len(all_records),
        source_count=len(sources),
        relationship_count=len(edges) if isinstance(edges, list) else 0,
        publication_count=len(publications),
        event_count=len(events),
        substrate_sha256=fingerprint.get("substrate_sha256") if fingerprint else None,
        findings=findings,
    )
