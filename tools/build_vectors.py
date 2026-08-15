from __future__ import annotations

import argparse
from pathlib import Path

from vector_core import VectorError, build_vector_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic QSOL-SUBSTRATE vector projection")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist/vectors"))
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    try:
        manifest = build_vector_bundle(args.root, args.output, args.source_commit)
    except VectorError as exc:
        print(f"VECTOR BUILD REFUSED: {exc}")
        return 1
    print(f"vector_records={manifest['record_count']}")
    print(f"embedding_backend={manifest['embedding']['id']}")
    print(f"dimension={manifest['embedding']['dimension']}")
    print(f"source_commit={manifest['substrate']['source_commit']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    print(f"vector_bundle_sha256={manifest['bundle_sha256']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
