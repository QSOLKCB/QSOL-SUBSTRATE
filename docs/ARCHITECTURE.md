# Architecture

QSOL-SUBSTRATE separates canonical meaning from presentation and vendor transport.

## Layers

### Human documentation

`README.md` and `docs/` explain the project in ordinary prose. These documents optimise for understanding, examples, rationale, and maintenance.

### Machine contract

`ai/` contains compact, structured instructions for AI consumers. These files define mandatory contract load order, epistemic states, public-boundary behaviour, retrieval precedence, and consumer obligations.

The bootstrap deliberately separates **mandatory contract loading** from **selective payload retrieval**. Consumers load the normative machine contract first, then retrieve only the canonical payload records needed for the current task.

### Schema

`schema/` defines structural validation for canonical substrate records. The shared canonical record schema includes identity, organization, project, repository, publication, research-topic, term, event, relationship, source, claim, adapter, and probe record types.

### Canonical public knowledge payload

Phase 1 implements the public context dataset under these roots:

```text
sources/index.json
identity/public.json
context/public.json
terminology/index.json
projects/index.json
publications/index.json
relationships/graph.json
chronology/current.jsonl
```

These records provide the currently selected public identity/context, QSOL terminology and aliases, active-project registry, verified publication/DOI registry, project/research relationship graph, provenance source registry, and materially relevant chronology.

The payload is **selective, not exhaustive**. Missing records and missing relationship edges mean unavailable/unknown from this snapshot, not false.

Payload records remain separable from the consumer contract so the knowledge layer can evolve without turning every query into a full-dataset load.

### Provenance snapshots

`sources/index.json` stores live source locators together with snapshot evidence. First-party repository documents retain an exact commit-pinned URL; release records retain the release tag commit. This preserves the evidence used by the substrate snapshot while still allowing live primary sources to supersede stale state later.

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

## Retrieval flow

```text
ai/bootstrap.json
       |
       v
mandatory machine contracts
       |
       v
identify task-relevant records
       |
       v
selective canonical payload retrieval
       |
       +--> sources/index.json when provenance resolution is required
```

This preserves the `smallest_sufficient_context` rule as the registries grow.

## Trust precedence

The substrate is a cache of public context, not a replacement for current primary evidence. A current repository commit, release, DOI record, or other primary source can supersede a stale substrate entry.

Consumers should preserve both the newer evidence and the fact that the substrate snapshot was stale rather than silently rewriting history.

## Determinism

Future build tooling should produce canonical bundles with stable ordering and fingerprints. Model inference itself need not be deterministic for the substrate to be version-identifiable.
