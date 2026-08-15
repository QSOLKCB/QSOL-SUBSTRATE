import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from projection_core import ProjectionError, build_projection_bundle, validate_projection_bundle  # noqa: E402
from retrieve_vector_context import _safe_context_output  # noqa: E402
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

    def test_retrieval_output_allows_dist_path(self):
        output = _safe_context_output(ROOT / "dist" / "retrieved" / "context.txt")
        self.assertEqual(output, (ROOT / "dist" / "retrieved" / "context.txt").resolve())

    def test_retrieval_output_refuses_symlink(self):
        target = self.base / "context.txt"
        target.write_text("safe target", encoding="utf-8")
        link = self.base / "context-link.txt"
        link.symlink_to(target)
        with self.assertRaises(VectorError):
            _safe_context_output(link)


if __name__ == "__main__":
    unittest.main()
