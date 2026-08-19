from __future__ import annotations

import argparse
from pathlib import Path

from mode_delivery_core import ModeDeliveryError, build_mode_delivery_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind QSOL-MODE-POLICY/1 into deterministic delivery surfaces")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/mode-delivery"))
    args = parser.parse_args()
    try:
        manifest = build_mode_delivery_bundle(ROOT, args.output, args.source_commit)
    except (OSError, ModeDeliveryError) as exc:
        print(f"MODE DELIVERY BUILD REFUSED: {exc}")
        return 1
    print(f"mode_policy_sha256={manifest['mode_policy']['mode_policy_sha256']}")
    print(f"tool_less_profiles={len(manifest['tool_less_profiles'])}")
    print(f"bundle_sha256={manifest['bundle_sha256']}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
