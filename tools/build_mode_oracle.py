from __future__ import annotations

import argparse
from pathlib import Path

from mode_core import ModeError, build_oracle_run
from substrate_integrity import canonical_json_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic MODE-CONFUSION/1 scoring-oracle self-test run")
    parser.add_argument("--bundle", type=Path, default=Path("dist/modes"))
    parser.add_argument("--output", type=Path, default=Path("mode-oracle-run.json"))
    args = parser.parse_args()
    try:
        run = build_oracle_run(args.bundle)
        args.output.write_bytes(canonical_json_bytes(run))
    except (OSError, ModeError) as exc:
        print(f"MODE ORACLE BUILD REFUSED: {exc}")
        return 1
    print(f"responses={len(run['responses'])}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
