from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import release_core_base as base
from adapter_core import validate_adapter_bundle
from probe_core import validate_probe_bundle
from projection_core import validate_projection_bundle
from toolless_core import validate_toolless_bundle
from vector_core import validate_vector_bundle

ReleaseError = base.ReleaseError
RELEASE_SPEC_VERSION = base.RELEASE_SPEC_VERSION
SCHEMA_VERSION = base.SCHEMA_VERSION
RELEASE_SCHEMA = base.RELEASE_SCHEMA
POLICY_SCHEMA = base.POLICY_SCHEMA
ARCHIVE_SCHEMA = base.ARCHIVE_SCHEMA
EXPECTED_RELEASE_FILES = base.EXPECTED_RELEASE_FILES
HEX40_RE = base.HEX40_RE
HEX64_RE = base.HEX64_RE
parse_semver = base.parse_semver
validate_release_version = base.validate_release_version
release_fingerprint = base.release_fingerprint
_read_json = base._read_json
_schema_validate = base._schema_validate
_sha256 = base._sha256
_git_output = base._git_output
_safe_output = base._safe_output
_component = base._component
_probe_snapshot = base._probe_snapshot
_file_row = base._file_row
_write_bundle = base._write_bundle
_expected_checksums = base._expected_checksums
canonical_json_bytes = base.canonical_json_bytes
build_fingerprint = base.build_fingerprint

REPRODUCIBILITY_SOURCE_DIRS = {
    ".github",
    "adapters",
    "ai",
    "chronology",
    "context",
    "identity",
    "projects",
    "public_export",
    "publications",
    "relationships",
    "release",
    "schema",
    "sources",
    "terminology",
    "tests",
    "tools",
}
REPRODUCIBILITY_SOURCE_FILES = {"requirements-validation.txt"}


def snapshot_identity(snapshot_date: str, source_commit: str, substrate_sha256: str) -> str:
    if not HEX40_RE.fullmatch(source_commit):
        raise ReleaseError("snapshot source_commit must be a 40-character lowercase Git SHA")
    if not HEX64_RE.fullmatch(substrate_sha256):
        raise ReleaseError("canonical substrate fingerprint must be lowercase SHA-256")
    return f"snapshot-{snapshot_date}@git:{source_commit}@sha256:{substrate_sha256}"


