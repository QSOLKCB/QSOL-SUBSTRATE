from __future__ import annotations

import argparse
from pathlib import Path

from epistemic_conformance_core import EpistemicConformanceError, build_benchmark_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic EPISTEMIC-CONFORMANCE/1 bundle")
    parser.add_argument("--source-commit")
    parser.add_argument("--output", type=Path, default=Path("dist/epistemic-conformance-1"))
    args = parser.parse_args()
    try:
        manifest = build_benchmark_bundle(ROOT, args.output, args.source_commit)
    except (EpistemicConformanceError, OSError) as exc:
        print(f"EPISTEMIC CONFORMANCE BUILD REFUSED: {exc}")
        return 1
    print(f"benchmark={manifest['benchmark_id']}")
    print(f"benchmark_sha256={manifest['benchmark_sha256']}")
    print(f"cases={manifest['case_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
