import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from projection_core import (  # noqa: E402
    EPISTEMIC_RULES,
    YEAH_NAH_EXPERIMENTAL_RULES,
    build_projection_bundle,
    compatibility_fingerprint,
    compatibility_mismatches,
    validate_compatibility_manifest,
    validate_projection_bundle,
)
from toolless_core import _canonical_items, _load_json  # noqa: E402
from vector_core import (  # noqa: E402
    DIMENSION,
    _context_closure,
    _read_records,
    build_vector_bundle,
    retrieve,
    validate_vector_bundle,
)


class Phase6ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.vectors = self.base / "vectors"
        self.projections = self.base / "projections"
        self.commit = "c" * 40

    def tearDown(self):
        self.tmp.cleanup()

    def _build_vectors(self, commit=None):
        return build_vector_bundle(ROOT, self.vectors, commit or self.commit)

    def _build_projections(self, commit=None):
        return build_projection_bundle(ROOT, self.projections, commit or self.commit)

    def _compatibility(self, **updates):
        value = {
            "type": "qsol-model-projection-compatibility",
            "schema_version": "1.0.0",
            "projection_kind": "kv_cache",
            "model_id": "example/model",
            "model_revision": "revision-1",
            "architecture": "ExampleForCausalLM",
            "tokenizer_id": "example/tokenizer",
            "tokenizer_sha256": "d" * 64,
            "context_length": 32768,
            "hidden_size": 4096,
            "num_hidden_layers": 32,
            "num_attention_heads": 32,
            "kv_layout_version": "v1",
        }
        value.update(updates)
        return value

    def test_vector_bundle_builds_and_validates(self):
        manifest = self._build_vectors()
        self.assertGreater(manifest["record_count"], 0)
        self.assertEqual(manifest["embedding"]["id"], "qsol-hash-embed-v1")
        self.assertEqual(validate_vector_bundle(ROOT, self.vectors), [])

    def test_vector_build_is_deterministic(self):
        first = self._build_vectors()
        first_files = {p.name: p.read_bytes() for p in self.vectors.iterdir() if p.is_file()}
        shutil.rmtree(self.vectors)
        second = self._build_vectors()
        second_files = {p.name: p.read_bytes() for p in self.vectors.iterdir() if p.is_file()}
        self.assertEqual(first["bundle_sha256"], second["bundle_sha256"])
        self.assertEqual(first_files, second_files)

    def test_vector_source_commit_changes_projection_identity_not_substrate(self):
        first = self._build_vectors("a" * 40)
        shutil.rmtree(self.vectors)
        second = self._build_vectors("b" * 40)
        self.assertEqual(first["substrate"]["substrate_sha256"], second["substrate"]["substrate_sha256"])
        self.assertNotEqual(first["bundle_sha256"], second["bundle_sha256"])

    def test_vector_record_count_matches_canonical_items(self):
        manifest = self._build_vectors()
        source_manifest = _load_json(ROOT / "ai/manifest.json")
        canonical = _canonical_items(ROOT, source_manifest)
        self.assertEqual(manifest["record_count"], len(canonical))

    def test_embedding_binary_has_exact_shape(self):
        manifest = self._build_vectors()
        data = (self.vectors / "embeddings.f16").read_bytes()
        self.assertEqual(len(data), manifest["record_count"] * DIMENSION * 2)

    def test_vector_records_keep_ids_and_provenance_outside_embedding(self):
        self._build_vectors()
        rows = _read_records(self.vectors / "records.jsonl")
        publication = next(row for row in rows if row["canonical_id"] == "publication:uff-v5.2.0")
        self.assertEqual(publication["metadata"]["epistemic_state"], "known")
        self.assertIn("src:uff-v5.2.0-release", publication["metadata"]["source_refs"])
        self.assertEqual(publication["payload"]["doi"], "10.5281/zenodo.21911644")

    def test_nearest_neighbor_retrieval_hits_exact_identity(self):
        self._build_vectors()
        rows = _read_records(self.vectors / "records.jsonl")
        embeddings = (self.vectors / "embeddings.f16").read_bytes()
        ranked = retrieve(rows, embeddings, "publication:uff-v5.2.0 10.5281/zenodo.21911644", top_k=5)
        self.assertIn("publication:uff-v5.2.0", [row["canonical_id"] for row in ranked])

    def test_retrieval_closure_adds_public_provenance(self):
        self._build_vectors()
        rows = _read_records(self.vectors / "records.jsonl")
        closed = _context_closure(["publication:uff-v5.2.0"], rows)
        self.assertIn("publication:uff-v5.2.0", closed)
        self.assertIn("src:uff-v5.2.0-release", closed)

    def test_reference_retrieval_report_is_provenance_closed_and_compact(self):
        self._build_vectors()
        report = json.loads((self.vectors / "retrieval-report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["all_contexts_provenance_closed"])
        self.assertGreater(report["hit_rate"], 0.5)
        self.assertLess(report["average_closed_context_portable_tokens"], 8192)

    def test_vector_tamper_fails_deterministic_rebuild(self):
        self._build_vectors()
        path = self.vectors / "records.jsonl"
        path.write_text(path.read_text(encoding="utf-8").replace("Trent Slade", "Invented Person", 1), encoding="utf-8")
        codes = [finding.code for finding in validate_vector_bundle(ROOT, self.vectors)]
        self.assertIn("vector.deterministic_mismatch", codes)

    def test_vector_extra_file_is_rejected(self):
        self._build_vectors()
        (self.vectors / "extra.txt").write_text("not part of the bundle", encoding="utf-8")
        codes = [finding.code for finding in validate_vector_bundle(ROOT, self.vectors)]
        self.assertIn("vector.file_set", codes)

    def test_vector_symlink_is_rejected(self):
        self._build_vectors()
        target = self.base / "outside.bin"
        target.write_bytes((self.vectors / "embeddings.f16").read_bytes())
        (self.vectors / "embeddings.f16").unlink()
        (self.vectors / "embeddings.f16").symlink_to(target)
        codes = [finding.code for finding in validate_vector_bundle(ROOT, self.vectors)]
        self.assertIn("vector.symlink", codes)

    def test_vector_output_cannot_replace_repository_source(self):
        with self.assertRaises(Exception):
            build_vector_bundle(ROOT, ROOT / "tools", self.commit)

    def test_projection_bundle_builds_and_validates(self):
        manifest = self._build_projections()
        self.assertEqual(len(manifest["recipes"]), 6)
        self.assertEqual(validate_projection_bundle(ROOT, self.projections), [])

    def test_epistemic_prefix_contains_core_and_yeah_nah_rules(self):
        self._build_projections()
        text = (self.projections / "epistemic-prefix.txt").read_text(encoding="utf-8")
        for rule in EPISTEMIC_RULES + YEAH_NAH_EXPERIMENTAL_RULES:
            self.assertIn(rule, text)
        self.assertIn("CANONICAL_TRUTH_AUTHORITY=false", text)

    def test_projection_recipes_cover_phase6_mechanisms(self):
        self._build_projections()
        recipes = json.loads((self.projections / "projection-recipes.json").read_text(encoding="utf-8"))
        ids = {recipe["id"] for recipe in recipes["recipes"]}
        self.assertEqual(ids, {
            "soft-prompt-prefix-tuning",
            "prompt-tuned-virtual-tokens",
            "lora-epistemic-adapter",
            "prefilled-kv-cache",
            "reusable-prefix-state",
            "hybrid-epistemic-prefix-factual-text",
        })
        self.assertIn("does not claim", recipes["non_claim"])

    def test_delivery_matrix_defers_model_behavior_measurement_to_phase7(self):
        self._build_projections()
        matrix = json.loads((self.projections / "delivery-matrix.json").read_text(encoding="utf-8"))
        self.assertTrue(matrix["phase7_measurement_required"])
        self.assertEqual([mode["id"] for mode in matrix["modes"]], ["textual", "epistemic-prefix", "hybrid"])

    def test_compatibility_manifest_schema_accepts_complete_identity(self):
        self.assertEqual(validate_compatibility_manifest(ROOT, self._compatibility()), [])

    def test_exact_model_compatibility_is_stable(self):
        expected = self._compatibility()
        actual = dict(expected)
        self.assertEqual(compatibility_mismatches(expected, actual), [])
        self.assertEqual(compatibility_fingerprint(expected), compatibility_fingerprint(actual))

    def test_tokenizer_change_invalidates_projection(self):
        expected = self._compatibility()
        actual = self._compatibility(tokenizer_sha256="e" * 64)
        self.assertIn("tokenizer_sha256", compatibility_mismatches(expected, actual))

    def test_architecture_change_invalidates_projection(self):
        expected = self._compatibility()
        actual = self._compatibility(architecture="DifferentArchitecture")
        self.assertIn("architecture", compatibility_mismatches(expected, actual))

    def test_projection_tamper_fails_deterministic_rebuild(self):
        self._build_projections()
        path = self.projections / "epistemic-prefix.txt"
        path.write_text(path.read_text(encoding="utf-8") + "INVENTED_FACT=true\n", encoding="utf-8")
        codes = [finding.code for finding in validate_projection_bundle(ROOT, self.projections)]
        self.assertIn("projection.deterministic_mismatch", codes)

    def test_projection_extra_file_is_rejected(self):
        self._build_projections()
        (self.projections / "weights.bin").write_bytes(b"not-a-real-model-projection")
        codes = [finding.code for finding in validate_projection_bundle(ROOT, self.projections)]
        self.assertIn("projection.file_set", codes)

    def test_projection_output_cannot_replace_repository_source(self):
        with self.assertRaises(Exception):
            build_projection_bundle(ROOT, ROOT / "ai", self.commit)


if __name__ == "__main__":
    unittest.main()
