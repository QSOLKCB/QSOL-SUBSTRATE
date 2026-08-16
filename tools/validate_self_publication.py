#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

DOI = "10.5281/zenodo.21959180"
VERSION = "1.0.0"
TAG = "v1.0.0"
COMMIT = "4483582173abf62f61bcc18076b22c1db10b26ca"
RELEASE_ID = 371154565
CANONICAL_SHA256 = "fb6e7a694ff1279af67d4aaf776e232e31025d9737011f6768fdc79c0f63eb25"
REPOSITORY = "QSOLKCB/QSOL-SUBSTRATE"
SOURCE_ID = "src:qsol-substrate-v1.0.0-release"
PUBLICATION_ID = "publication:qsol-substrate-v1.0.0"
RELATIONSHIP_ID = "rel:qsol-substrate-publishes-qsol-substrate-v1.0.0"


def load_json(root: Path, rel: str) -> dict[str, Any]:
    value = json.loads((root / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{rel} must contain an object")
    return value


def one(items: list[Any], identity: str, label: str) -> dict[str, Any]:
    matches = [item for item in items if isinstance(item, dict) and item.get("id") == identity]
    if len(matches) != 1:
        raise RuntimeError(f"{label}: expected exactly one {identity}; found {len(matches)}")
    return matches[0]


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    sources = load_json(root, "sources/index.json")
    publications = load_json(root, "publications/index.json")
    relationships = load_json(root, "relationships/graph.json")
    release_manifest = load_json(root, "release/published-v1.0.0.json")
    release_schema = load_json(root, "schema/published-release-manifest.schema.json")
    Draft202012Validator.check_schema(release_schema)
    schema_errors = list(Draft202012Validator(release_schema).iter_errors(release_manifest))
    require(not schema_errors, "published v1.0.0 release manifest schema drift", failures)

    source = one(sources.get("sources", []), SOURCE_ID, "sources/index.json")
    publication = one(publications.get("records", []), PUBLICATION_ID, "publications/index.json")
    edge = one(relationships.get("edges", []), RELATIONSHIP_ID, "relationships/graph.json")

    snapshot = source.get("snapshot") if isinstance(source.get("snapshot"), dict) else {}
    require(source.get("class") == "release_record", "source class must be release_record", failures)
    require(source.get("url") == f"https://github.com/{REPOSITORY}/releases/tag/{TAG}", "source release URL drift", failures)
    require(snapshot.get("kind") == "release_tag_commit", "source snapshot kind drift", failures)
    require(snapshot.get("commit") == COMMIT, "source commit drift", failures)
    require(snapshot.get("tag") == TAG, "source tag drift", failures)
    require(snapshot.get("release_id") == RELEASE_ID, "source release_id drift", failures)

    require(publication.get("doi") == DOI, "canonical publication DOI drift", failures)
    require(publication.get("version") == VERSION, "canonical publication version drift", failures)
    require(publication.get("repository") == REPOSITORY, "canonical publication repository drift", failures)
    require(publication.get("commit") == COMMIT, "canonical publication commit drift", failures)
    require(publication.get("source_refs") == [SOURCE_ID], "canonical publication provenance drift", failures)

    require(edge.get("source") == "project:qsol-substrate", "publishes edge source drift", failures)
    require(edge.get("relationship") == "publishes", "publishes edge relationship drift", failures)
    require(edge.get("target") == PUBLICATION_ID, "publishes edge target drift", failures)
    require(edge.get("source_refs") == [SOURCE_ID], "publishes edge provenance drift", failures)

    require(release_manifest.get("version") == VERSION, "published release manifest version drift", failures)
    require(release_manifest.get("tag") == TAG, "published release manifest tag drift", failures)
    require(release_manifest.get("repository") == REPOSITORY, "published release manifest repository drift", failures)
    require(release_manifest.get("commit") == COMMIT, "published release manifest commit drift", failures)
    require(release_manifest.get("github_release_id") == RELEASE_ID, "published release manifest release ID drift", failures)
    require(release_manifest.get("doi") == DOI, "published release manifest DOI drift", failures)
    require(release_manifest.get("canonical_substrate_sha256") == CANONICAL_SHA256, "published release manifest canonical SHA drift", failures)
    require(release_manifest.get("canonical_source_id") == SOURCE_ID, "published release manifest source ID drift", failures)
    require(release_manifest.get("canonical_publication_id") == PUBLICATION_ID, "published release manifest publication ID drift", failures)

    readme = (root / "README.md").read_text(encoding="utf-8")
    require(DOI in readme, "README DOI badge/reference drift", failures)

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    require(re.search(r"(?m)^version:\s*[\"']?1\.0\.0[\"']?\s*$", citation) is not None, "CITATION.cff version drift", failures)
    require(COMMIT in citation, "CITATION.cff release commit drift", failures)
    require(f"releases/tag/{TAG}" in citation, "CITATION.cff release URL drift", failures)

    zenodo = load_json(root, ".zenodo.json")
    require(zenodo.get("version") == VERSION, ".zenodo.json version drift", failures)
    identifiers = zenodo.get("related_identifiers") if isinstance(zenodo.get("related_identifiers"), list) else []
    identifier_values = {item.get("identifier") for item in identifiers if isinstance(item, dict)}
    require(f"https://github.com/{REPOSITORY}/commit/{COMMIT}" in identifier_values, ".zenodo.json commit identity drift", failures)
    require(f"https://github.com/{REPOSITORY}/releases/tag/{TAG}" in identifier_values, ".zenodo.json release identity drift", failures)
    notes = str(zenodo.get("notes", ""))
    require(CANONICAL_SHA256 in notes, ".zenodo.json canonical substrate SHA drift", failures)

    if failures:
        for failure in failures:
            print(f"SELF_PUBLICATION_DRIFT\t{failure}")
        return 1
    print(f"SELF_PUBLICATION_VALID doi={DOI} version={VERSION} commit={COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
