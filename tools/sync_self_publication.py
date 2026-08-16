#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DOI = "10.5281/zenodo.21959180"
VERSION = "1.0.0"
TAG = "v1.0.0"
COMMIT = "4483582173abf62f61bcc18076b22c1db10b26ca"
RELEASE_ID = 371154565
CAPTURED_AT = "2026-08-15"
REPOSITORY = "QSOLKCB/QSOL-SUBSTRATE"
SOURCE_ID = "src:qsol-substrate-v1.0.0-release"
PUBLICATION_ID = "publication:qsol-substrate-v1.0.0"
RELATIONSHIP_ID = "rel:qsol-substrate-publishes-qsol-substrate-v1.0.0"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return value


def upsert(items: list[dict[str, Any]], record: dict[str, Any], *, key: str = "id") -> None:
    matches = [index for index, item in enumerate(items) if isinstance(item, dict) and item.get(key) == record[key]]
    if len(matches) > 1:
        raise RuntimeError(f"duplicate existing identity: {record[key]}")
    if matches:
        items[matches[0]] = record
    else:
        items.append(record)


def render_source_registry(value: dict[str, Any]) -> str:
    rows = value.get("sources")
    if not isinstance(rows, list):
        raise RuntimeError("sources/index.json sources must be an array")
    lines = ["{"]
    scalar_items = [(key, item) for key, item in value.items() if key != "sources"]
    for key, item in scalar_items:
        lines.append(f"  {json.dumps(key)}: {json.dumps(item, ensure_ascii=False)},")
    lines.append('  "sources": [')
    for index, row in enumerate(rows):
        suffix = "," if index < len(rows) - 1 else ""
        lines.append("    " + json.dumps(row, ensure_ascii=False, separators=(",", ":")) + suffix)
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source_path = root / "sources/index.json"
    publication_path = root / "publications/index.json"
    relationship_path = root / "relationships/graph.json"

    sources = load(source_path)
    publications = load(publication_path)
    relationships = load(relationship_path)

    source_rows = sources.get("sources")
    publication_rows = publications.get("records")
    edge_rows = relationships.get("edges")
    if not isinstance(source_rows, list) or not isinstance(publication_rows, list) or not isinstance(edge_rows, list):
        raise RuntimeError("canonical registry collections are malformed")

    source = {
        "id": SOURCE_ID,
        "record_type": "source",
        "visibility": "public",
        "epistemic_state": "known",
        "class": "release_record",
        "url": f"https://github.com/{REPOSITORY}/releases/tag/{TAG}",
        "snapshot": {
            "kind": "release_tag_commit",
            "commit": COMMIT,
            "url": f"https://github.com/{REPOSITORY}/tree/{COMMIT}",
            "tag": TAG,
            "release_id": RELEASE_ID,
            "captured_at": CAPTURED_AT,
        },
        "summary": f"QSOL-SUBSTRATE {TAG} release identity for archival software DOI {DOI}.",
    }
    publication = {
        "id": PUBLICATION_ID,
        "record_type": "publication",
        "visibility": "public",
        "epistemic_state": "known",
        "name": "QSOL-SUBSTRATE: A Deterministic, Provenance-Aware Public Context Substrate for AI Systems",
        "version": VERSION,
        "doi": DOI,
        "repository": REPOSITORY,
        "commit": COMMIT,
        "source_refs": [SOURCE_ID],
        "metadata": {
            "publisher": "Zenodo",
            "resource_type": "computer software",
            "release_id": RELEASE_ID,
        },
    }
    edge = {
        "id": RELATIONSHIP_ID,
        "record_type": "relationship",
        "visibility": "public",
        "epistemic_state": "known",
        "source": "project:qsol-substrate",
        "relationship": "publishes",
        "target": PUBLICATION_ID,
        "source_refs": [SOURCE_ID],
    }

    upsert(source_rows, source)
    upsert(publication_rows, publication)
    upsert(edge_rows, edge)

    source_path.write_text(render_source_registry(sources), encoding="utf-8")
    publication_path.write_text(json.dumps(publications, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    relationship_path.write_text(json.dumps(relationships, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    print(f"source={SOURCE_ID}")
    print(f"publication={PUBLICATION_ID}")
    print(f"relationship={RELATIONSHIP_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
