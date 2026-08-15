import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.export_public_substrate import ExportError, run_export


class ExportPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "private"
        self.substrate = self.root / "substrate"
        self.source.mkdir()
        (self.substrate / "ai").mkdir(parents=True)
        (self.substrate / "sources").mkdir()
        (self.substrate / "projects").mkdir()
        (self.substrate / "public_export").mkdir()

        (self.source / "manifest.json").write_text(
            json.dumps({"type": "qsol-context-manifest", "protocol": "QSOL-CONTEXT"})
            + "\n",
            encoding="utf-8",
        )
        (self.substrate / "ai/manifest.json").write_text(
            json.dumps(
                {
                    "type": "qsol-substrate-manifest",
                    "canonical_payload_files": [
                        "sources/index.json",
                        "projects/index.json",
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.substrate / "sources/index.json").write_text(
            json.dumps(
                {
                    "type": "qsol-substrate-source-registry",
                    "visibility": "public",
                    "sources": [
                        {
                            "id": "src:example-readme",
                            "record_type": "source",
                            "visibility": "public",
                            "epistemic_state": "known",
                            "class": "first_party_documentation",
                            "url": "https://example.invalid/readme",
                            "summary": "synthetic public source",
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.substrate / "projects/index.json").write_text(
            json.dumps(
                {
                    "type": "qsol-substrate-project-registry",
                    "visibility": "public",
                    "records": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        self.policy = {
            "type": "qsol-substrate-export-policy",
            "schema_version": "1.0.0",
            "export_policy": "explicit_allow_only",
            "source_contract": {
                "manifest_path": "manifest.json",
                "protocol_pointer": "/protocol",
                "protocol_equals": "QSOL-CONTEXT",
            },
            "output_manifest": "export-manifest.json",
            "immutable_payload_files": ["sources/index.json"],
        }
        self.exclude = {
            "type": "qsol-substrate-export-deny-policy",
            "schema_version": "1.0.0",
            "default": "deny_on_match",
            "forbidden_source_path_globs": [".env", "**/.env", "secrets/**"],
            "forbidden_field_names": [
                "password",
                "secret",
                "token",
                "api_key",
                "private_key",
            ],
            "secret_patterns": [
                {"id": "github-token", "regex": "\\bghp_[A-Za-z0-9]{20,}\\b"},
                {"id": "private-key-pem", "regex": "-----BEGIN PRIVATE KEY-----"},
            ],
            "private_reference_patterns": [
                {
                    "id": "private-source-url",
                    "regex": "https?://github\\.com/QSOLKCB/QSOL-CONTEXT(?:/|\\b)",
                },
                {
                    "id": "unix-private-absolute-path",
                    "regex": "(?:^|[\\s\"'=:(])/(?:home|root|Users|workspace|workspaces|tmp|var/tmp|mnt|media)/[^\\s\"',;)}\\]]+",
                },
            ],
        }
        self._write_configs([])

    def tearDown(self):
        self.tmp.cleanup()

    def _write_configs(self, entries):
        (self.substrate / "public_export/policy.json").write_text(
            json.dumps(self.policy) + "\n", encoding="utf-8"
        )
        (self.substrate / "public_export/include.json").write_text(
            json.dumps(
                {
                    "type": "qsol-substrate-export-allowlist",
                    "schema_version": "1.0.0",
                    "default": "deny",
                    "entries": entries,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.substrate / "public_export/exclude.json").write_text(
            json.dumps(self.exclude) + "\n", encoding="utf-8"
        )

    def _directive(
        self,
        fields,
        *,
        source_ref="src:example-readme",
        record_type="project",
        target_path="projects/index.json",
        collection_pointer="/records",
    ):
        return {
            "id": "synthetic-project",
            "enabled": True,
            "visibility": "public",
            "source": {
                "path": "projects/index.json",
                "collection_pointer": "/projects",
                "match": {
                    "pointer": "/id",
                    "equals": "project.private-example",
                },
            },
            "target": {
                "path": target_path,
                "collection_pointer": collection_pointer,
                "allow_create": True,
                "sort_by": "/id",
            },
            "record": {
                "id": "project:public-example",
                "record_type": record_type,
                "epistemic_state": "known",
                "public_source_refs": [source_ref],
                "fields": fields,
            },
        }

    def _source_projects(self, record):
        (self.source / "projects").mkdir(exist_ok=True)
        (self.source / "projects/index.json").write_text(
            json.dumps({"projects": [record]}) + "\n", encoding="utf-8"
        )

    def _run(self, name="out", **kwargs):
        return run_export(
            source_root=self.source,
            substrate_root=self.substrate,
            output_root=self.root / name,
            policy_path=self.substrate / "public_export/policy.json",
            include_path=self.substrate / "public_export/include.json",
            exclude_path=self.substrate / "public_export/exclude.json",
            **kwargs,
        )

    def test_empty_allowlist_exports_only_public_baseline(self):
        manifest = self._run()
        self.assertEqual(manifest["applied_directives"], [])
        exported = json.loads((self.root / "out/projects/index.json").read_text())
        self.assertEqual(exported["records"], [])
        self.assertEqual(manifest["export_policy"], "explicit_allow_only")

    def test_explicit_fields_export_and_unselected_private_fields_do_not(self):
        self._source_projects(
            {
                "id": "project.private-example",
                "name": "Public Example",
                "summary": "Safe public summary",
                "private_note": "DO NOT EXPORT ME",
                "sources": [{"type": "private", "ref": "internal-record"}],
            }
        )
        self._write_configs(
            [
                self._directive(
                    [
                        {
                            "from": "/name",
                            "to": "/name",
                            "visibility": "public",
                        },
                        {
                            "from": "/summary",
                            "to": "/summary",
                            "visibility": "public",
                        },
                    ]
                )
            ]
        )
        self._run()
        record = json.loads((self.root / "out/projects/index.json").read_text())[
            "records"
        ][0]
        self.assertEqual(record["name"], "Public Example")
        self.assertEqual(record["source_refs"], ["src:example-readme"])
        self.assertNotIn("private_note", record)
        self.assertNotIn("sources", record)
        self.assertNotIn("DO NOT EXPORT ME", json.dumps(record))

    def test_missing_field_visibility_fails_closed(self):
        self._source_projects({"id": "project.private-example", "name": "Example"})
        self._write_configs(
            [self._directive([{"from": "/name", "to": "/name"}])]
        )
        with self.assertRaisesRegex(ExportError, "visibility='public'"):
            self._run()

    def test_unknown_public_provenance_ref_fails_closed(self):
        self._source_projects({"id": "project.private-example", "name": "Example"})
        self._write_configs(
            [
                self._directive(
                    [{"from": "/name", "to": "/name", "visibility": "public"}],
                    source_ref="src:not-in-public-registry",
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "unknown or non-public provenance ref"):
            self._run()

    def test_secret_in_selected_value_fails_closed(self):
        self._source_projects(
            {
                "id": "project.private-example",
                "name": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            }
        )
        self._write_configs(
            [
                self._directive(
                    [{"from": "/name", "to": "/name", "visibility": "public"}]
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "secret pattern"):
            self._run()

    def test_private_reference_in_output_fails_closed(self):
        self._source_projects(
            {
                "id": "project.private-example",
                "name": "Example",
                "repository": "https://github.com/QSOLKCB/QSOL-CONTEXT/private/path",
            }
        )
        self._write_configs(
            [
                self._directive(
                    [
                        {
                            "from": "/name",
                            "to": "/name",
                            "visibility": "public",
                        },
                        {
                            "from": "/repository",
                            "to": "/repository",
                            "visibility": "public",
                        },
                    ]
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "private-reference pattern"):
            self._run()

    def test_explicit_redaction_emits_placeholder_not_source_value(self):
        self._source_projects(
            {
                "id": "project.private-example",
                "name": "Example",
                "note": "non-public detail",
            }
        )
        self._write_configs(
            [
                self._directive(
                    [
                        {
                            "from": "/name",
                            "to": "/name",
                            "visibility": "public",
                        },
                        {
                            "redact_from": "/note",
                            "to": "/metadata/note",
                            "visibility": "public",
                            "replacement": "[REDACTED]",
                        },
                    ]
                )
            ]
        )
        manifest = self._run()
        record = json.loads((self.root / "out/projects/index.json").read_text())[
            "records"
        ][0]
        self.assertEqual(record["metadata"]["note"], "[REDACTED]")
        self.assertNotIn("non-public detail", json.dumps(record))
        self.assertTrue(manifest["redaction_applied"])

    def test_repeated_runs_have_identical_public_manifest(self):
        first = self._run("out1")
        second = self._run("out2")
        self.assertEqual(first, second)
        self.assertEqual(
            (self.root / "out1/export-manifest.json").read_bytes(),
            (self.root / "out2/export-manifest.json").read_bytes(),
        )

    def test_private_audit_manifest_cannot_live_inside_public_output(self):
        with self.assertRaisesRegex(ExportError, "audit manifest"):
            run_export(
                source_root=self.source,
                substrate_root=self.substrate,
                output_root=self.root / "out",
                policy_path=self.substrate / "public_export/policy.json",
                include_path=self.substrate / "public_export/include.json",
                exclude_path=self.substrate / "public_export/exclude.json",
                audit_manifest=self.root / "out/private-audit.json",
            )

    def test_output_equal_source_rejected_even_with_force(self):
        with self.assertRaisesRegex(ExportError, "must not overlap"):
            run_export(
                source_root=self.source,
                substrate_root=self.substrate,
                output_root=self.source,
                policy_path=self.substrate / "public_export/policy.json",
                include_path=self.substrate / "public_export/include.json",
                exclude_path=self.substrate / "public_export/exclude.json",
                force=True,
            )

    def test_output_ancestor_of_inputs_rejected_even_with_force(self):
        with self.assertRaisesRegex(ExportError, "must not overlap"):
            run_export(
                source_root=self.source,
                substrate_root=self.substrate,
                output_root=self.root,
                policy_path=self.substrate / "public_export/policy.json",
                include_path=self.substrate / "public_export/include.json",
                exclude_path=self.substrate / "public_export/exclude.json",
                force=True,
            )

    def test_output_inside_substrate_cannot_be_overridden(self):
        with self.assertRaisesRegex(ExportError, "must not overlap"):
            run_export(
                source_root=self.source,
                substrate_root=self.substrate,
                output_root=self.substrate / "dist",
                policy_path=self.substrate / "public_export/policy.json",
                include_path=self.substrate / "public_export/include.json",
                exclude_path=self.substrate / "public_export/exclude.json",
                allow_output_inside_repo=True,
            )

    def test_unsupported_record_type_fails_closed(self):
        self._source_projects({"id": "project.private-example", "name": "Example"})
        self._write_configs(
            [
                self._directive(
                    [{"from": "/name", "to": "/name", "visibility": "public"}],
                    record_type="projet",
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "unsupported record_type"):
            self._run()

    def test_unsupported_epistemic_state_fails_closed(self):
        self._source_projects({"id": "project.private-example", "name": "Example"})
        directive = self._directive(
            [{"from": "/name", "to": "/name", "visibility": "public"}]
        )
        directive["record"]["epistemic_state"] = "certainly"
        self._write_configs([directive])
        with self.assertRaisesRegex(ExportError, "unsupported epistemic_state"):
            self._run()

    def test_secret_pattern_in_object_key_fails_closed(self):
        self._source_projects(
            {
                "id": "project.private-example",
                "metadata": {"ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456": "account"},
            }
        )
        self._write_configs(
            [
                self._directive(
                    [
                        {
                            "from": "/metadata",
                            "to": "/metadata",
                            "visibility": "public",
                        }
                    ]
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "secret pattern"):
            self._run()

    def test_common_private_unix_paths_fail_closed(self):
        for idx, path in enumerate(
            [
                "/workspace/QSOL-CONTEXT/private.json",
                "/root/.config/private.json",
                "/Users/alice/private/data.json",
            ]
        ):
            with self.subTest(path=path):
                self._source_projects(
                    {"id": "project.private-example", "name": path}
                )
                self._write_configs(
                    [
                        self._directive(
                            [
                                {
                                    "from": "/name",
                                    "to": "/name",
                                    "visibility": "public",
                                }
                            ]
                        )
                    ]
                )
                with self.assertRaisesRegex(ExportError, "private-reference pattern"):
                    self._run(f"out{idx}")

    def test_arbitrary_nested_array_target_fails_closed(self):
        baseline = json.loads((self.substrate / "projects/index.json").read_text())
        baseline["records"].append(
            {
                "id": "project:existing",
                "record_type": "project",
                "visibility": "public",
                "epistemic_state": "known",
                "source_refs": [],
            }
        )
        (self.substrate / "projects/index.json").write_text(
            json.dumps(baseline) + "\n"
        )
        self._source_projects({"id": "project.private-example", "name": "Example"})
        self._write_configs(
            [
                self._directive(
                    [{"from": "/name", "to": "/name", "visibility": "public"}],
                    collection_pointer="/records/0/source_refs",
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "approved canonical record collection"):
            self._run()

    def test_wrong_record_type_for_collection_fails_closed(self):
        self._source_projects({"id": "project.private-example", "name": "Example"})
        self._write_configs(
            [
                self._directive(
                    [{"from": "/name", "to": "/name", "visibility": "public"}],
                    record_type="publication",
                )
            ]
        )
        with self.assertRaisesRegex(ExportError, "not allowed in"):
            self._run()

    def test_manifest_path_cannot_collide_with_payload(self):
        self.policy["output_manifest"] = "projects/index.json"
        self._write_configs([])
        with self.assertRaisesRegex(ExportError, "must not collide"):
            self._run()

    def test_symlinked_source_into_denied_directory_fails_closed(self):
        (self.source / "secrets").mkdir()
        (self.source / "secrets/records.json").write_text(
            json.dumps(
                {"projects": [{"id": "project.private-example", "name": "Example"}]}
            )
            + "\n"
        )
        try:
            os.symlink(
                self.source / "secrets/records.json", self.source / "records.json"
            )
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        directive = self._directive(
            [{"from": "/name", "to": "/name", "visibility": "public"}]
        )
        directive["source"]["path"] = "records.json"
        self._write_configs([directive])
        with self.assertRaisesRegex(ExportError, "symlinked source paths"):
            self._run()

    def test_source_registry_is_immutable_even_if_policy_omits_it(self):
        self.policy["immutable_payload_files"] = []
        self._source_projects({"id": "project.private-example", "name": "Example"})
        directive = self._directive(
            [{"from": "/name", "to": "/name", "visibility": "public"}],
            target_path="sources/index.json",
            collection_pointer="/sources",
            record_type="source",
        )
        self._write_configs([directive])
        with self.assertRaisesRegex(ExportError, "immutable"):
            self._run()


if __name__ == "__main__":
    unittest.main()
