# Grok Build Adapter

Phase 4 generates a repository-scoped Grok Build bundle:

```text
dist/adapters/grok-build/
├── AGENTS.md
├── knowledge/QSOL-SUBSTRATE.txt
└── .grok/skills/qsol-substrate/SKILL.md
```

`AGENTS.md` carries compact project rules. The skill defines the reusable loading procedure. The knowledge file contains the complete canonical projection.

This avoids duplicating factual substrate into project rules while preserving the exact snapshot, source commit, substrate fingerprint, projection fingerprint, and adapter identity.

See `docs/ADAPTERS.md`.
