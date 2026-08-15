from __future__ import annotations

import argparse
from pathlib import Path

from probe_core import ProbeError, build_scoring_oracle_run
from substrate_integrity import canonical_json_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Phase 7 scoring-oracle run (self-test only, not an empirical benchmark)")
    parser.add_argument("--bundle", type=Path, default=Path("dist/probes"))
    parser.add_argument("--condition", default="naked")
    parser.add_argument("--output", type=Path, default=Path("probe-oracle-run.json"))
    args = parser.parse_args()
    try:
        run = build_scoring_oracle_run(args.bundle, args.condition)
        args.output.write_bytes(canonical_json_bytes(run))
    except (OSError, ProbeError) as exc:
        print(f"PROBE ORACLE BUILD REFUSED: {exc}")
        return 1
    print(f"scoring_oracle_responses={len(run['responses'])}")
    print("empirical_model_result=false")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
