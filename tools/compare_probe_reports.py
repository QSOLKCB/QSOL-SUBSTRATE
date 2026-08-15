from __future__ import annotations

import argparse
import json
from pathlib import Path

from probe_core import ProbeError, compare_probe_reports, comparison_markdown
from substrate_integrity import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]


def _prepare_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Phase 7 model report cards under a common probe/substrate identity")
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown")
    args = parser.parse_args()
    try:
        reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.reports]
        comparison = compare_probe_reports(ROOT, reports)
        _prepare_parent(args.output)
        args.output.write_bytes(canonical_json_bytes(comparison))
        if args.markdown:
            markdown_path = Path(args.markdown)
            _prepare_parent(markdown_path)
            markdown_path.write_text(comparison_markdown(comparison), encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ProbeError) as exc:
        print(f"PROBE COMPARISON REFUSED: {exc}")
        return 1
    print(f"models={len(comparison['models'])}")
    print(f"rows={len(comparison['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
