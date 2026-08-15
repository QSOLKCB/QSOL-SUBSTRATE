#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from adapter_core import AdapterError, build_adapter_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic portable QSOL-SUBSTRATE adapter bundles.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("dist/adapters"))
    parser.add_argument("--source-commit", required=True, help="Exact 40-character git commit identifying this adapter build.")
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else args.root / args.output
    try:
        manifest = build_adapter_bundle(args.root, output, args.source_commit)
    except AdapterError as exc:
        print(f"ADAPTER BUILD REFUSED: {exc}")
        return 1

    print(f"built_adapters={len(manifest['adapters'])}")
    print(f"substrate_version={manifest['substrate']['version']}")
    print(f"source_commit={manifest['substrate']['source_commit']}")
    print(f"substrate_sha256={manifest['substrate']['substrate_sha256']}")
    print(f"adapter_bundle_sha256={manifest['adapter_bundle_sha256']}")
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
