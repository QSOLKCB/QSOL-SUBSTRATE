import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from substrate_integrity import build_fingerprint, validate_repository


RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id", "record_type", "visibility", "epistemic_state"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "record_type": {"enum": ["identity", "organization", "project", "publication", "research_topic", "term", "event", "relationship", "source", "claim"]},
        "visibility": {"const": "public"},
        "epistemic_state": {"enum": ["known", "retrieved", "inferred", "unknown", "conflict", "fiction"]},
        "source_refs": {"type": "array", "items": {"type": "string"}},
        "snapshot": {"type": "object"},
    },
}
PERMISSIVE_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}


class SubstrateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for d in ["ai", "schema", "sources", "identity", "context", "terminology", "projects", "publications", "relationships", "chronology", "public_export"]:
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.payload_paths = [
            "sources/index.json", "identity/public.json", "context/public.json", "terminology/index.json",
            "projects/index.json", "publications/index.json", "relationships/graph.json", "chronology/current.jsonl",
        ]
        self.manifest = {
            "type": "qsol-substrate-manifest", "protocol": "QSOL-SUBSTRATE", "schema_version": "1.0.0",
            "status": "phase-3-validation-ci", "snapshot_date": "2026-08-15", "visibility": "public",
            "canonical_payload_files": self.payload_paths, "normative_machine_files": ["ai/ontology.json"],
            "schema": "schema/substrate.schema.json",
            "export_schemas": {
                "policy": "schema/export-policy.schema.json",
                "allowlist": "schema/export-allowlist.schema.json",
                "deny_policy": "schema/export-deny-policy.schema.json",
            },
        }
        self.ontology = {"relationship_types": ["studies", "publishes"], "provenance_classes": ["first_party_documentation", "release_record"]}
        self.boundary = {
            "repository_visibility": "public", "publication_model": "explicit_allow_only", "absence_semantics": "unavailable_not_false",
            "private_source_access_required": False,
            "export_contract": {"default_publication_grants": 0, "public_source_registry_is_immutable_to_private_export": True},
        }
        self.policy = {"export_policy": "explicit_allow_only", "immutable_payload_files": ["sources/index.json"]}
        self.include = {"default": "deny", "entries": []}
        self.exclude = {
            "default": "deny_on_match", "forbidden_field_names": ["password", "token", "secret", "api_key"],
            "secret_patterns": [{"id": "github-token", "regex": "\\bghp_[A-Za-z0-9]{20,}\\b"}],
            "private_reference_patterns": [{"id": "private-path", "regex": "(?:^|[\\s\\\"'])/(?:home|root|workspace|Users)/[^\\s\\\"']+"}],
        }
        self.sources = {
            "type": "qsol-substrate-source-registry", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public",
            "sources": [
                {"id": "src:readme", "record_type": "source", "visibility": "public", "epistemic_state": "known", "class": "first_party_documentation", "url": "https://github.com/QSOLKCB/DEMO/blob/main/README.md", "snapshot": {"kind": "git_commit", "commit": "a" * 40, "url": "https://github.com/QSOLKCB/DEMO/blob/" + "a" * 40 + "/README.md", "captured_at": "2026-08-15"}},
                {"id": "src:release", "record_type": "source", "visibility": "public", "epistemic_state": "known", "class": "release_record", "url": "https://github.com/QSOLKCB/DEMO/releases/tag/v1.0.0", "snapshot": {"kind": "release_tag_commit", "commit": "b" * 40, "url": "https://github.com/QSOLKCB/DEMO/tree/" + "b" * 40, "tag": "v1.0.0", "release_id": 1, "captured_at": "2026-08-15"}},
            ],
        }
        self.identity = {"type": "qsol-substrate-public-identity", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public", "records": [
            {"id": "person:demo", "record_type": "identity", "visibility": "public", "epistemic_state": "known", "name": "Demo", "aliases": [], "source_refs": ["src:readme"]}
        ]}
        self.context = {"type": "qsol-substrate-public-context", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public", "claims": [
            {"id": "claim:demo", "record_type": "claim", "visibility": "public", "epistemic_state": "known", "summary": "demo", "source_refs": ["src:readme"]}
        ]}
        self.terminology = {"type": "qsol-substrate-terminology-registry", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public", "records": [
            {"id": "term:demo", "record_type": "term", "visibility": "public", "epistemic_state": "known", "name": "DEMO", "aliases": ["Demo System"], "source_refs": ["src:readme"]}
        ]}
        self.projects = {"type": "qsol-substrate-project-registry", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public", "records": [
            {"id": "project:demo", "record_type": "project", "visibility": "public", "epistemic_state": "known", "name": "DEMO", "repository": "QSOLKCB/DEMO", "source_refs": ["src:readme"]}
        ]}
        self.publications = {"type": "qsol-substrate-publication-registry", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public", "records": [
            {"id": "publication:demo-v1.0.0", "record_type": "publication", "visibility": "public", "epistemic_state": "known", "name": "Demo v1.0.0", "version": "1.0.0", "doi": "10.5281/zenodo.123456", "repository": "QSOLKCB/DEMO", "commit": "b" * 40, "source_refs": ["src:release"]}
        ]}
        self.relationships = {"type": "qsol-substrate-relationship-graph", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public", "nodes": [
            {"id": "topic:demo", "record_type": "research_topic", "visibility": "public", "epistemic_state": "known", "name": "Demo topic"}
        ], "edges": [
            {"id": "rel:demo-studies", "record_type": "relationship", "visibility": "public", "epistemic_state": "known", "source": "project:demo", "relationship": "studies", "target": "topic:demo", "source_refs": ["src:readme"]},
            {"id": "rel:demo-publishes", "record_type": "relationship", "visibility": "public", "epistemic_state": "known", "source": "project:demo", "relationship": "publishes", "target": "publication:demo-v1.0.0", "source_refs": ["src:release"]},
        ]}
        self.events = [
            {"id": "event:demo-release", "record_type": "event", "visibility": "public", "epistemic_state": "known", "occurred_at": "2026-08-15T01:00:00Z", "name": "Demo release", "source_refs": ["src:release"], "metadata": {"tag": "v1.0.0", "repository": "QSOLKCB/DEMO", "doi": "10.5281/zenodo.123456"}}
        ]
        self._write_all()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel, value):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8")

    def _write_all(self):
        self._write("ai/manifest.json", self.manifest)
        self._write("ai/ontology.json", self.ontology)
        self._write("ai/public-boundary.json", self.boundary)
        self._write("public_export/policy.json", self.policy)
        self._write("public_export/include.json", self.include)
        self._write("public_export/exclude.json", self.exclude)
        self._write("schema/substrate.schema.json", RECORD_SCHEMA)
        for name in ["export-policy", "export-allowlist", "export-deny-policy"]:
            self._write(f"schema/{name}.schema.json", PERMISSIVE_SCHEMA)
        self._write("sources/index.json", self.sources)
        self._write("identity/public.json", self.identity)
        self._write("context/public.json", self.context)
        self._write("terminology/index.json", self.terminology)
        self._write("projects/index.json", self.projects)
        self._write("publications/index.json", self.publications)
        self._write("relationships/graph.json", self.relationships)
        (self.root / "chronology/current.jsonl").write_text("".join(json.dumps(e) + "\n" for e in self.events), encoding="utf-8")

    def _codes(self):
        return [f.code for f in validate_repository(self.root).findings]

    def test_valid_fixture_passes(self):
        report = validate_repository(self.root)
        self.assertTrue(report.valid, report.findings)
        self.assertEqual(report.publication_count, 1)
        self.assertIsNotNone(report.substrate_sha256)

    def test_dangling_provenance_fails(self):
        self.projects["records"][0]["source_refs"] = ["src:missing"]
        self._write_all()
        self.assertIn("provenance.dangling", self._codes())

    def test_alias_collision_fails(self):
        self.terminology["records"].append({"id": "term:other", "record_type": "term", "visibility": "public", "epistemic_state": "known", "name": "Other", "aliases": [" demo system "], "source_refs": ["src:readme"]})
        self._write_all()
        self.assertIn("alias.collision", self._codes())

    def test_duplicate_doi_fails(self):
        second = copy.deepcopy(self.publications["records"][0])
        second.update({"id": "publication:demo-copy", "name": "Copy"})
        self.publications["records"].append(second)
        self.relationships["edges"].append({"id": "rel:demo-publishes-copy", "record_type": "relationship", "visibility": "public", "epistemic_state": "known", "source": "project:demo", "relationship": "publishes", "target": "publication:demo-copy", "source_refs": ["src:release"]})
        self._write_all()
        self.assertIn("doi.duplicate", self._codes())

    def test_relationship_endpoint_fails(self):
        self.relationships["edges"][0]["target"] = "topic:missing"
        self._write_all()
        self.assertIn("relationship.target", self._codes())

    def test_chronology_order_fails(self):
        self.events.insert(0, {"id": "event:later", "record_type": "event", "visibility": "public", "epistemic_state": "known", "occurred_at": "2026-08-16T01:00:00Z", "source_refs": ["src:release"], "metadata": {"tag": "v1.0.0", "repository": "QSOLKCB/DEMO"}})
        self._write_all()
        self.assertIn("chronology.order", self._codes())

    def test_nonpublic_record_fails_schema_and_boundary(self):
        self.projects["records"][0]["visibility"] = "private"
        self._write_all()
        codes = self._codes()
        self.assertIn("schema.invalid", codes)
        self.assertIn("boundary.visibility", codes)

    def test_secret_in_json_key_fails(self):
        self.projects["records"][0]["metadata"] = {"ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456": "oops"}
        self._write_all()
        self.assertIn("boundary.secret", self._codes())

    def test_private_absolute_path_fails(self):
        self.projects["records"][0]["summary"] = "internal /workspace/QSOL-CONTEXT/secret.json"
        self._write_all()
        self.assertIn("boundary.private_reference", self._codes())

    def test_release_tag_mismatch_fails(self):
        self.publications["records"][0]["version"] = "2.0.0"
        self._write_all()
        self.assertIn("release.version", self._codes())

    def test_publication_requires_publishes_edge(self):
        self.relationships["edges"] = [e for e in self.relationships["edges"] if e["relationship"] != "publishes"]
        self._write_all()
        self.assertIn("publication.relationship", self._codes())

    def test_fingerprint_is_deterministic_and_semantic(self):
        first = build_fingerprint(self.root)["substrate_sha256"]
        second = build_fingerprint(self.root)["substrate_sha256"]
        self.assertEqual(first, second)
        self.projects["records"][0]["summary"] = "changed public meaning"
        self._write_all()
        third = build_fingerprint(self.root)["substrate_sha256"]
        self.assertNotEqual(first, third)


if __name__ == "__main__":
    unittest.main()
