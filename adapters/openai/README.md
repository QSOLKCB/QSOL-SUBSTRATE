# OpenAI-Compatible Adapter

Phase 4 generates:

```text
dist/adapters/openai/
├── developer-instructions.txt
└── request.example.json
```

The instructions file contains the complete canonical projection. The request template supplies that exact text as high-priority instructions and leaves model ID and user task as explicit runtime placeholders.

No API key or hosted-model identity is embedded in the substrate.

See `docs/ADAPTERS.md`.
