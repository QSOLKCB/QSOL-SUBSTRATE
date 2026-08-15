from __future__ import annotations

import argparse
from pathlib import Path

from release_core import ReleaseError, build_release_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic QSOL-SUBSTRATE Phase 8 release metadata")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", choices=("stable", "candidate", "ci"), required=True)
    parser.add_argument("--archive-status", choices=("unassigned", "reserved", "published"), default="unassigned")
    parser.add_argument("--doi", help="Assigned archival DOI, for reserved/published archive metadata")
    parser.add_argument("--output", type=Path, default=Path("dist/release"))
    args = parser.parse_args()
    try:
        manifest = build_release_bundle(
            ROOT,
            args.output,
            args.source_commit,
            args.version,
            args.channel,
            archive_status=args.archive_status,
            doi=args.doi,
        )
    except (OSError, ReleaseError) as exc:
        print(f"RELEASE BUILD REFUSED: {exc}")
        return 1
    print(f"release_version={manifest['release']['version']}")
    print(f"release_channel={manifest['release']['channel']}")
    print(f"release_publishable={str(manifest['release']['publishable']).lower()}")
    print(f"source_commit={manifest['substrate']['source_commit']}")
    print(f"snapshot_id={manifest['substrate']['snapshot_id']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    print(f"archive_status={manifest['archive']['status']}")
    print(f"archive_doi={manifest['archive']['doi'] or 'none'}")
    print(f"release_sha256={manifest['release_sha256']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
