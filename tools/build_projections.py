from __future__ import annotations

import argparse
from pathlib import Path

from projection_core import ProjectionError, build_projection_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build QSOL-SUBSTRATE Phase 6 projection experiment bundle")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist/projections"))
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    try:
        manifest = build_projection_bundle(args.root, args.output, args.source_commit)
    except ProjectionError as exc:
        print(f"PROJECTION BUILD REFUSED: {exc}")
        return 1
    print(f"projection_recipes={len(manifest['recipes'])}")
    print(f"source_commit={manifest['substrate']['source_commit']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    print(f"projection_bundle_sha256={manifest['bundle_sha256']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
