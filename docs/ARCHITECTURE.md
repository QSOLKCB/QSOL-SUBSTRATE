# Architecture

QSOL-SUBSTRATE separates canonical meaning from presentation and vendor transport.

## Layers

### Human documentation

`README.md` and `docs/` explain the project in ordinary prose. These documents optimise for understanding, examples, rationale, and maintenance.

### Machine contract

`ai/` contains compact, structured instructions for AI consumers. These files define load order, epistemic states, public-boundary behaviour, retrieval precedence, and consumer obligations.

### Schema

`schema/` defines structural validation for canonical substrate records. As the knowledge payload grows, additional schemas can be added without changing the high-level contract.

### Knowledge payload

Future public identity, project, publication, chronology, terminology, and research records form the actual context dataset. Payload records should remain separable from the consumer contract.

### Adapters

`adapters/` describes how to transport the same canonical substrate into different systems: chat uploads, knowledge bases, project rules, RAG stores, system prompts, or local model wrappers. Adapters are intentionally disposable. The canonical substrate is not.

## Information flow

```text
private canonical context (optional source)
              |
              | explicit-allow export
              v
      QSOL-SUBSTRATE public records
              |
       validate + fingerprint
              |
       canonical public bundle
              |
     +--------+--------+
     |        |        |
   Grok     Sider    Ollama   ...
```

The private source is not required for consumers and is never assumed to be accessible.

## Trust precedence

The substrate is a cache of public context, not a replacement for current primary evidence. A current repository commit, release, DOI record, or other primary source can supersede a stale substrate entry.

Consumers should preserve both the newer evidence and the fact that the substrate snapshot was stale rather than silently rewriting history.

## Determinism

Future build tooling should produce canonical bundles with stable ordering and fingerprints. Model inference itself need not be deterministic for the substrate to be version-identifiable.
