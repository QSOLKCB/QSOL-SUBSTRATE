from __future__ import annotations

import argparse
from pathlib import Path

from release_core import validate_release_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic QSOL-SUBSTRATE Phase 8 release metadata")
    parser.add_argument("--bundle", type=Path, default=Path("dist/release"))
    parser.add_argument("--no-rebuild", action="store_true", help="skip deterministic rebuild verification")
    args = parser.parse_args()
    findings = validate_release_bundle(ROOT, args.bundle, deterministic_rebuild=not args.no_rebuild)
    if findings:
        for finding in findings:
            print(f"INVALID release: {finding}")
        return 1
    print(f"VALID release_bundle={args.bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
