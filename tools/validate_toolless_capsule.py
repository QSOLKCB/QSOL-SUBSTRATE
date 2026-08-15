#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from toolless_core import validate_toolless_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated QSOL-SUBSTRATE tool-less capsules.")
    parser.add_argument("--bundle", default="dist/toolless", help="Capsule bundle directory.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    bundle = Path(args.bundle)
    findings = validate_toolless_bundle(root, bundle)
    if findings:
        print(f"TOOLLESS VALIDATION REFUSED findings={len(findings)}")
        for finding in findings:
            print(f"{finding.code}\t{finding.path}\t{finding.message}")
        return 2

    print(f"VALID toolless_bundle={bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
