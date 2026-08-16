#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mixed_register_core import MixedRegisterError, score_claim_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a MIXED-REGISTER/1 claim audit.")
    parser.add_argument("audit", help="Path to qsol-claim-audit JSON")
    parser.add_argument("--bundle", default="dist/mixed-register-1")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
        report = score_claim_audit(root, Path(args.bundle), audit)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, MixedRegisterError) as exc:
        print(f"MIXED-REGISTER SCORE REFUSED: {exc}")
        return 2
    rendered = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.output == "-":
        print(rendered, end="")
    else:
        Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
