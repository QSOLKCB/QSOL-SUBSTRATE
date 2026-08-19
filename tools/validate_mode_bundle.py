from __future__ import annotations

import argparse
from pathlib import Path

from mode_core import validate_mode_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic QSOL-SUBSTRATE mode-policy bundle")
    parser.add_argument("--bundle", type=Path, default=Path("dist/modes"))
    args = parser.parse_args()
    findings = validate_mode_bundle(ROOT, args.bundle)
    if findings:
        for finding in findings:
            print(f"INVALID mode bundle [{finding.code}] {finding.path}: {finding.message}")
        return 1
    print(f"VALID mode_bundle={args.bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
