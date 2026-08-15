# Grok Adapter

Phase 4 implements two Grok-family transports:

1. `dist/adapters/grok/chat-bootstrap.txt` — complete chat/file bootstrap;
2. `dist/adapters/xai-retrieval/` — persistent xAI Collections retrieval document plus upload metadata.

The same canonical projection is used by both. Delivery changes; facts do not.

The generated bundle preserves `known`, `retrieved`, `inferred`, `unknown`, `conflict`, and `fiction` semantics and records the exact substrate snapshot, source commit, substrate fingerprint, projection fingerprint, and adapter identity.

Runtime collection IDs, API keys, and model IDs are deliberately excluded from canonical substrate state.

See `docs/ADAPTERS.md`.
