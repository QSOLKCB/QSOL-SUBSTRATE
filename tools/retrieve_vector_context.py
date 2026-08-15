from __future__ import annotations

import argparse
from pathlib import Path

from vector_core import (
    VectorError,
    _context_closure,
    _load_json,
    _read_records,
    render_retrieved_context,
    retrieve,
    validate_vector_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def _safe_context_output(path: Path) -> Path:
    if path.exists() and path.is_symlink():
        raise VectorError("refusing to write retrieved context through a symlink")
    resolved = path.resolve()
    root = ROOT.resolve()
    retrieved_root = (root / "dist" / "retrieved").resolve()
    if resolved == root or resolved in root.parents:
        raise VectorError("retrieved-context output may not replace or contain repository root")
    if root in resolved.parents and retrieved_root not in resolved.parents:
        raise VectorError("in-repository retrieved-context output is restricted to dist/retrieved/")
    if resolved.exists() and not resolved.is_file():
        raise VectorError("retrieved-context output must be a regular file path")
    return resolved


def _validated_bundle_identity(bundle: Path) -> dict[str, str]:
    findings = validate_vector_bundle(ROOT, bundle)
    if findings:
        codes = ",".join(sorted({finding.code for finding in findings}))
        raise VectorError(f"vector bundle validation failed ({codes})")
    manifest = _load_json(bundle / "manifest.json")
    substrate = manifest.get("substrate") if isinstance(manifest, dict) else None
    if not isinstance(substrate, dict):
        raise VectorError("validated vector manifest is missing substrate identity")
    return substrate


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve deterministic context from a QSOL-SUBSTRATE vector bundle")
    parser.add_argument("query")
    parser.add_argument("--bundle", type=Path, default=Path("dist/vectors"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        identity = _validated_bundle_identity(args.bundle)
        rows = _read_records(args.bundle / "records.jsonl")
        embeddings = (args.bundle / "embeddings.f16").read_bytes()
        primary = retrieve(rows, embeddings, args.query, top_k=args.top_k)
        primary_ids = [row["canonical_id"] for row in primary]
        closed_ids = _context_closure(primary_ids, rows)
        context = render_retrieved_context(rows, closed_ids, identity)
        if args.output:
            output = _safe_context_output(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(context, encoding="utf-8")
        else:
            print(context, end="")
    except (OSError, UnicodeDecodeError, VectorError) as exc:
        print(f"VECTOR RETRIEVAL REFUSED: {exc}")
        return 1

    print("# primary=" + ",".join(primary_ids))
    print("# closure=" + ",".join(closed_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
