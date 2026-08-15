#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from substrate_integrity import build_fingerprint, canonical_json_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic SHA-256 identity of the canonical public substrate payload.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    fingerprint = build_fingerprint(args.root)
    data = canonical_json_bytes(fingerprint)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
    print(f"substrate_sha256={fingerprint['substrate_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