def _is_reproducibility_source(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    if normalized in REPRODUCIBILITY_SOURCE_FILES:
        return True
    head = normalized.split("/", 1)[0]
    return head in REPRODUCIBILITY_SOURCE_DIRS


def verify_source_revision(root: Path, source_commit: str) -> None:
    if not HEX40_RE.fullmatch(source_commit):
        raise ReleaseError("source_commit must be a 40-character lowercase Git SHA")
    head = _git_output(root, "rev-parse", "HEAD^{commit}")
    if head != source_commit:
        raise ReleaseError(f"declared source_commit {source_commit} does not equal checked-out HEAD {head}")
    dirty = _git_output(root, "status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise ReleaseError("tracked source tree contains uncommitted changes")
    untracked = _git_output(root, "ls-files", "--others", "--exclude-standard")
    offending = sorted(path for path in untracked.splitlines() if path and _is_reproducibility_source(path))
    if offending:
        raise ReleaseError(f"untracked reproducibility source is not bound to source_commit: {offending[0]}")


def _resolve_tag_commit(root: Path, tag: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ReleaseError(f"cannot resolve stable tag {tag}") from exc
    if proc.returncode == 1:
        return None
    if proc.returncode != 0:
        raise ReleaseError(f"cannot resolve stable tag {tag}")
    target = proc.stdout.strip()
    if not HEX40_RE.fullmatch(target):
        raise ReleaseError(f"stable tag {tag} did not resolve to a commit")
    return target


def verify_stable_tag_binding(root: Path, version: str, channel: str, source_commit: str) -> None:
    if channel != "stable":
        return
    tag = f"v{version}"
    target = _resolve_tag_commit(root, tag)
    if target is not None and target != source_commit:
        raise ReleaseError(f"stable tag {tag} already points to {target}, not release source_commit {source_commit}")


def _validate_publishability(channel: str, publishable: bool) -> None:
    expected = channel == "stable"
    if publishable is not expected:
        raise ReleaseError(f"release publishability mismatch: channel={channel} requires publishable={str(expected).lower()}")


def build_reproducible_plan(
    version: str,
    channel: str,
    archive_status: str = "unassigned",
    doi: str | None = None,
) -> dict[str, Any]:
    validate_release_version(version, channel)
    release_command = (
        "python tools/build_release.py --source-commit $SOURCE_COMMIT --version $VERSION "
        "--channel $CHANNEL --archive-status $ARCHIVE_STATUS"
    )
    variables: dict[str, Any] = {
        "SOURCE_COMMIT": "exact checked-out Git commit",
        "VERSION": version,
        "CHANNEL": channel,
        "ARCHIVE_STATUS": archive_status,
        "DOI": doi,
    }
    if doi is not None:
        release_command += " --doi $DOI"
    release_command += " --output dist/release"
    return {
        "type": "qsol-substrate-release-build-plan",
        "schema_version": SCHEMA_VERSION,
        "release_spec_version": RELEASE_SPEC_VERSION,
        "version": version,
        "channel": channel,
        "variables": variables,
        "network_required": False,
        "prerequisites": {
            "python": "3.12+",
            "validation_dependencies": "requirements-validation.txt dependencies must already be installed, or supplied from an offline wheelhouse before this plan begins",
            "dependency_installation_is_part_of_plan": False,
        },
        "commands": [
            "python -m unittest discover -s tests -v",
            "python tools/validate_substrate.py --json-report validation-report.json",
            "python tools/fingerprint_substrate.py --output substrate-fingerprint.json",
            "python tools/build_adapters.py --source-commit $SOURCE_COMMIT --output dist/adapters",
            "python tools/validate_adapter_bundle.py --bundle dist/adapters",
            "python tools/build_toolless.py --source-commit $SOURCE_COMMIT --output dist/toolless",
            "python tools/validate_toolless_capsule.py --bundle dist/toolless",
            "python tools/build_vectors.py --source-commit $SOURCE_COMMIT --output dist/vectors",
            "python tools/validate_vector_bundle.py --bundle dist/vectors",
            "python tools/build_projections.py --source-commit $SOURCE_COMMIT --output dist/projections",
            "python tools/validate_projection_bundle.py --bundle dist/projections",
            "python tools/build_probes.py --source-commit $SOURCE_COMMIT --output dist/probes",
            "python tools/validate_probe_bundle.py --bundle dist/probes",
            release_command,
            "python tools/validate_release.py --bundle dist/release",
        ],
    }


def build_archive_metadata(
    version: str,
    source_commit: str,
    substrate_sha256: str,
    status: str = "unassigned",
    doi: str | None = None,
) -> dict[str, Any]:
    value = {
        "type": "qsol-substrate-archive-metadata",
        "schema_version": SCHEMA_VERSION,
        "provider": "Zenodo",
        "status": status,
        "doi": doi,
        "resource_type": "Software",
        "title": "QSOL-SUBSTRATE",
        "version": version,
        "license": "Apache-2.0",
        "source_commit": source_commit,
        "substrate_sha256": substrate_sha256,
        "notes": [
            "Archival DOI assignment is optional post-publication metadata bound by rebuilding this release metadata against the same exact canonical snapshot.",
            "A DOI records an archive location; it does not redefine canonical substrate facts or the canonical substrate fingerprint.",
        ],
    }
    return value


def _validate_archive_binding(
    root: Path,
    archive: dict[str, Any],
    version: str,
    source_commit: str,
    substrate_sha256: str,
) -> None:
    _schema_validate(root, ARCHIVE_SCHEMA, archive, "archive metadata")
    if archive.get("version") != version:
        raise ReleaseError("archive metadata version does not match release")
    if archive.get("source_commit") != source_commit:
        raise ReleaseError("archive metadata source_commit does not match release")
    if archive.get("substrate_sha256") != substrate_sha256:
        raise ReleaseError("archive metadata canonical fingerprint does not match release")
    if archive.get("status") == "unassigned" and archive.get("doi") is not None:
        raise ReleaseError("unassigned archive metadata may not carry a DOI")


def _finding_text(finding: Any) -> str:
    code = getattr(finding, "code", "invalid")
    path = getattr(finding, "path", "<bundle>")
    message = getattr(finding, "message", str(finding))
    return f"[{code}] {path}: {message}"


def _run_component_validator(
    label: str,
    validator: Callable[[Path, Path], list[Any]],
    root: Path,
    bundle: Path,
) -> None:
    findings = validator(root, bundle)
    if findings:
        raise ReleaseError(f"{label} component validation failed: {_finding_text(findings[0])}")


def _validate_component_bundles(root: Path) -> None:
    checks: tuple[tuple[str, Callable[[Path, Path], list[Any]], str], ...] = (
        ("adapters", validate_adapter_bundle, "dist/adapters"),
        ("toolless", validate_toolless_bundle, "dist/toolless"),
        ("vectors", validate_vector_bundle, "dist/vectors"),
        ("projections", validate_projection_bundle, "dist/projections"),
        ("probes", validate_probe_bundle, "dist/probes"),
    )
    for label, validator, rel_path in checks:
        _run_component_validator(label, validator, root, root / rel_path)


def build_release_bundle(
    root: Path,
    output: Path,
    source_commit: str,
    version: str,
    channel: str,
    archive_status: str = "unassigned",
    doi: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    output = _safe_output(root, output)
    validate_release_version(version, channel)
    verify_source_revision(root, source_commit)
    verify_stable_tag_binding(root, version, channel, source_commit)

    policy = _read_json(root / "release/policy.json")
    _schema_validate(root, POLICY_SCHEMA, policy, "release policy")
    canonical = build_fingerprint(root)
    substrate_sha = canonical["substrate_sha256"]
    snapshot_date = canonical["snapshot_date"]

    # Never seal a component merely because its manifest still looks plausible.
    _validate_component_bundles(root)

    adapters, adapter_entry = _component(root, "dist/adapters/manifest.json", "adapter_bundle_sha256", source_commit, substrate_sha)
    toolless, toolless_entry = _component(root, "dist/toolless/manifest.json", "bundle_sha256", source_commit, substrate_sha)
    vectors, vector_entry = _component(root, "dist/vectors/manifest.json", "bundle_sha256", source_commit, substrate_sha)
    projections, projection_entry = _component(root, "dist/projections/manifest.json", "bundle_sha256", source_commit, substrate_sha)
    probes, probe_entry = _component(root, "dist/probes/manifest.json", "bundle_sha256", source_commit, substrate_sha)

    toolless_entry["profiles"] = [
        {"name": item["name"], "sha256": item["sha256"]}
        for item in toolless.get("profiles", [])
    ]
    vector_entry["index_sha256"] = _sha256((root / "dist/vectors/index.json").read_bytes())
    vector_entry["embeddings_sha256"] = _sha256((root / "dist/vectors/embeddings.f16").read_bytes())
    projection_entry.update(
        {
            "compatibility_schema": "schema/model-projection-compatibility.schema.json",
            "model_specific_binary_artifacts_included": False,
            "compatibility_metadata_required": True,
        }
    )

    probe_snapshot = _probe_snapshot(probes, source_commit, substrate_sha)
    probe_snapshot_bytes = canonical_json_bytes(probe_snapshot)
    probe_entry.update(
        {
            "snapshot_file": "probe-snapshot.json",
            "snapshot_sha256": _sha256(probe_snapshot_bytes),
            "probe_count": probes.get("probe_count"),
        }
    )

    archive = build_archive_metadata(version, source_commit, substrate_sha, archive_status, doi)
    _validate_archive_binding(root, archive, version, source_commit, substrate_sha)
    build_plan = build_reproducible_plan(version, channel, archive_status, doi)
    build_plan_bytes = canonical_json_bytes(build_plan)
    archive_bytes = canonical_json_bytes(archive)

    generated = {
        "archive-metadata.json": archive_bytes,
        "build-plan.json": build_plan_bytes,
        "probe-snapshot.json": probe_snapshot_bytes,
    }
    file_rows = [_file_row(name, data) for name, data in sorted(generated.items())]
    publishable = channel == "stable"

    manifest: dict[str, Any] = {
        "type": "qsol-substrate-release-manifest",
        "schema_version": SCHEMA_VERSION,
        "release_spec_version": RELEASE_SPEC_VERSION,
        "release": {
            "name": "QSOL-SUBSTRATE",
            "version": version,
            "channel": channel,
            "tag": f"v{version}",
            "publishable": publishable,
        },
        "substrate": {
            "protocol": "QSOL-SUBSTRATE",
            "schema_version": SCHEMA_VERSION,
            "snapshot_date": snapshot_date,
            "snapshot_id": snapshot_identity(snapshot_date, source_commit, substrate_sha),
            "source_commit": source_commit,
            "substrate_sha256": substrate_sha,
        },
        "components": {
            "adapters": adapter_entry,
            "toolless": toolless_entry,
            "vectors": vector_entry,
            "projections": projection_entry,
            "probes": probe_entry,
        },
        "reproducibility": {
            "build_plan": "build-plan.json",
            "build_plan_sha256": _sha256(build_plan_bytes),
            "source_commit_verified": True,
            "tracked_source_clean": True,
            "untracked_reproducibility_sources_absent": True,
            "network_required": False,
        },
        "archive": {
            "metadata_file": "archive-metadata.json",
            "metadata_sha256": _sha256(archive_bytes),
            "doi_required": False,
            "doi": archive["doi"],
            "provider": archive["provider"],
            "status": archive["status"],
        },
        "files": file_rows,
    }
    _validate_publishability(channel, publishable)
    manifest["release_sha256"] = release_fingerprint(manifest)
    _schema_validate(root, RELEASE_SCHEMA, manifest, "release manifest")
    _write_bundle(output, generated, manifest)
    return manifest


def validate_release_bundle(root: Path, bundle: Path, deterministic_rebuild: bool = True) -> list[str]:
    root = root.resolve()
    candidate = bundle if bundle.is_absolute() else root / bundle
    findings: list[str] = []
    try:
        # Check the user-supplied path before resolve(), otherwise a symlink is erased by resolution.
        if candidate.is_symlink():
            raise ReleaseError("release bundle must be a real directory, not a symlink")
        bundle = candidate.resolve()
        if not bundle.is_dir():
            raise ReleaseError("release bundle must be a real directory")
        actual = {path.name for path in bundle.iterdir()}
        if actual != EXPECTED_RELEASE_FILES:
            raise ReleaseError(f"release file set mismatch: expected {sorted(EXPECTED_RELEASE_FILES)}, got {sorted(actual)}")
        if any(path.is_symlink() for path in bundle.iterdir()):
            raise ReleaseError("release bundle may not contain symlinks")

        manifest = _read_json(bundle / "manifest.json")
        _schema_validate(root, RELEASE_SCHEMA, manifest, "release manifest")
        version = manifest["release"]["version"]
        channel = manifest["release"]["channel"]
        validate_release_version(version, channel)
        if manifest["release"]["tag"] != f"v{version}":
            raise ReleaseError("release tag does not match version")
        _validate_publishability(channel, manifest["release"]["publishable"])
        verify_source_revision(root, manifest["substrate"]["source_commit"])
        verify_stable_tag_binding(root, version, channel, manifest["substrate"]["source_commit"])

        canonical = build_fingerprint(root)
        if manifest["substrate"]["substrate_sha256"] != canonical["substrate_sha256"]:
            raise ReleaseError("release canonical fingerprint does not match current substrate")
        expected_snapshot = snapshot_identity(
            canonical["snapshot_date"],
            manifest["substrate"]["source_commit"],
            canonical["substrate_sha256"],
        )
        if manifest["substrate"]["snapshot_id"] != expected_snapshot:
            raise ReleaseError("release snapshot identity does not match canonical substrate and source commit")
        if manifest["release_sha256"] != release_fingerprint(manifest):
            raise ReleaseError("release fingerprint mismatch")

        for row in manifest["files"]:
            data = (bundle / row["path"]).read_bytes()
            if row["sha256"] != _sha256(data) or row["bytes"] != len(data):
                raise ReleaseError(f"release helper file mismatch: {row['path']}")
        if (bundle / "SHA256SUMS.txt").read_text(encoding="utf-8") != _expected_checksums(bundle):
            raise ReleaseError("SHA256SUMS.txt does not match release files")

        archive = _read_json(bundle / "archive-metadata.json")
        _validate_archive_binding(
            root,
            archive,
            version,
            manifest["substrate"]["source_commit"],
            manifest["substrate"]["substrate_sha256"],
        )
        archive_bytes = (bundle / "archive-metadata.json").read_bytes()
        archive_manifest = manifest["archive"]
        if archive_manifest["metadata_sha256"] != _sha256(archive_bytes):
            raise ReleaseError("archive metadata hash mismatch")
        for key in ("provider", "status", "doi"):
            if archive_manifest[key] != archive[key]:
                raise ReleaseError(f"archive manifest {key} does not match archive metadata")

        plan = _read_json(bundle / "build-plan.json")
        expected_plan = build_reproducible_plan(version, channel, archive["status"], archive["doi"])
        if plan != expected_plan:
            raise ReleaseError("reproducible build plan mismatch")

        # Component validation is a core trust check and remains active even with --no-rebuild.
        _validate_component_bundles(root)

        probes = _read_json(root / "dist/probes/manifest.json")
        expected_probe_snapshot = _probe_snapshot(
            probes,
            manifest["substrate"]["source_commit"],
            manifest["substrate"]["substrate_sha256"],
        )
        if _read_json(bundle / "probe-snapshot.json") != expected_probe_snapshot:
            raise ReleaseError("immutable probe snapshot does not match built probe bundle")

        component_keys = {
            "adapters": ("dist/adapters/manifest.json", "adapter_bundle_sha256"),
            "toolless": ("dist/toolless/manifest.json", "bundle_sha256"),
            "vectors": ("dist/vectors/manifest.json", "bundle_sha256"),
            "projections": ("dist/projections/manifest.json", "bundle_sha256"),
            "probes": ("dist/probes/manifest.json", "bundle_sha256"),
        }
        for name, (rel_path, bundle_key) in component_keys.items():
            current = _read_json(root / rel_path)
            recorded = manifest["components"][name]
            if recorded["manifest_sha256"] != _sha256((root / rel_path).read_bytes()):
                raise ReleaseError(f"{name} manifest hash mismatch")
            if recorded["bundle_sha256"] != current.get(bundle_key):
                raise ReleaseError(f"{name} bundle fingerprint mismatch")

        if deterministic_rebuild:
            with tempfile.TemporaryDirectory() as tmp:
                rebuilt_dir = Path(tmp) / "release"
                build_release_bundle(
                    root,
                    rebuilt_dir,
                    manifest["substrate"]["source_commit"],
                    version,
                    channel,
                    archive["status"],
                    archive["doi"],
                )
                for name in EXPECTED_RELEASE_FILES:
                    if (rebuilt_dir / name).read_bytes() != (bundle / name).read_bytes():
                        raise ReleaseError(f"deterministic release rebuild mismatch: {name}")
    except (OSError, KeyError, TypeError, ReleaseError) as exc:
        findings.append(str(exc))
    return findings
