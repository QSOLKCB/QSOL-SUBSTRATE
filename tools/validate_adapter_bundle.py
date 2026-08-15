#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adapter_core import validate_adapter_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated QSOL-SUBSTRATE portable adapter bundle.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--bundle", type=Path, default=Path("dist/adapters"))
    args = parser.parse_args()

    bundle = args.bundle if args.bundle.is_absolute() else args.root / args.bundle
    findings = validate_adapter_bundle(args.root, bundle)
    if findings:
        print(f"ADAPTER VALIDATION REFUSED: {len(findings)} finding(s)", file=sys.stderr)
        for finding in findings:
            print(f"- [{finding.code}] {finding.path}: {finding.message}", file=sys.stderr)
        return 1
    print(f"VALID portable_adapter_bundle={bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
