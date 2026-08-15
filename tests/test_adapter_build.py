import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from adapter_core import (  # noqa: E402
    AdapterError,
    REQUIRED_ADAPTER_IDS,
    build_adapter_bundle,
    validate_adapter_bundle,
)


class PortableAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output = Path(self.tmp.name) / "adapters"
        self.commit = "a" * 40

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, commit=None):
        return build_adapter_bundle(ROOT, self.output, commit or self.commit)

    def _codes(self):
        return [finding.code for finding in validate_adapter_bundle(ROOT, self.output)]

    def test_builds_all_phase4_adapters_and_validates(self):
        manifest = self._build()
        self.assertEqual([entry["id"] for entry in manifest["adapters"]], list(REQUIRED_ADAPTER_IDS))
        self.assertEqual(len(manifest["adapters"]), 8)
        self.assertEqual(validate_adapter_bundle(ROOT, self.output), [])

    def test_successful_build_preserves_repository_source_tree(self):
        manifest_path = ROOT / "ai/manifest.json"
        before = manifest_path.read_bytes()
        self._build()
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(manifest_path.read_bytes(), before)
        self.assertTrue((ROOT / "tools/adapter_core.py").is_file())

    def test_build_is_deterministic_for_same_commit(self):
        first = self._build()
        first_manifest = (self.output / "manifest.json").read_bytes()
        first_files = {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        shutil.rmtree(self.output)
        second = self._build()
        second_manifest = (self.output / "manifest.json").read_bytes()
        second_files = {p.relative_to(self.output).as_posix(): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(first["adapter_bundle_sha256"], second["adapter_bundle_sha256"])
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_files, second_files)

    def test_source_commit_changes_reproducible_identity_not_substrate_fingerprint(self):
        first = self._build("a" * 40)
        shutil.rmtree(self.output)
        second = self._build("b" * 40)
        self.assertEqual(first["substrate"]["substrate_sha256"], second["substrate"]["substrate_sha256"])
        self.assertNotEqual(first["adapter_bundle_sha256"], second["adapter_bundle_sha256"])
        self.assertEqual(second["substrate"]["source_commit"], "b" * 40)

    def test_invalid_source_commit_fails_closed(self):
        with self.assertRaises(AdapterError):
            self._build("not-a-commit")

    def test_tampered_knowledge_projection_fails(self):
        self._build()
        path = self.output / "generic/QSOL-SUBSTRATE.txt"
        path.write_text(path.read_text(encoding="utf-8").replace("UNKNOWN != FALSE", "UNKNOWN == FALSE", 1), encoding="utf-8")
        codes = self._codes()
        self.assertIn("adapter.file_hash", codes)

    def test_tampered_nonknowledge_file_fails_bundle_hash(self):
        self._build()
        path = self.output / "grok-build/AGENTS.md"
        path.write_text(path.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
        self.assertIn("adapter.file_hash", self._codes())

    def test_missing_adapter_entry_fails(self):
        self._build()
        path = self.output / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["adapters"] = manifest["adapters"][:-1]
        path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
        codes = self._codes()
        self.assertIn("adapter.schema", codes)
        self.assertIn("adapter.set", codes)

    def test_adapter_manifest_records_snapshot_commit_and_hash(self):
        manifest = self._build()
        substrate = manifest["substrate"]
        self.assertEqual(substrate["version"], f"snapshot-{substrate['snapshot_date']}")
        self.assertEqual(substrate["source_commit"], self.commit)
        self.assertRegex(substrate["substrate_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(manifest["adapter_bundle_sha256"], r"^[0-9a-f]{64}$")

    def test_grok_build_rules_fit_native_rules_file_cap(self):
        self._build()
        self.assertLess(len((self.output / "grok-build/AGENTS.md").read_text(encoding="utf-8")), 10_000)
        skill = (self.output / "grok-build/.grok/skills/qsol-substrate/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: qsol-substrate", skill)
        self.assertIn("UNKNOWN", skill)

    def test_xai_retrieval_export_has_collection_transport_metadata(self):
        manifest = self._build()
        upload = json.loads((self.output / "xai-retrieval/upload-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(upload["adapter_id"], "adapter:xai-retrieval")
        self.assertEqual(upload["substrate"]["source_commit"], self.commit)
        self.assertEqual(upload["substrate"]["substrate_sha256"], manifest["substrate"]["substrate_sha256"])
        self.assertEqual(upload["search_transport"]["search_api"], "https://api.x.ai/v1/documents/search")

    def test_openai_anthropic_and_ollama_templates_are_transport_only(self):
        self._build()
        openai = json.loads((self.output / "openai/request.example.json").read_text(encoding="utf-8"))
        anthropic = json.loads((self.output / "anthropic/request.example.json").read_text(encoding="utf-8"))
        modelfile = (self.output / "ollama/Modelfile.template").read_text(encoding="utf-8")
        self.assertEqual(openai["model"], "REPLACE_WITH_MODEL_ID")
        self.assertIn("TRANSPORT_ONLY=true", openai["instructions"])
        self.assertEqual(anthropic["model"], "REPLACE_WITH_MODEL_ID")
        self.assertIn("TRANSPORT_ONLY=true", anthropic["system"])
        self.assertIn("FROM REPLACE_WITH_BASE_MODEL", modelfile)
        self.assertNotIn("sk-", json.dumps(openai) + json.dumps(anthropic))

    def test_output_cannot_replace_or_escape_repository_root(self):
        with self.assertRaises(AdapterError):
            build_adapter_bundle(ROOT, ROOT, self.commit)
        with self.assertRaises(AdapterError):
            build_adapter_bundle(ROOT, ROOT.parent, self.commit)


if __name__ == "__main__":
    unittest.main()
