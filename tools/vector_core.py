from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import struct
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import canonical_json_bytes
from toolless_core import CapsuleItem, _canonical_items, _identity, portable_token_count

VECTOR_SPEC_VERSION = "1.0.0"
VECTOR_MANIFEST_SCHEMA = "schema/vector-manifest.schema.json"
EMBEDDING_ID = "qsol-hash-embed-v1"
CHUNKING_ID = "qsol-record-chunk-v1"
DIMENSION = 256
DTYPE = "float16"
ENDIAN = "little"
TOKEN_RE = re.compile(r"[\w]+(?:[-.:/][\w]+)*|[^\w\s]", re.UNICODE)
EXPECTED_FILES = {
    "records.jsonl",
    "embeddings.f16",
    "index.json",
    "retrieval-report.json",
    "manifest.json",
}
PROFILE_BUDGETS = {"MICRO": 8192, "STANDARD": 24576, "FULL": 131072}

REFERENCE_QUERIES = (
    {
        "id": "identity-trent",
        "query": "person:trent-slade Trent Slade EmergentMonk",
        "expected": ["person:trent-slade"],
    },
    {
        "id": "substrate-project",
        "query": "project:qsol-substrate QSOL-SUBSTRATE public vendor-neutral context substrate",
        "expected": ["project:qsol-substrate", "term:qsol-substrate"],
    },
    {
        "id": "uff-doi",
        "query": "publication:uff-v5.2.0 10.5281/zenodo.21911644 UFF v5.2.0",
        "expected": ["publication:uff-v5.2.0"],
    },
    {
        "id": "res-rag",
        "query": "publication:res-rag-v1.1.0 RES=RAG CSNP",
        "expected": ["publication:res-rag-v1.1.0", "project:res-rag"],
    },
    {
        "id": "whoami-satire",
        "query": "project:whoami-18437 WHOAMI-18437 satire",
        "expected": ["project:whoami-18437"],
    },
    {
        "id": "deepseek-c64",
        "query": "publication:deepseekc64-v1.0.0 deepseekc64 C64-IET Lean 4",
        "expected": ["publication:deepseekc64-v1.0.0", "project:deepseekc64"],
    },
)


class VectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorFinding:
    code: str
    path: str
    message: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VectorError(f"cannot load JSON {path}: {exc}") from exc


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key in sorted(value):
            yield str(key)
            yield from _walk_strings(value[key])
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_strings(nested)


def record_search_text(item: CapsuleItem) -> str:
    """Deterministic record-level chunk text; one canonical item == one chunk."""
    fields = [item.item_id, item.kind, item.source_path]
    fields.extend(_walk_strings(item.payload))
    return "\n".join(str(value) for value in fields if str(value))


def _features(text: str) -> list[tuple[str, float]]:
    tokens = TOKEN_RE.findall(_normalise(text))
    result: list[tuple[str, float]] = []
    for token in tokens:
        result.append(("u\0" + token, 1.0))
    for left, right in zip(tokens, tokens[1:]):
        result.append(("b\0" + left + "\0" + right, 0.5))
    return result


def hash_embedding(text: str, dimension: int = DIMENSION) -> list[float]:
    if dimension <= 0:
        raise VectorError("embedding dimension must be positive")
    values = [0.0] * dimension
    for feature, weight in _features(text):
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] & 1 else -1.0
        values[index] += sign * weight
    norm = math.sqrt(sum(value * value for value in values))
    if norm:
        values = [value / norm for value in values]
    return values


def pack_f16(vector: list[float]) -> bytes:
    return struct.pack("<" + "e" * len(vector), *vector)


