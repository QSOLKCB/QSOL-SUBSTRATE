import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from projection_core import ProjectionError, build_projection_bundle, validate_projection_bundle  # noqa: E402
from retrieve_vector_context import _safe_context_output, main as retrieve_main  # noqa: E402
from vector_core import VectorError, build_vector_bundle, validate_vector_bundle  # noqa: E402


class Phase6FilesystemSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.commit = "f" * 40

    def tearDown(self):
        self.tmp.cleanup()

    def test_vector_builder_refuses_symlinked_output_root(self):
        target = self.base / "vector-target"
        target.mkdir()
        link = self.base / "vector-link"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(VectorError):
            build_vector_bundle(ROOT, link, self.commit)

    def test_projection_builder_refuses_symlinked_output_root(self):
        target = self.base / "projection-target"
        target.mkdir()
        link = self.base / "projection-link"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ProjectionError):
            build_projection_bundle(ROOT, link, self.commit)

    def test_vector_validator_refuses_symlinked_bundle_root(self):
        target = self.base / "vectors"
        build_vector_bundle(ROOT, target, self.commit)
        link = self.base / "vectors-link"
        link.symlink_to(target, target_is_directory=True)
        codes = [finding.code for finding in validate_vector_bundle(ROOT, link)]
        self.assertIn("vector.bundle", codes)

    def test_projection_validator_refuses_symlinked_bundle_root(self):
        target = self.base / "projections"
        build_projection_bundle(ROOT, target, self.commit)
        link = self.base / "projections-link"
        link.symlink_to(target, target_is_directory=True)
        codes = [finding.code for finding in validate_projection_bundle(ROOT, link)]
        self.assertIn("projection.bundle", codes)

    def test_retrieval_output_refuses_repository_source_path(self):
        with self.assertRaises(VectorError):
            _safe_context_output(ROOT / "tools" / "invented-context.txt")

    def test_retrieval_output_allows_dedicated_dist_retrieved_path(self):
        output = _safe_context_output(ROOT / "dist" / "retrieved" / "context.txt")
        self.assertEqual(output, (ROOT / "dist" / "retrieved" / "context.txt").resolve())

    def test_retrieval_output_refuses_generated_vector_bundle_path(self):
        with self.assertRaises(VectorError):
            _safe_context_output(ROOT / "dist" / "vectors" / "records.jsonl")

    def test_retrieval_output_refuses_generated_projection_bundle_path(self):
        with self.assertRaises(VectorError):
            _safe_context_output(ROOT / "dist" / "projections" / "manifest.json")

    def test_retrieval_output_refuses_symlink(self):
        target = self.base / "context.txt"
        target.write_text("safe target", encoding="utf-8")
        link = self.base / "context-link.txt"
        link.symlink_to(target)
        with self.assertRaises(VectorError):
            _safe_context_output(link)

    def test_retrieval_cli_refuses_tampered_vector_bundle(self):
        bundle = self.base / "vectors"
        build_vector_bundle(ROOT, bundle, self.commit)
        records = bundle / "records.jsonl"
        records.write_text(records.read_text(encoding="utf-8").replace("Trent Slade", "Tampered Person", 1), encoding="utf-8")
        output = io.StringIO()
        argv = ["retrieve_vector_context.py", "Trent Slade", "--bundle", str(bundle)]
        with patch.object(sys, "argv", argv), redirect_stdout(output):
            result = retrieve_main()
        self.assertEqual(result, 1)
        self.assertIn("VECTOR RETRIEVAL REFUSED", output.getvalue())
        self.assertIn("vector bundle validation failed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
