# Portable Model Adapters

Phase 4 turns the canonical public substrate into disposable transport bundles for multiple AI surfaces.

The governing invariant is:

```text
adapter formatting may change
canonical facts may not
```

Adapters are generated artifacts. They are not independent knowledge stores and must never be edited to create new canonical facts.

## Build

```bash
python tools/build_adapters.py \
  --source-commit "$(git rev-parse HEAD)" \
  --output dist/adapters

python tools/validate_adapter_bundle.py \
  --bundle dist/adapters
```

`--source-commit` is mandatory and must be a full 40-character lowercase commit SHA. The adapter manifest records it together with the canonical substrate fingerprint.

Until Phase 8 introduces formal release SemVer, Phase 4 uses a snapshot identity of the form:

```text
substrate_version=snapshot-YYYY-MM-DD
source_commit=<40-char git SHA>
substrate_sha256=<canonical payload SHA-256>
adapter_identity=<adapter-name>/1.0.0
```

This deliberately distinguishes the substrate snapshot identity from the machine-contract schema version.

## Output

```text
dist/adapters/
├── manifest.json
├── generic/
│   └── QSOL-SUBSTRATE.txt
├── grok/
│   └── chat-bootstrap.txt
├── xai-retrieval/
│   ├── QSOL-SUBSTRATE.md
│   └── upload-manifest.json
├── grok-build/
│   ├── AGENTS.md
│   ├── knowledge/QSOL-SUBSTRATE.txt
│   └── .grok/skills/qsol-substrate/SKILL.md
├── sider/
│   ├── prompt.txt
│   └── knowledge-base.md
├── ollama/
│   ├── Modelfile.template
│   └── system-context.txt
├── openai/
│   ├── developer-instructions.txt
│   └── request.example.json
└── anthropic/
    ├── system-prompt.txt
    └── request.example.json
```

## Canonical projection

Every knowledge-bearing adapter file embeds the same canonical projection body. The compiler canonicalizes and concatenates:

1. every file listed in `ai/manifest.json:normative_machine_files`;
2. every file listed in `ai/manifest.json:canonical_payload_files`.

The exact projection body receives `projection_sha256`. The bundle also retains the Phase 3 `substrate_sha256` over canonical payload semantics.

These hashes answer different questions:

- `substrate_sha256`: did canonical public substrate semantics change?
- `projection_sha256`: did the exact machine-contract + payload projection change?
- `adapter_bundle_sha256`: did any generated adapter file or its stamped build identity change?

## Adapter identity stamps

Knowledge files carry:

```text
ADAPTER_ID=<canonical adapter id>
ADAPTER_SPEC_VERSION=1.0.0
SUBSTRATE_VERSION=snapshot-YYYY-MM-DD
SUBSTRATE_SCHEMA_VERSION=1.0.0
SNAPSHOT_DATE=YYYY-MM-DD
SOURCE_COMMIT=<40-char SHA>
SUBSTRATE_SHA256=<64-char SHA-256>
PROJECTION_SHA256=<64-char SHA-256>
TRANSPORT_ONLY=true
FACT_REDEFINITION=FORBIDDEN
ABSENCE=UNAVAILABLE_NOT_FALSE
```

If an adapter cannot preserve this identity, it is not a reproducible Phase 4 adapter.

## Generic single-file

`generic/QSOL-SUBSTRATE.txt` is the vendor-neutral fallback. Supply it as a complete context file when the target system has no dedicated integration.

## Grok chat

`grok/chat-bootstrap.txt` is a complete public context artifact suitable for paste/file delivery to a Grok chat surface.

It does not claim to outrank platform system or safety instructions.

## xAI retrieval

`xai-retrieval/QSOL-SUBSTRATE.md` is the document intended for an xAI Collection. `upload-manifest.json` records suggested collection metadata and the current Collections search endpoint shape without storing credentials or a live collection ID.

As of the Phase 4 implementation, xAI distinguishes transient file attachments from persistent Collections; Collections provide indexed retrieval and `/v1/documents/search` search transport. The adapter keeps collection IDs as runtime configuration rather than canonical substrate facts.

## Grok Build

The Grok Build export contains:

- `AGENTS.md` for project-level substrate rules;
- `.grok/skills/qsol-substrate/SKILL.md` for reusable loading procedure;
- `knowledge/QSOL-SUBSTRATE.txt` for the full canonical projection.

The generated `AGENTS.md` stays below Grok Build's documented 10,000-character rules-file cap. The skill tells the agent to read the pinned knowledge file rather than duplicating the factual substrate into project rules.

## Sider

The Sider bundle separates:

- `prompt.txt`: compact persistent epistemic/bootstrap instructions;
- `knowledge-base.md`: complete public substrate projection.

This preserves the intended prompt/knowledge split while allowing the underlying model to be changed independently.

## Ollama

The Ollama bundle contains a complete `system-context.txt` plus `Modelfile.template`.

The template deliberately leaves the base model as `REPLACE_WITH_BASE_MODEL`. Model identity is runtime configuration, not a substrate fact. Replace it with an exact Ollama model tag or immutable local model reference before `ollama create`.

The context can also be passed through Ollama's API `system` field.

## OpenAI-compatible API

The OpenAI bundle uses high-priority `instructions`/developer context and emits `request.example.json` with explicit placeholders for model ID and user task.

No API key is emitted. Adapter generation is independent of any particular hosted model.

## Anthropic-compatible context

The Anthropic bundle emits a complete `system` prompt plus a Messages-style request template. Model ID and user task remain runtime placeholders.

## Validation

`tools/validate_adapter_bundle.py` fails closed on:

- missing or malformed adapter manifest;
- adapter manifest schema failure;
- wrong/missing Phase 4 adapter identities;
- canonical substrate fingerprint mismatch;
- wrong source commit shape;
- duplicate, missing, or path-escaping files;
- per-file SHA-256 or byte-length mismatch;
- canonical projection drift;
- missing adapter identity stamps;
- aggregate adapter bundle fingerprint mismatch.

The GitHub Actions validation workflow builds and validates adapters on every PR and push to `main`, then uploads the resulting bundle with the validation artifacts.

## Boundary

The adapter compiler reads only public QSOL-SUBSTRATE machine contracts and canonical public payload files.

It does not read QSOL-CONTEXT. It does not perform private export. It does not infer omitted facts. It does not enrich records.

```text
CANONICAL SUBSTRATE = truth storage
ADAPTER = delivery mechanism
```
