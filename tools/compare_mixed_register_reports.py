#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mixed_register_core import MixedRegisterError, compare_mixed_register_reports


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare empirical MIXED-REGISTER/1 reports from one immutable model revision.")
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()
    try:
        reports = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.reports]
        comparison = compare_mixed_register_reports(reports)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, MixedRegisterError) as exc:
        print(f"MIXED-REGISTER COMPARISON REFUSED: {exc}")
        return 2
    rendered = json.dumps(comparison, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.output == "-":
        print(rendered, end="")
    else:
        Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
