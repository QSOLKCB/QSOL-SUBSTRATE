from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from substrate_integrity import build_fingerprint, canonical_json_bytes

RELEASE_SPEC_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
RELEASE_SCHEMA = "schema/release-manifest.schema.json"
POLICY_SCHEMA = "schema/release-policy.schema.json"
ARCHIVE_SCHEMA = "schema/archive-metadata.schema.json"
EXPECTED_RELEASE_FILES = {
    "archive-metadata.json",
    "build-plan.json",
    "manifest.json",
    "probe-snapshot.json",
    "SHA256SUMS.txt",
}
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class ReleaseError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"{path} must contain a JSON object")
    return value


def _schema_validate(root: Path, schema_path: str, value: dict[str, Any], label: str) -> None:
    schema = _read_json(root / schema_path)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
        key=lambda err: list(err.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ReleaseError(f"{label} schema validation failed at {location}: {first.message}")


def parse_semver(version: str) -> dict[str, Any]:
    match = SEMVER_RE.fullmatch(version)
    if not match:
        raise ReleaseError(f"invalid SemVer 2.0.0 version: {version}")
    prerelease = match.group(4)
    if prerelease:
        for item in prerelease.split("."):
            if item.isdigit() and len(item) > 1 and item.startswith("0"):
                raise ReleaseError(f"numeric prerelease identifiers may not contain leading zeroes: {version}")
    return {
        "major": int(match.group(1)),
        "minor": int(match.group(2)),
        "patch": int(match.group(3)),
        "prerelease": prerelease,
        "build": match.group(5),
    }


def validate_release_version(version: str, channel: str) -> dict[str, Any]:
    parsed = parse_semver(version)
    if channel not in {"stable", "candidate", "ci"}:
        raise ReleaseError(f"unsupported release channel: {channel}")
    prerelease = parsed["prerelease"]
    if channel == "stable" and prerelease is not None:
        raise ReleaseError("stable releases may not use a prerelease identifier")
    if channel in {"candidate", "ci"} and prerelease is None:
        raise ReleaseError(f"{channel} releases require a prerelease identifier")
    if channel == "ci" and not str(prerelease).startswith("ci."):
        raise ReleaseError("ci release versions must use a ci.* prerelease identifier")
    return parsed


def snapshot_identity(snapshot_date: str, substrate_sha256: str) -> str:
    if not HEX64_RE.fullmatch(substrate_sha256):
        raise ReleaseError("canonical substrate fingerprint must be lowercase SHA-256")
    return f"snapshot-{snapshot_date}@sha256:{substrate_sha256}"


def release_fingerprint(value: dict[str, Any]) -> str:
    material = dict(value)
    material.pop("release_sha256", None)
    return _sha256(canonical_json_bytes(material))


def build_reproducible_plan(version: str, channel: str) -> dict[str, Any]:
    validate_release_version(version, channel)
    return {
        "type": "qsol-substrate-release-build-plan",
        "schema_version": SCHEMA_VERSION,
        "release_spec_version": RELEASE_SPEC_VERSION,
        "version": version,
        "channel": channel,
        "variables": {
            "SOURCE_COMMIT": "exact checked-out Git commit",
            "VERSION": version,
            "CHANNEL": channel,
        },
        "network_required": False,
        "commands": [
            "python -m pip install --disable-pip-version-check -r requirements-validation.txt",
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
            "python tools/build_release.py --source-commit $SOURCE_COMMIT --version $VERSION --channel $CHANNEL --output dist/release",
            "python tools/validate_release.py --bundle dist/release",
        ],
    }


def build_archive_metadata(version: str, source_commit: str, substrate_sha256: str) -> dict[str, Any]:
    return {
        "type": "qsol-substrate-archive-metadata",
        "schema_version": SCHEMA_VERSION,
        "provider": "Zenodo",
        "status": "unassigned",
        "doi": None,
        "resource_type": "Software",
        "title": "QSOL-SUBSTRATE",
        "version": version,
        "license": "Apache-2.0",
        "source_commit": source_commit,
        "substrate_sha256": substrate_sha256,
        "notes": [
            "Archival DOI assignment is optional and occurs after immutable release identity has been computed.",
            "A DOI records an archive location; it does not redefine canonical substrate facts or fingerprints.",
        ],
    }


def _git_output(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleaseError(f"git identity check failed: {' '.join(args)}") from exc
    return proc.stdout.strip()


def verify_source_revision(root: Path, source_commit: str) -> None:
    if not HEX40_RE.fullmatch(source_commit):
        raise ReleaseError("source_commit must be a 40-character lowercase Git SHA")
    head = _git_output(root, "rev-parse", "HEAD^{commit}")
    if head != source_commit:
        raise ReleaseError(f"declared source_commit {source_commit} does not equal checked-out HEAD {head}")
    dirty = _git_output(root, "status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise ReleaseError("tracked source tree contains uncommitted changes")


def _safe_output(root: Path, output: Path) -> Path:
    root = root.resolve()
    if output.exists() and output.is_symlink():
        raise ReleaseError("refusing symlinked release output")
    resolved = output.resolve()
    if resolved == root or resolved in root.parents:
        raise ReleaseError("release output may not replace or contain repository root")
    if root in resolved.parents and resolved != root / "dist" / "release":
        raise ReleaseError("in-repository release output is restricted to dist/release")
    if resolved.exists() and not resolved.is_dir():
        raise ReleaseError("release output must be a directory")
    return resolved


def _component(root: Path, rel_manifest: str, bundle_key: str, source_commit: str, substrate_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = root / rel_manifest
    data = _read_json(path)
    substrate = data.get("substrate")
    if not isinstance(substrate, dict):
        raise ReleaseError(f"{rel_manifest} lacks substrate identity")
    if substrate.get("source_commit") != source_commit:
        raise ReleaseError(f"{rel_manifest} source_commit does not match release")
    if substrate.get("substrate_sha256") != substrate_sha256:
        raise ReleaseError(f"{rel_manifest} canonical fingerprint does not match release")
    bundle_sha = data.get(bundle_key)
    if not isinstance(bundle_sha, str) or not HEX64_RE.fullmatch(bundle_sha):
        raise ReleaseError(f"{rel_manifest} lacks valid {bundle_key}")
    entry = {
        "manifest": rel_manifest,
        "manifest_sha256": _sha256(path.read_bytes()),
        "bundle_sha256": bundle_sha,
    }
    return data, entry


def _probe_snapshot(probe_manifest: dict[str, Any], source_commit: str, substrate_sha256: str) -> dict[str, Any]:
    return {
        "type": "qsol-substrate-probe-snapshot",
        "schema_version": SCHEMA_VERSION,
        "probe_spec_version": probe_manifest.get("probe_spec_version"),
        "immutable": True,
        "source_commit": source_commit,
        "substrate_sha256": substrate_sha256,
        "probe_count": probe_manifest.get("probe_count"),
        "bundle_sha256": probe_manifest.get("bundle_sha256"),
        "files": probe_manifest.get("files"),
    }


def _file_row(path: str, data: bytes) -> dict[str, Any]:
    return {"path": path, "sha256": _sha256(data), "bytes": len(data)}


def _write_bundle(output: Path, generated: dict[str, bytes], manifest: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".qsol-release-", dir=output.parent))
    try:
        for name, data in generated.items():
            (temp / name).write_bytes(data)
        manifest_bytes = canonical_json_bytes(manifest)
        (temp / "manifest.json").write_bytes(manifest_bytes)
        checksum_rows = []
        for name in sorted(set(generated) | {"manifest.json"}):
            checksum_rows.append(f"{_sha256((temp / name).read_bytes())}  {name}\n")
        (temp / "SHA256SUMS.txt").write_text("".join(checksum_rows), encoding="utf-8")
        if output.exists():
            shutil.rmtree(output)
        temp.replace(output)
    except Exception:
        if temp.exists():
            shutil.rmtree(temp)
        raise


def build_release_bundle(root: Path, output: Path, source_commit: str, version: str, channel: str) -> dict[str, Any]:
    root = root.resolve()
    output = _safe_output(root, output)
    validate_release_version(version, channel)
    verify_source_revision(root, source_commit)

    policy = _read_json(root / "release/policy.json")
    _schema_validate(root, POLICY_SCHEMA, policy, "release policy")
    canonical = build_fingerprint(root)
    substrate_sha = canonical["substrate_sha256"]
    snapshot_date = canonical["snapshot_date"]

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

    build_plan = build_reproducible_plan(version, channel)
    build_plan_bytes = canonical_json_bytes(build_plan)
    archive = build_archive_metadata(version, source_commit, substrate_sha)
    _schema_validate(root, ARCHIVE_SCHEMA, archive, "archive metadata")
    archive_bytes = canonical_json_bytes(archive)

    generated = {
        "archive-metadata.json": archive_bytes,
        "build-plan.json": build_plan_bytes,
        "probe-snapshot.json": probe_snapshot_bytes,
    }
    file_rows = [_file_row(name, data) for name, data in sorted(generated.items())]

    manifest: dict[str, Any] = {
        "type": "qsol-substrate-release-manifest",
        "schema_version": SCHEMA_VERSION,
        "release_spec_version": RELEASE_SPEC_VERSION,
        "release": {
            "name": "QSOL-SUBSTRATE",
            "version": version,
            "channel": channel,
            "tag": f"v{version}",
            "publishable": channel == "stable",
        },
        "substrate": {
            "protocol": "QSOL-SUBSTRATE",
            "schema_version": SCHEMA_VERSION,
            "snapshot_date": snapshot_date,
            "snapshot_id": snapshot_identity(snapshot_date, substrate_sha),
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
            "network_required": False,
        },
        "archive": {
            "metadata_file": "archive-metadata.json",
            "metadata_sha256": _sha256(archive_bytes),
            "doi_required": False,
            "doi": None,
            "provider": "Zenodo",
            "status": "unassigned",
        },
        "files": file_rows,
    }
    manifest["release_sha256"] = release_fingerprint(manifest)
    _schema_validate(root, RELEASE_SCHEMA, manifest, "release manifest")
    _write_bundle(output, generated, manifest)
    return manifest


def _expected_checksums(bundle: Path) -> str:
    rows = []
    for name in sorted(EXPECTED_RELEASE_FILES - {"SHA256SUMS.txt"}):
        rows.append(f"{_sha256((bundle / name).read_bytes())}  {name}\n")
    return "".join(rows)


def validate_release_bundle(root: Path, bundle: Path, deterministic_rebuild: bool = True) -> list[str]:
    root = root.resolve()
    bundle = bundle.resolve()
    findings: list[str] = []
    try:
        if not bundle.is_dir() or bundle.is_symlink():
            raise ReleaseError("release bundle must be a real directory")
        actual = {path.name for path in bundle.iterdir()}
        if actual != EXPECTED_RELEASE_FILES:
            raise ReleaseError(f"release file set mismatch: expected {sorted(EXPECTED_RELEASE_FILES)}, got {sorted(actual)}")
        if any(path.is_symlink() for path in bundle.iterdir()):
            raise ReleaseError("release bundle may not contain symlinks")

        manifest = _read_json(bundle / "manifest.json")
        _schema_validate(root, RELEASE_SCHEMA, manifest, "release manifest")
        validate_release_version(manifest["release"]["version"], manifest["release"]["channel"])
        verify_source_revision(root, manifest["substrate"]["source_commit"])

        canonical = build_fingerprint(root)
        if manifest["substrate"]["substrate_sha256"] != canonical["substrate_sha256"]:
            raise ReleaseError("release canonical fingerprint does not match current substrate")
        if manifest["substrate"]["snapshot_id"] != snapshot_identity(canonical["snapshot_date"], canonical["substrate_sha256"]):
            raise ReleaseError("release snapshot identity does not match canonical substrate")
        if manifest["release_sha256"] != release_fingerprint(manifest):
            raise ReleaseError("release fingerprint mismatch")

        for row in manifest["files"]:
            data = (bundle / row["path"]).read_bytes()
            if row["sha256"] != _sha256(data) or row["bytes"] != len(data):
                raise ReleaseError(f"release helper file mismatch: {row['path']}")
        if (bundle / "SHA256SUMS.txt").read_text(encoding="utf-8") != _expected_checksums(bundle):
            raise ReleaseError("SHA256SUMS.txt does not match release files")

        archive = _read_json(bundle / "archive-metadata.json")
        _schema_validate(root, ARCHIVE_SCHEMA, archive, "archive metadata")
        plan = _read_json(bundle / "build-plan.json")
        expected_plan = build_reproducible_plan(manifest["release"]["version"], manifest["release"]["channel"])
        if plan != expected_plan:
            raise ReleaseError("reproducible build plan mismatch")

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
                    manifest["release"]["version"],
                    manifest["release"]["channel"],
                )
                for name in EXPECTED_RELEASE_FILES:
                    if (rebuilt_dir / name).read_bytes() != (bundle / name).read_bytes():
                        raise ReleaseError(f"deterministic release rebuild mismatch: {name}")
    except (OSError, KeyError, TypeError, ReleaseError) as exc:
        findings.append(str(exc))
    return findings
