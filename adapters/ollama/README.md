# Ollama / Local Model Adapter

Local models can consume QSOL-SUBSTRATE without depending on a hosted vendor.

Recommended architecture:

```text
compact system bootstrap
        +
local indexed public substrate
        +
user task
```

A generated Modelfile may embed the compact consumer rules, while larger public records remain in a local retrieval store or task-specific bundle.

The adapter should not compensate for a small context window by deleting provenance or uncertainty metadata. Prefer better selection and chunking.

Future work may add generated Modelfiles and deterministic local-model probe runners.
