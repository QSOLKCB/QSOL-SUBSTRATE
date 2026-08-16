#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mixed_register_core import MixedRegisterError, build_scoring_oracle_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic MIXED-REGISTER/1 scoring-oracle audit.")
    parser.add_argument("--bundle", default="dist/mixed-register-1")
    parser.add_argument("--condition", default="full")
    parser.add_argument("--output", default="dist/mixed-register-1-oracle.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        audit = build_scoring_oracle_audit(root, Path(args.bundle), args.condition)
    except MixedRegisterError as exc:
        print(f"MIXED-REGISTER ORACLE REFUSED: {exc}")
        return 2
    Path(args.output).write_text(json.dumps(audit, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"output={Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
