from __future__ import annotations

import argparse
from pathlib import Path

from vector_core import VectorError, _context_closure, _read_records, render_retrieved_context, retrieve

ROOT = Path(__file__).resolve().parents[1]


def _safe_context_output(path: Path) -> Path:
    if path.exists() and path.is_symlink():
        raise VectorError("refusing to write retrieved context through a symlink")
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or resolved in root.parents:
        raise VectorError("retrieved-context output may not replace or contain repository root")
    if root in resolved.parents and root / "dist" not in resolved.parents:
        raise VectorError("in-repository retrieved-context output is restricted to dist/")
    if resolved.exists() and not resolved.is_file():
        raise VectorError("retrieved-context output must be a regular file path")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve deterministic context from a QSOL-SUBSTRATE vector bundle")
    parser.add_argument("query")
    parser.add_argument("--bundle", type=Path, default=Path("dist/vectors"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        rows = _read_records(args.bundle / "records.jsonl")
        embeddings = (args.bundle / "embeddings.f16").read_bytes()
        primary = retrieve(rows, embeddings, args.query, top_k=args.top_k)
        primary_ids = [row["canonical_id"] for row in primary]
        closed_ids = _context_closure(primary_ids, rows)
        context = render_retrieved_context(rows, closed_ids)
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
