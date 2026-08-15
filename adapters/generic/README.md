# Generic Adapter

Use this adapter when the target system has no dedicated integration.

Recommended pattern:

1. load `ai/bootstrap.json` as persistent high-priority context where possible;
2. provide or index the canonical public payload;
3. retrieve the smallest sufficient records for the current question;
4. preserve `known`, `retrieved`, `inferred`, `unknown`, `conflict`, and `fiction` semantics;
5. record substrate version/commit for reproducible evaluations.

A future generic exporter should produce a compact bootstrap plus a deterministic single-file public bundle.
