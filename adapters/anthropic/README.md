# Anthropic-Compatible Adapter

Phase 4 generates:

```text
dist/adapters/anthropic/
├── system-prompt.txt
└── request.example.json
```

The system prompt contains the complete canonical projection. The request template places that exact text in the Messages-style `system` field and leaves model ID and user task as runtime placeholders.

The adapter changes transport only and does not redefine substrate facts.

See `docs/ADAPTERS.md`.
