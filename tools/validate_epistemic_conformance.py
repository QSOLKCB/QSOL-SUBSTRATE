from __future__ import annotations

import argparse
from pathlib import Path

from epistemic_conformance_core import validate_benchmark_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic EPISTEMIC-CONFORMANCE/1 bundle")
    parser.add_argument("--bundle", type=Path, default=Path("dist/epistemic-conformance-1"))
    args = parser.parse_args()
    findings = validate_benchmark_bundle(ROOT, args.bundle)
    if findings:
        for finding in findings:
            print(finding)
        return 1
    print("epistemic_conformance_validation=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
