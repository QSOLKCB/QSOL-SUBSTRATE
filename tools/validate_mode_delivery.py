from __future__ import annotations

import argparse
from pathlib import Path

from mode_delivery_core import validate_mode_delivery_bundle

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic QSOL mode-delivery bindings")
    parser.add_argument("--bundle", type=Path, default=Path("dist/mode-delivery"))
    args = parser.parse_args()
    findings = validate_mode_delivery_bundle(ROOT, args.bundle)
    if findings:
        for finding in findings:
            print(f"INVALID mode delivery: {finding}")
        return 1
    print(f"VALID mode_delivery_bundle={args.bundle.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
