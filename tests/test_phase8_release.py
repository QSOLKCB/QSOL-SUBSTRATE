import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from release_core import (  # noqa: E402
    ReleaseError,
    _probe_snapshot,
    _validate_component_bundles,
    _validate_publishability,
    build_archive_metadata,
    build_reproducible_plan,
    parse_semver,
    release_fingerprint,
    snapshot_identity,
    validate_release_bundle,
    validate_release_version,
    verify_source_revision,
    verify_stable_tag_binding,
)


class Phase8ReleaseTests(unittest.TestCase):
    def test_release_policy_is_schema_valid(self):
        policy = json.loads((ROOT / "release/policy.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "schema/release-policy.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(policy))
        self.assertEqual(errors, [])

    def test_semver_accepts_stable_and_prerelease(self):
        self.assertEqual(parse_semver("1.2.3")["major"], 1)
        self.assertEqual(parse_semver("1.2.3-rc.1+build.7")["prerelease"], "rc.1")

    def test_semver_rejects_leading_zeroes(self):
        with self.assertRaises(ReleaseError):
            parse_semver("01.2.3")
        with self.assertRaises(ReleaseError):
            parse_semver("1.2.3-rc.01")

    def test_stable_channel_rejects_prerelease(self):
        with self.assertRaises(ReleaseError):
            validate_release_version("1.0.0-rc.1", "stable")

    def test_candidate_channel_requires_prerelease(self):
        with self.assertRaises(ReleaseError):
            validate_release_version("1.0.0", "candidate")
        validate_release_version("1.0.0-rc.1", "candidate")

    def test_ci_channel_requires_ci_prefix(self):
        with self.assertRaises(ReleaseError):
            validate_release_version("0.8.0-rc.1", "ci")
        validate_release_version("0.8.0-ci.0", "ci")

    def test_snapshot_identity_includes_commit_and_not_release_version(self):
        commit = "a" * 40
        sha = "b" * 64
        identity = snapshot_identity("2026-08-15", commit, sha)
        self.assertEqual(identity, f"snapshot-2026-08-15@git:{commit}@sha256:{sha}")
        self.assertNotIn("1.2.0", identity)

    def test_snapshot_identity_changes_when_commit_changes(self):
        sha = "b" * 64
        left = snapshot_identity("2026-08-15", "a" * 40, sha)
        right = snapshot_identity("2026-08-15", "c" * 40, sha)
        self.assertNotEqual(left, right)

    def test_release_fingerprint_is_key_order_independent(self):
        left = {"type": "x", "a": 1, "b": {"x": 2, "y": 3}}
        right = {"b": {"y": 3, "x": 2}, "a": 1, "type": "x"}
        self.assertEqual(release_fingerprint(left), release_fingerprint(right))

    def test_release_fingerprint_excludes_its_own_field(self):
        base = {"type": "x", "a": 1}
        stamped = dict(base, release_sha256="f" * 64)
        self.assertEqual(release_fingerprint(base), release_fingerprint(stamped))

    def test_build_plan_is_network_free_and_complete(self):
        plan = build_reproducible_plan("0.8.0-ci.0", "ci")
        joined = "\n".join(plan["commands"])
        self.assertFalse(plan["network_required"])
        self.assertFalse(plan["prerequisites"]["dependency_installation_is_part_of_plan"])
        self.assertNotIn("pip install", joined)
        self.assertNotIn("http://", joined)
        self.assertNotIn("https://", joined)
        for required in (
            "validate_substrate.py",
            "build_adapters.py",
            "build_toolless.py",
            "build_vectors.py",
            "build_projections.py",
            "build_probes.py",
            "build_release.py",
            "validate_release.py",
        ):
            self.assertIn(required, joined)

    def test_build_plan_preserves_assigned_doi_input(self):
        plan = build_reproducible_plan("1.0.0", "stable", "published", "10.5281/zenodo.12345")
        self.assertEqual(plan["variables"]["ARCHIVE_STATUS"], "published")
        self.assertEqual(plan["variables"]["DOI"], "10.5281/zenodo.12345")
        self.assertIn("--doi $DOI", "\n".join(plan["commands"]))

    def test_archive_metadata_starts_without_doi_and_validates(self):
        value = build_archive_metadata("1.0.0", "a" * 40, "b" * 64)
        schema = json.loads((ROOT / "schema/archive-metadata.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
        self.assertEqual(errors, [])
        self.assertIsNone(value["doi"])
        self.assertEqual(value["status"], "unassigned")

    def test_assigned_doi_metadata_can_be_built_and_validated(self):
        value = build_archive_metadata(
            "1.0.0",
            "a" * 40,
            "b" * 64,
            status="published",
            doi="10.5281/zenodo.12345",
        )
        schema = json.loads((ROOT / "schema/archive-metadata.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
        self.assertEqual(errors, [])
        self.assertEqual(value["doi"], "10.5281/zenodo.12345")
        self.assertEqual(value["status"], "published")

    def test_published_archive_metadata_requires_doi(self):
        value = build_archive_metadata("1.0.0", "a" * 40, "b" * 64, status="published")
        schema = json.loads((ROOT / "schema/archive-metadata.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
        self.assertTrue(errors)

    def test_probe_snapshot_binds_exact_bundle_and_files(self):
        probe_manifest = {
            "probe_spec_version": "1.0.0",
            "probe_count": 48,
            "bundle_sha256": "c" * 64,
            "files": [{"path": "conditions.json", "sha256": "d" * 64, "bytes": 1}],
        }
        snapshot = _probe_snapshot(probe_manifest, "a" * 40, "b" * 64)
        self.assertTrue(snapshot["immutable"])
        self.assertEqual(snapshot["bundle_sha256"], "c" * 64)
        self.assertEqual(snapshot["files"], probe_manifest["files"])

    def test_checked_out_source_revision_is_accepted(self):
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()
        verify_source_revision(ROOT, commit)

    def test_mismatched_source_revision_fails_closed(self):
        with self.assertRaises(ReleaseError):
            verify_source_revision(ROOT, "0" * 40)

    def test_dirty_tracked_source_fails_closed(self):
        with mock.patch("release_core._git_output", side_effect=["a" * 40, " M ROADMAP.md"]):
            with self.assertRaises(ReleaseError):
                verify_source_revision(ROOT, "a" * 40)

    def test_untracked_reproducibility_source_fails_closed(self):
        with mock.patch("release_core._git_output", side_effect=["a" * 40, "", "tools/rogue.py"]):
            with self.assertRaisesRegex(ReleaseError, "untracked reproducibility source"):
                verify_source_revision(ROOT, "a" * 40)

    def test_untracked_dist_output_is_allowed(self):
        with mock.patch("release_core._git_output", side_effect=["a" * 40, "", "dist/release/manifest.json"]):
            verify_source_revision(ROOT, "a" * 40)

    def test_stable_tag_collision_fails_closed(self):
        with mock.patch("release_core._resolve_tag_commit", return_value="b" * 40):
            with self.assertRaisesRegex(ReleaseError, "already points"):
                verify_stable_tag_binding(ROOT, "1.0.0", "stable", "a" * 40)

    def test_missing_stable_tag_is_allowed_for_build_before_tag(self):
        with mock.patch("release_core._resolve_tag_commit", return_value=None):
            verify_stable_tag_binding(ROOT, "1.0.0", "stable", "a" * 40)

    def test_existing_stable_tag_may_point_to_same_commit(self):
        with mock.patch("release_core._resolve_tag_commit", return_value="a" * 40):
            verify_stable_tag_binding(ROOT, "1.0.0", "stable", "a" * 40)

    def test_publishability_is_derived_from_channel(self):
        _validate_publishability("stable", True)
        _validate_publishability("candidate", False)
        _validate_publishability("ci", False)
        with self.assertRaises(ReleaseError):
            _validate_publishability("ci", True)
        with self.assertRaises(ReleaseError):
            _validate_publishability("stable", False)

    def test_component_validation_finding_blocks_release_sealing(self):
        finding = mock.Mock(code="bundle.tampered", path="dist/adapters/file", message="tampered")
        with mock.patch("release_core.validate_adapter_bundle", return_value=[finding]):
            with self.assertRaisesRegex(ReleaseError, "component validation failed"):
                _validate_component_bundles(ROOT)

    def test_release_validator_rejects_symlinked_bundle_path_before_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "target"
            target.mkdir()
            link = tmp_path / "bundle"
            link.symlink_to(target, target_is_directory=True)
            findings = validate_release_bundle(ROOT, link, deterministic_rebuild=False)
            self.assertTrue(findings)
            self.assertIn("symlink", findings[0])


if __name__ == "__main__":
    unittest.main()
