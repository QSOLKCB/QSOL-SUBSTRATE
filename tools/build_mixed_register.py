#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from mixed_register_core import MixedRegisterError, build_mixed_register_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic MIXED-REGISTER/1 evaluation bundle.")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", default="dist/mixed-register-1")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        manifest = build_mixed_register_bundle(root, Path(args.output), args.source_commit)
    except MixedRegisterError as exc:
        print(f"MIXED-REGISTER BUILD REFUSED: {exc}")
        return 2
    print(f"claims={manifest['claim_count']}")
    print(f"bundle_sha256={manifest['bundle_sha256']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    print(f"output={Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
