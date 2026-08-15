from __future__ import annotations

import argparse
from pathlib import Path

from projection_core import validate_projection_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate QSOL-SUBSTRATE model projection experiment bundle")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--bundle", type=Path, default=Path("dist/projections"))
    args = parser.parse_args()
    findings = validate_projection_bundle(args.root, args.bundle)
    if findings:
        print(f"PROJECTION VALIDATION REFUSED: {len(findings)} finding(s)")
        for finding in findings:
            print(f"- [{finding.code}] {finding.path}: {finding.message}")
        return 1
    print(f"VALID projection_bundle={args.bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
