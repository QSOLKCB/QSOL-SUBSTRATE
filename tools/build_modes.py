from __future__ import annotations

import argparse
from pathlib import Path

from mode_core import ModeError, build_mode_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic QSOL-SUBSTRATE mode-policy and MODE-CONFUSION/1 bundle")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/modes"))
    args = parser.parse_args()
    try:
        manifest = build_mode_bundle(ROOT, args.output, args.source_commit)
    except (OSError, ModeError) as exc:
        print(f"MODE BUNDLE BUILD REFUSED: {exc}")
        return 1
    print(f"policy_version={manifest['policy_version']}")
    print(f"mode_policy_sha256={manifest['mode_policy_sha256']}")
    print(f"cases={manifest['case_count']}")
    print(f"bundle_sha256={manifest['bundle_sha256']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
