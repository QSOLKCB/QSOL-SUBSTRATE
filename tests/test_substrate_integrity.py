import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import substrate_integrity
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
        "snapshot": {"type": ["object", "null"]}
    }
}
PERMISSIVE_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}
FINGERPRINT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["snapshot_date"],
    "properties": {"snapshot_date": {"type": "string", "format": "date"}}
}


class SubstrateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for d in ["ai", "schema", "sources", "identity", "context", "terminology", "projects", "publications", "relationships", "chronology", "public_export"]:
            (self.root / d).mkdir(parents=True, exist_ok=True)

        self.payload_paths = list(substrate_integrity.PAYLOAD_SPECS)
        self.manifest = {
            "type": "qsol-substrate-manifest", "protocol": "QSOL-SUBSTRATE", "schema_version": "1.0.0",
            "status": "phase-3-validation-ci", "snapshot_date": "2026-08-15", "visibility": "public",
            "canonical_payload_files": self.payload_paths, "normative_machine_files": ["ai/ontology.json"],
            "schema": "schema/substrate.schema.json",
            "machine_contract_schemas": copy.deepcopy(substrate_integrity.BOOTSTRAP_CONTRACT_SCHEMAS),
            "export_schemas": {
                "policy": "schema/export-policy.schema.json",
                "allowlist": "schema/export-allowlist.schema.json",
                "deny_policy": "schema/export-deny-policy.schema.json"
            },
            "validation_schemas": {
                "report": "schema/validation-report.schema.json",
                "fingerprint": "schema/substrate-fingerprint.schema.json"
            }
        }
        self.ontology = {"relationship_types": ["studies", "publishes"], "provenance_classes": ["first_party_documentation", "release_record"]}
        self.boundary = {
            "repository_visibility": "public", "publication_model": "explicit_allow_only", "absence_semantics": "unavailable_not_false",
            "private_source_access_required": False,
            "export_contract": {"default_publication_grants": 0, "public_source_registry_is_immutable_to_private_export": True}
        }
        self.policy = {"export_policy": "explicit_allow_only", "immutable_payload_files": ["sources/index.json"]}
        self.include = {"default": "deny", "entries": []}
        self.exclude = {
            "default": "deny_on_match", "forbidden_source_path_globs": ["secrets/**"],
            "forbidden_field_names": ["password", "token", "secret", "api_key"],
            "secret_patterns": [{"id": "github-token", "regex": "\\bghp_[A-Za-z0-9]{20,}\\b"}],
            "private_reference_patterns": [{"id": "private-path", "regex": "(?:^|[\\s\\\"'])/(?:home|root|workspace|Users)/[^\\s\\\"']+"}]
        }
        self.sources = {
            "type": "qsol-substrate-source-registry", "schema_version": "1.0.0", "snapshot_date": "2026-08-15", "visibility": "public",
            "sources": [
                {"id": "src:readme", "record_type": "source", "visibility": "public", "epistemic_state": "known", "class": "first_party_documentation", "url": "https://github.com/QSOLKCB/DEMO/blob/main/README.md", "snapshot": {"kind": "git_commit", "commit": "a" * 40, "url": "https://github.com/QSOLKCB/DEMO/blob/" + "a" * 40 + "/README.md", "captured_at": "2026-08-15"}},
                {"id": "src:release", "record_type": "source", "visibility": "public", "epistemic_state": "known", "class": "release_record", "url": "https://github.com/QSOLKCB/DEMO/releases/tag/v1.0.0", "snapshot": {"kind": "release_tag_commit", "commit": "b" * 40, "url": "https://github.com/QSOLKCB/DEMO/tree/" + "b" * 40, "tag": "v1.0.0", "release_id": 1, "captured_at": "2026-08-15"}}
            ]
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
            {"id": "rel:demo-publishes", "record_type": "relationship", "visibility": "public", "epistemic_state": "known", "source": "project:demo", "relationship": "publishes", "target": "publication:demo-v1.0.0", "source_refs": ["src:release"]}
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
        for name in ["manifest", "public-boundary", "export-policy", "export-allowlist", "export-deny-policy", "validation-report"]:
            self._write(f"schema/{name}.schema.json", PERMISSIVE_SCHEMA)
        self._write("schema/substrate-fingerprint.schema.json", FINGERPRINT_SCHEMA)
        self._write("sources/index.json", self.sources)
        self._write("identity/public.json", self.identity)
        self._write("context/public.json", self.context)
        self._write("terminology/index.json", self.terminology)
        self._write("projects/index.json", self.projects)
        self._write("publications/index.json", self.publications)
        self._write("relationships/graph.json", self.relationships)
        (self.root / "chronology/current.jsonl").write_text("".join(json.dumps(e) + "\n" for e in self.events), encoding="utf-8")

    def _report(self):
        return validate_repository(self.root)

    def _codes(self):
        return [f.code for f in self._report().findings]

    def test_valid_fixture_passes(self):
        report = self._report()
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

    def test_secret_in_json_key_fails_without_echoing_secret(self):
        token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        self.projects["records"][0]["metadata"] = {token: "oops"}
        self._write_all()
        report = self._report()
        self.assertIn("boundary.secret", [f.code for f in report.findings])
        rendered = json.dumps([f.__dict__ for f in report.findings])
        self.assertNotIn(token, rendered)

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

    def test_wrong_record_type_in_projects_fails(self):
        self.projects["records"][0]["record_type"] = "publication"
        self.projects["records"][0]["id"] = "publication:not-a-project"
        self._write_all()
        self.assertIn("payload.record_type", self._codes())

    def test_public_boundary_is_secret_scanned(self):
        self.boundary["leak"] = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        self._write_all()
        self.assertIn("boundary.secret", self._codes())

    def test_publishes_source_must_be_project_even_if_repository_matches(self):
        self.identity["records"][0]["repository"] = "QSOLKCB/DEMO"
        self.relationships["edges"][1]["source"] = "person:demo"
        self._write_all()
        self.assertIn("relationship.publishes_source", self._codes())

    def test_generated_fingerprint_is_schema_validated(self):
        self.manifest["snapshot_date"] = "not-a-date"
        for wrapper in [self.sources, self.identity, self.context, self.terminology, self.projects, self.publications, self.relationships]:
            wrapper["snapshot_date"] = "not-a-date"
        self._write_all()
        findings = self._report().findings
        self.assertTrue(any(f.code == "schema.invalid" and "generated/substrate-fingerprint" in f.path for f in findings))

    def test_release_source_must_match_publication_repository(self):
        other = copy.deepcopy(self.sources["sources"][1])
        other["id"] = "src:other-release"
        other["url"] = "https://github.com/QSOLKCB/OTHER/releases/tag/v1.0.0"
        other["snapshot"]["url"] = "https://github.com/QSOLKCB/OTHER/tree/" + "b" * 40
        self.sources["sources"].append(other)
        self.publications["records"][0]["source_refs"] = ["src:other-release"]
        self._write_all()
        self.assertIn("release.repository", self._codes())

    def test_release_tag_and_commit_must_match_same_source(self):
        first = copy.deepcopy(self.sources["sources"][1])
        first["id"] = "src:tag-only"
        first["snapshot"]["commit"] = "c" * 40
        first["snapshot"]["url"] = "https://github.com/QSOLKCB/DEMO/tree/" + "c" * 40
        second = copy.deepcopy(self.sources["sources"][1])
        second["id"] = "src:commit-only"
        second["url"] = "https://github.com/QSOLKCB/DEMO/releases/tag/v2.0.0"
        second["snapshot"]["tag"] = "v2.0.0"
        self.sources["sources"] = [self.sources["sources"][0], first, second]
        self.publications["records"][0]["source_refs"] = ["src:tag-only", "src:commit-only"]
        self._write_all()
        self.assertIn("release.commit", self._codes())

    def test_event_doi_must_match_event_release_tag(self):
        second = copy.deepcopy(self.publications["records"][0])
        second.update({"id": "publication:demo-v2", "version": "2.0.0", "doi": "10.5281/zenodo.999999", "commit": None, "source_refs": ["src:readme"]})
        self.publications["records"].append(second)
        self.relationships["edges"].append({"id": "rel:demo-publishes-v2", "record_type": "relationship", "visibility": "public", "epistemic_state": "known", "source": "project:demo", "relationship": "publishes", "target": "publication:demo-v2", "source_refs": ["src:readme"]})
        self.events[0]["metadata"]["doi"] = "10.5281/zenodo.999999"
        self._write_all()
        self.assertIn("release.event_doi", self._codes())

    def test_release_origin_must_be_github(self):
        self.sources["sources"][1]["url"] = "https://evil.example/QSOLKCB/DEMO/releases/tag/v1.0.0"
        self._write_all()
        self.assertIn("release.origin", self._codes())

    def test_malformed_ontology_returns_report_not_exception(self):
        (self.root / "ai/ontology.json").write_text("{", encoding="utf-8")
        report = self._report()
        self.assertFalse(report.valid)
        self.assertIn("ontology.invalid", [f.code for f in report.findings])

    def test_malformed_release_snapshot_returns_report_not_exception(self):
        self.sources["sources"][1]["snapshot"] = None
        self._write_all()
        report = self._report()
        self.assertFalse(report.valid)
        self.assertIn("provenance.snapshot", [f.code for f in report.findings])

    def test_empty_deny_detectors_fail_closed(self):
        self.exclude["forbidden_source_path_globs"] = []
        self.exclude["forbidden_field_names"] = []
        self.exclude["secret_patterns"] = []
        self.exclude["private_reference_patterns"] = []
        self._write_all()
        self.assertIn("boundary.detector_disabled", self._codes())

    def test_unsupported_wrapper_schema_version_fails(self):
        self.projects["schema_version"] = "2.0.0"
        self._write_all()
        self.assertIn("payload.schema_version", self._codes())

    def test_machine_contract_schema_registration_is_required(self):
        self.manifest["machine_contract_schemas"] = {}
        self._write_all()
        self.assertIn("schema.registration", self._codes())


if __name__ == "__main__":
    unittest.main()
