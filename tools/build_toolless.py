#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from toolless_core import CapsuleError, build_toolless_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic QSOL-SUBSTRATE tool-less capsules.")
    parser.add_argument("--source-commit", required=True, help="Exact 40-character Git commit represented by this build.")
    parser.add_argument("--output", default="dist/toolless", help="Output directory (default: dist/toolless).")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    try:
        manifest = build_toolless_bundle(root, Path(args.output), args.source_commit)
    except CapsuleError as exc:
        print(f"CAPSULE BUILD REFUSED: {exc}")
        return 2

    print(f"built_profiles={len(manifest['profiles'])}")
    print(f"substrate_version={manifest['substrate']['version']}")
    print(f"source_commit={manifest['substrate']['source_commit']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    for profile in manifest["profiles"]:
        print(
            f"profile={profile['name']} portable_tokens={profile['portable_tokens']} "
            f"budget={profile['token_budget']} included={profile['included_items']} "
            f"omitted={profile['omitted_items']} sha256={profile['sha256']}"
        )
    print(f"toolless_bundle_sha256={manifest['bundle_sha256']}")
    print(f"output={Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
