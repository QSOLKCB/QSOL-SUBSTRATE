import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from release_core import (  # noqa: E402
    ReleaseError,
    _probe_snapshot,
    build_archive_metadata,
    build_reproducible_plan,
    parse_semver,
    release_fingerprint,
    snapshot_identity,
    validate_release_version,
    verify_source_revision,
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

    def test_snapshot_identity_does_not_depend_on_release_version(self):
        sha = "a" * 64
        identity = snapshot_identity("2026-08-15", sha)
        self.assertEqual(identity, f"snapshot-2026-08-15@sha256:{sha}")
        self.assertNotIn("1.2.0", identity)

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

    def test_archive_metadata_starts_without_doi_and_validates(self):
        value = build_archive_metadata("1.0.0", "a" * 40, "b" * 64)
        schema = json.loads((ROOT / "schema/archive-metadata.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
        self.assertEqual(errors, [])
        self.assertIsNone(value["doi"])
        self.assertEqual(value["status"], "unassigned")

    def test_published_archive_metadata_requires_doi(self):
        value = build_archive_metadata("1.0.0", "a" * 40, "b" * 64)
        value["status"] = "published"
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


if __name__ == "__main__":
    unittest.main()
