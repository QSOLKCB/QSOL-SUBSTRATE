# Ollama / Local Model Adapter

Phase 4 implements the Ollama transport as:

```text
dist/adapters/ollama/
├── Modelfile.template
└── system-context.txt
```

`system-context.txt` contains the complete canonical projection. `Modelfile.template` embeds that exact context in an Ollama `SYSTEM` block and leaves the base model as the explicit runtime placeholder `REPLACE_WITH_BASE_MODEL`.

Replace the placeholder with an exact model tag or immutable local model reference before creating the model. The selected model is runtime configuration, not a QSOL-SUBSTRATE fact.

The same system context may also be supplied through Ollama's API `system` field.

See `docs/ADAPTERS.md`.
