from __future__ import annotations

import argparse
from pathlib import Path

from vector_core import validate_vector_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic QSOL-SUBSTRATE vector projection")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--bundle", type=Path, default=Path("dist/vectors"))
    args = parser.parse_args()
    findings = validate_vector_bundle(args.root, args.bundle)
    if findings:
        print(f"VECTOR VALIDATION REFUSED: {len(findings)} finding(s)")
        for finding in findings:
            print(f"- [{finding.code}] {finding.path}: {finding.message}")
        return 1
    print(f"VALID vector_bundle={args.bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
