from __future__ import annotations

import argparse
from pathlib import Path

from probe_core import ProbeError, build_probe_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic QSOL-SUBSTRATE Phase 7 probe bundle")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/probes"))
    args = parser.parse_args()
    try:
        manifest = build_probe_bundle(ROOT, args.output, args.source_commit)
    except (OSError, ProbeError) as exc:
        print(f"PROBE BUILD REFUSED: {exc}")
        return 1
    print(f"probe_count={manifest['probe_count']}")
    print(f"substrate_cases={manifest['suite_counts']['substrate']}")
    print(f"yeah_nah_1_cases={manifest['suite_counts']['yeah-nah-1']}")
    print(f"source_commit={manifest['substrate']['source_commit']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    print(f"probe_bundle_sha256={manifest['bundle_sha256']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