def unpack_f16(data: bytes, dimension: int = DIMENSION) -> list[float]:
    expected = dimension * 2
    if len(data) != expected:
        raise VectorError(f"expected {expected} vector bytes, got {len(data)}")
    return list(struct.unpack("<" + "e" * dimension, data))


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _record_row(item: CapsuleItem, vector_index: int) -> dict[str, Any]:
    source_refs = item.payload.get("source_refs")
    if not isinstance(source_refs, list):
        source_refs = []
    epistemic = item.payload.get("epistemic_state")
    visibility = item.payload.get("visibility")
    text = record_search_text(item)
    return {
        "chunk_id": f"chunk:{item.item_id}",
        "canonical_id": item.item_id,
        "record_type": item.kind,
        "source_path": item.source_path,
        "vector_index": vector_index,
        "content_sha256": _sha256(canonical_json_bytes(item.payload)),
        "search_text": text,
        "payload": item.payload,
        "metadata": {
            "source_refs": sorted(ref for ref in source_refs if isinstance(ref, str)),
            "epistemic_state": epistemic if isinstance(epistemic, str) else None,
            "visibility": visibility if isinstance(visibility, str) else None,
        },
    }


def _records_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) for row in rows)


def _read_records(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise VectorError(f"cannot read records: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise VectorError(f"invalid records.jsonl line {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise VectorError(f"records.jsonl line {line_no} is not an object")
        rows.append(row)
    return rows


def _safe_output(root: Path, output: Path) -> tuple[Path, Path]:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise VectorError("refusing to replace symlinked vector output")
    output = output.resolve()
    if output == root or output in root.parents:
        raise VectorError("vector output may not replace or contain repository root")
    if root in output.parents and output != root / "dist" / "vectors":
        raise VectorError("in-repository vector output is restricted to dist/vectors")
    if output.exists() and not output.is_dir():
        raise VectorError("refusing to replace non-directory vector output")
    return root, output


def _context_closure(seed_ids: list[str], rows: list[dict[str, Any]]) -> list[str]:
    lookup = {row["canonical_id"]: row for row in rows}
    selected = set(seed_ids)
    pending = list(seed_ids)
    while pending:
        item_id = pending.pop()
        row = lookup.get(item_id)
        if row is None:
            continue
        metadata = row.get("metadata", {})
        refs = metadata.get("source_refs", []) if isinstance(metadata, dict) else []
        payload = row.get("payload", {})
        deps = [ref for ref in refs if isinstance(ref, str)]
        if row.get("record_type") == "relationship" and isinstance(payload, dict):
            deps.extend(value for value in (payload.get("source"), payload.get("target")) if isinstance(value, str))
        for dep in deps:
            if dep in lookup and dep not in selected:
                selected.add(dep)
                pending.append(dep)
    return [row["canonical_id"] for row in rows if row["canonical_id"] in selected]


def retrieve(rows: list[dict[str, Any]], embeddings: bytes, query: str, top_k: int = 5) -> list[dict[str, Any]]:
    if top_k <= 0:
        raise VectorError("top_k must be positive")
    if len(embeddings) != len(rows) * DIMENSION * 2:
        raise VectorError("embedding byte length does not match record count/dimension")
    query_vector = hash_embedding(query)
    ranked: list[tuple[float, str, dict[str, Any]]] = []
    stride = DIMENSION * 2
    for row in rows:
        index = row.get("vector_index")
        if not isinstance(index, int) or index < 0 or index >= len(rows):
            raise VectorError("invalid vector_index in records")
        vector = unpack_f16(embeddings[index * stride:(index + 1) * stride])
        score = _dot(query_vector, vector)
        ranked.append((score, str(row.get("canonical_id", "")), row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [dict(row, score=round(score, 8)) for score, _, row in ranked[:top_k]]


def render_retrieved_context(rows: list[dict[str, Any]], selected_ids: list[str]) -> str:
    lookup = {row["canonical_id"]: row for row in rows}
    lines = ["QSOL-SUBSTRATE/VECTOR-CONTEXT/1", "OMISSION_MEANS=UNAVAILABLE_NOT_FALSE"]
    for item_id in selected_ids:
        row = lookup[item_id]
        payload = canonical_json_bytes(row["payload"]).decode("utf-8").rstrip("\n")
        lines.append(f"ITEM\t{row['record_type']}\t{row['source_path']}\t{payload}")
    lines.append("")
    return "\n".join(lines)


def _retrieval_report(rows: list[dict[str, Any]], embeddings: bytes) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    hits = 0
    token_totals: list[int] = []
    for query in REFERENCE_QUERIES:
        primary = retrieve(rows, embeddings, query["query"], top_k=5)
        primary_ids = [row["canonical_id"] for row in primary]
        closed_ids = _context_closure(primary_ids, rows)
        context = render_retrieved_context(rows, closed_ids)
        tokens = portable_token_count(context)
        token_totals.append(tokens)
        expected = set(query["expected"])
        hit = bool(expected.intersection(primary_ids))
        hits += int(hit)
        closed_lookup = {row["canonical_id"]: row for row in rows if row["canonical_id"] in closed_ids}
        provenance_closed = True
        for row in closed_lookup.values():
            metadata = row.get("metadata", {})
            refs = metadata.get("source_refs", []) if isinstance(metadata, dict) else []
            if any(ref not in closed_lookup for ref in refs if isinstance(ref, str)):
                provenance_closed = False
        results.append({
            "id": query["id"],
            "query": query["query"],
            "expected_any": query["expected"],
            "top_k": primary_ids,
            "hit": hit,
            "closed_context_ids": closed_ids,
            "closed_context_items": len(closed_ids),
            "portable_tokens": tokens,
            "provenance_closed": provenance_closed,
        })
    average = sum(token_totals) / len(token_totals) if token_totals else 0.0
    reductions = {
        name: round(1.0 - average / budget, 6)
        for name, budget in PROFILE_BUDGETS.items()
    }
    return {
        "type": "qsol-vector-retrieval-reference-report",
        "schema_version": "1.0.0",
        "embedding_backend": EMBEDDING_ID,
        "top_k": 5,
        "query_count": len(results),
        "hit_count": hits,
        "hit_rate": round(hits / len(results), 6) if results else 0.0,
        "average_closed_context_portable_tokens": round(average, 3),
        "reduction_vs_fixed_profile_budget": reductions,
        "all_contexts_provenance_closed": all(item["provenance_closed"] for item in results),
        "results": results,
        "interpretation": "Reference retrieval-size experiment only; it does not measure downstream model answer quality.",
    }


def build_vector_bundle(root: Path, output: Path, source_commit: str) -> dict[str, Any]:
    root, output = _safe_output(root, output)
    identity, source_manifest = _identity(root, source_commit)
    items = _canonical_items(root, source_manifest)
    ordered = sorted(items, key=lambda item: (item.source_path, item.kind, item.item_id))
    rows = [_record_row(item, index) for index, item in enumerate(ordered)]
    records_data = _records_bytes(rows)
    embedding_parts = [pack_f16(hash_embedding(row["search_text"])) for row in rows]
    embeddings_data = b"".join(embedding_parts)
    index = {
        "type": "qsol-vector-index",
        "schema_version": "1.0.0",
        "substrate": identity,
        "chunking": CHUNKING_ID,
        "embedding_backend": EMBEDDING_ID,
        "dimension": DIMENSION,
        "dtype": DTYPE,
        "endian": ENDIAN,
        "record_count": len(rows),
        "entries": [
            {
                "chunk_id": row["chunk_id"],
                "canonical_id": row["canonical_id"],
                "vector_index": row["vector_index"],
                "byte_offset": row["vector_index"] * DIMENSION * 2,
                "byte_length": DIMENSION * 2,
            }
            for row in rows
        ],
    }
    index_data = canonical_json_bytes(index)
    report = _retrieval_report(rows, embeddings_data)
    report_data = canonical_json_bytes(report)

    files = {
        "records.jsonl": records_data,
        "embeddings.f16": embeddings_data,
        "index.json": index_data,
        "retrieval-report.json": report_data,
    }
    file_rows = [
        {"path": path, "sha256": _sha256(data), "bytes": len(data)}
        for path, data in sorted(files.items())
    ]
    bundle_material = "".join(f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n" for row in file_rows).encode("utf-8")
    manifest = {
        "type": "qsol-vector-substrate-manifest",
        "schema_version": "1.0.0",
        "vector_spec_version": VECTOR_SPEC_VERSION,
        "substrate": identity,
        "chunking": {
            "id": CHUNKING_ID,
            "unit": "canonical_item",
            "one_item_per_chunk": True,
            "factual_transformation": False,
        },
        "embedding": {
            "id": EMBEDDING_ID,
            "kind": "deterministic_feature_hash_reference",
            "dimension": DIMENSION,
            "dtype": DTYPE,
            "endian": ENDIAN,
            "normalization": "NFKC_casefold_L2",
            "learned_model": False,
            "canonical_truth_authority": False,
        },
        "retrieval": {
            "metric": "cosine_via_normalized_dot_product",
            "tie_break": "canonical_id_ascending",
            "provenance_closure": True,
            "relationship_endpoint_closure": True,
        },
        "record_count": len(rows),
        "files": file_rows,
        "bundle_sha256": _sha256(bundle_material),
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


def validate_vector_bundle(root: Path, bundle: Path, schema_path: str = VECTOR_MANIFEST_SCHEMA) -> list[VectorFinding]:
    root = root.resolve()
    if bundle.is_symlink():
        return [VectorFinding("vector.bundle", str(bundle), "bundle may not be a symlink")]
    bundle = bundle.resolve()
    findings: list[VectorFinding] = []
    if not bundle.is_dir():
        return [VectorFinding("vector.bundle", str(bundle), "bundle must be a real directory")]
    try:
        manifest = _load_json(bundle / "manifest.json")
    except VectorError as exc:
        return [VectorFinding("vector.manifest", "manifest.json", str(exc))]
    if not isinstance(manifest, dict):
        return [VectorFinding("vector.manifest", "manifest.json", "manifest must be an object")]
    try:
        schema = _load_json(root / schema_path)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in validator.iter_errors(manifest):
            pointer = "/".join(str(part) for part in error.absolute_path)
            findings.append(VectorFinding("vector.schema", f"manifest.json/{pointer}" if pointer else "manifest.json", "vector manifest schema violation"))
    except Exception as exc:
        return [VectorFinding("vector.schema_definition", schema_path, str(exc))]

    actual_names: set[str] = set()
    try:
        for child in bundle.iterdir():
            if child.is_symlink():
                findings.append(VectorFinding("vector.symlink", child.name, "bundle entries may not be symlinks"))
                continue
            if not child.is_file():
                findings.append(VectorFinding("vector.extra_entry", child.name, "bundle entries must be declared regular files"))
                continue
            actual_names.add(child.name)
    except OSError as exc:
        findings.append(VectorFinding("vector.bundle_read", str(bundle), str(exc)))
        return findings
    if actual_names != EXPECTED_FILES:
        findings.append(VectorFinding("vector.file_set", str(bundle), "bundle file set must match deterministic Phase 6 layout"))

    substrate = manifest.get("substrate", {})
    source_commit = substrate.get("source_commit") if isinstance(substrate, dict) else None
    if not isinstance(source_commit, str):
        findings.append(VectorFinding("vector.source_commit", "manifest.json/substrate/source_commit", "missing source commit"))
        return findings

    with tempfile.TemporaryDirectory() as temp:
        expected_dir = Path(temp) / "vectors"
        try:
            expected = build_vector_bundle(root, expected_dir, source_commit)
        except Exception as exc:
            findings.append(VectorFinding("vector.recompile", "canonical_payload", str(exc)))
            return findings
        for name in sorted(EXPECTED_FILES):
            actual_path = bundle / name
            expected_path = expected_dir / name
            if not actual_path.is_file() or actual_path.is_symlink():
                continue
            try:
                if actual_path.read_bytes() != expected_path.read_bytes():
                    findings.append(VectorFinding("vector.deterministic_mismatch", name, "file differs from deterministic canonical rebuild"))
            except OSError as exc:
                findings.append(VectorFinding("vector.file_read", name, str(exc)))
        if manifest != expected:
            findings.append(VectorFinding("vector.manifest_mismatch", "manifest.json", "manifest differs from deterministic canonical rebuild"))
    return findings
