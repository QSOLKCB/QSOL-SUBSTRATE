import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from toolless_core import (  # noqa: E402
    CORE_GUARDS,
    PROFILE_NAMES,
    CapsuleError,
    _canonical_items,
    _load_json,
    _parse_capsule_items,
    build_toolless_bundle,
    portable_token_count,
    validate_toolless_bundle,
)


class ToollessCapsuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output = Path(self.tmp.name) / "toolless"
        self.commit = "a" * 40

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, commit=None):
        return build_toolless_bundle(ROOT, self.output, commit or self.commit)

    def _codes(self):
        return [finding.code for finding in validate_toolless_bundle(ROOT, self.output)]

    def _profile_text(self, name):
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        entry = next(item for item in manifest["profiles"] if item["name"] == name)
        return (self.output / entry["file"]).read_text(encoding="utf-8")

    def test_builds_three_profiles_and_validates(self):
        manifest = self._build()
        self.assertEqual([entry["name"] for entry in manifest["profiles"]], list(PROFILE_NAMES))
        self.assertEqual(validate_toolless_bundle(ROOT, self.output), [])

    def test_build_is_deterministic_for_same_commit(self):
        first = self._build()
        first_files = {path.relative_to(self.output).as_posix(): path.read_bytes() for path in self.output.rglob("*") if path.is_file()}
        shutil.rmtree(self.output)
        second = self._build()
        second_files = {path.relative_to(self.output).as_posix(): path.read_bytes() for path in self.output.rglob("*") if path.is_file()}
        self.assertEqual(first["bundle_sha256"], second["bundle_sha256"])
        self.assertEqual(first_files, second_files)

    def test_source_commit_changes_bundle_identity_not_substrate_fingerprint(self):
        first = self._build("a" * 40)
        shutil.rmtree(self.output)
        second = self._build("b" * 40)
        self.assertEqual(first["substrate"]["substrate_sha256"], second["substrate"]["substrate_sha256"])
        self.assertNotEqual(first["bundle_sha256"], second["bundle_sha256"])
        self.assertEqual(second["substrate"]["source_commit"], "b" * 40)

    def test_invalid_source_commit_fails_closed(self):
        with self.assertRaises(CapsuleError):
            self._build("not-a-commit")

    def test_profiles_respect_portable_token_budgets(self):
        manifest = self._build()
        for entry in manifest["profiles"]:
            text = (self.output / entry["file"]).read_text(encoding="utf-8")
            self.assertEqual(portable_token_count(text), entry["portable_tokens"])
            self.assertLessEqual(entry["portable_tokens"], entry["token_budget"])

    def test_full_contains_every_canonical_payload_item(self):
        manifest = self._build()
        source_manifest = _load_json(ROOT / "ai/manifest.json")
        canonical = _canonical_items(ROOT, source_manifest)
        full = next(entry for entry in manifest["profiles"] if entry["name"] == "FULL")
        parsed, _ = _parse_capsule_items((self.output / full["file"]).read_text(encoding="utf-8"))
        self.assertEqual(set(parsed), {item.item_id for item in canonical})
        self.assertEqual(full["omitted_items"], 0)
        self.assertFalse(full["truncated"])

    def test_micro_repeats_critical_epistemic_guards(self):
        self._build()
        text = self._profile_text("MICRO")
        self.assertIn("[SMALL_MODEL_GUARD_REPEAT]", text)
        for guard in CORE_GUARDS:
            self.assertGreaterEqual(text.count(guard), 2)
        self.assertGreaterEqual(text.count("NO_TOOLS=true"), 2)

    def test_all_profiles_declare_no_tools_and_snapshot_limit(self):
        manifest = self._build()
        snapshot = manifest["substrate"]["snapshot_date"]
        for entry in manifest["profiles"]:
            text = (self.output / entry["file"]).read_text(encoding="utf-8")
            self.assertIn("NO_TOOLS=true", text)
            self.assertIn(f"SNAPSHOT_DATE={snapshot}", text)
            self.assertIn("If a question requires post-snapshot current state", text)
            self.assertIn("OMISSION_MEANS=UNAVAILABLE_NOT_FALSE", text)

    def test_micro_preserves_core_identity_and_term_records(self):
        self._build()
        parsed, _ = _parse_capsule_items(self._profile_text("MICRO"))
        self.assertIn("person:trent-slade", parsed)
        self.assertIn("org:qsolkcb", parsed)
        self.assertIn("term:qsol", parsed)
        self.assertIn("term:qsol-substrate", parsed)

    def test_source_refs_are_closed_inside_every_capsule(self):
        manifest = self._build()
        for entry in manifest["profiles"]:
            parsed, _ = _parse_capsule_items((self.output / entry["file"]).read_text(encoding="utf-8"))
            source_ids = {item_id for item_id, (kind, _, _) in parsed.items() if kind == "source"}
            for _, (_, _, payload) in parsed.items():
                refs = payload.get("source_refs", [])
                if isinstance(refs, list):
                    self.assertTrue(set(ref for ref in refs if isinstance(ref, str)).issubset(source_ids))

    def test_relationship_endpoints_are_closed_inside_every_capsule(self):
        manifest = self._build()
        for entry in manifest["profiles"]:
            parsed, _ = _parse_capsule_items((self.output / entry["file"]).read_text(encoding="utf-8"))
            for item_id, (kind, _, payload) in parsed.items():
                if kind != "relationship":
                    continue
                self.assertIn(payload["source"], parsed, item_id)
                self.assertIn(payload["target"], parsed, item_id)

    def test_full_inlines_high_risk_project_boundaries(self):
        self._build()
        text = self._profile_text("FULL")
        self.assertIn("BOUNDARY\tproject:whoami-18437\tSATIRE != BIOGRAPHY", text)
        self.assertIn("BOUNDARY\tproject:deepseekc64\tFORMALIZATION != PHYSICAL_TRUTH", text)
        self.assertIn("BOUNDARY\tproject:deepseekc64\tOBSERVED_OR_ARCHIVED_MODEL_OUTPUT != GENERAL_MODEL_IDENTITY", text)
        self.assertIn("BOUNDARY\tproject:uff\tFORMALIZATION != PHYSICAL_TRUTH", text)

    def test_tampered_canonical_item_fails_hash_and_fact_transform(self):
        self._build()
        path = self.output / "QSOL-SUBSTRATE-FULL.txt"
        text = path.read_text(encoding="utf-8")
        self.assertIn("Public vendor-neutral context substrate", text)
        path.write_text(text.replace("Public vendor-neutral context substrate", "Invented private omniscience substrate", 1), encoding="utf-8")
        codes = self._codes()
        self.assertIn("toolless.file_hash", codes)
        self.assertIn("toolless.fact_transform", codes)

    def test_missing_source_item_fails_provenance_closure(self):
        self._build()
        path = self.output / "QSOL-SUBSTRATE-FULL.txt"
        lines = path.read_text(encoding="utf-8").splitlines()
        target = next(line for line in lines if line.startswith("ITEM\tsource\t") and '"id":"src:qsol-readme"' in line)
        lines.remove(target)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        codes = self._codes()
        self.assertIn("toolless.provenance_closure", codes)

    def test_missing_relationship_endpoint_fails_closed(self):
        self._build()
        path = self.output / "QSOL-SUBSTRATE-FULL.txt"
        lines = path.read_text(encoding="utf-8").splitlines()
        target = next(line for line in lines if line.startswith("ITEM\tproject\t") and '"id":"project:qec"' in line)
        lines.remove(target)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        codes = self._codes()
        self.assertIn("toolless.relationship_closure", codes)

    def test_manifest_missing_profile_fails_schema_and_profile_set(self):
        self._build()
        path = self.output / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["profiles"] = manifest["profiles"][:-1]
        path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        codes = self._codes()
        self.assertIn("toolless.schema", codes)
        self.assertIn("toolless.profile_set", codes)

    def test_successful_build_preserves_repository_source_files(self):
        watched = [ROOT / "ai/manifest.json", ROOT / "projects/index.json", ROOT / "tools/toolless_core.py"]
        before = {path: path.read_bytes() for path in watched}
        self._build()
        after = {path: path.read_bytes() for path in watched}
        self.assertEqual(before, after)

    def test_output_cannot_replace_or_escape_repository_root(self):
        with self.assertRaises(CapsuleError):
            build_toolless_bundle(ROOT, ROOT, self.commit)
        with self.assertRaises(CapsuleError):
            build_toolless_bundle(ROOT, ROOT.parent, self.commit)


if __name__ == "__main__":
    unittest.main()
