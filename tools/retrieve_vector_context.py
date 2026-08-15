from __future__ import annotations

import argparse
from pathlib import Path

from vector_core import _context_closure, _read_records, render_retrieved_context, retrieve


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve deterministic context from a QSOL-SUBSTRATE vector bundle")
    parser.add_argument("query")
    parser.add_argument("--bundle", type=Path, default=Path("dist/vectors"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = _read_records(args.bundle / "records.jsonl")
    embeddings = (args.bundle / "embeddings.f16").read_bytes()
    primary = retrieve(rows, embeddings, args.query, top_k=args.top_k)
    primary_ids = [row["canonical_id"] for row in primary]
    closed_ids = _context_closure(primary_ids, rows)
    context = render_retrieved_context(rows, closed_ids)

    if args.output:
        args.output.write_text(context, encoding="utf-8")
    else:
        print(context, end="")
    print("# primary=" + ",".join(primary_ids))
    print("# closure=" + ",".join(closed_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
