# xAI Retrieval Adapter

Phase 4 targets xAI Collections with a generated retrieval document and upload metadata:

```text
dist/adapters/xai-retrieval/
├── QSOL-SUBSTRATE.md
└── upload-manifest.json
```

The Markdown document contains the complete canonical projection. The upload manifest records snapshot, source commit, substrate SHA-256, projection SHA-256, suggested collection name, document fields, and runtime endpoint placeholders.

Collection IDs and credentials are runtime configuration and are never written into canonical substrate records.

See `docs/ADAPTERS.md`.
