# Architecture

QSOL-SUBSTRATE separates canonical meaning from presentation, private-source publication, and vendor transport.

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

### Private-to-public export boundary

Phase 2 implements a maintainer-side publication pipeline under:

```text
public_export/
├── policy.json
├── include.json
└── exclude.json

tools/export_public_substrate.py
```

The private source is optional and local. It is not available to public consumers and is never a runtime dependency of QSOL-SUBSTRATE.

The export boundary is **explicit allow only**. The repository ships with zero private publication grants. Each enabled directive selects one exact source object and names every field permitted to cross the boundary.

Unselected source material is not copied. Public provenance must resolve through the existing public `sources/index.json` registry, which the private exporter cannot modify.

The exporter canonicalises the current public payload, applies explicit grants, performs secret/private-reference scanning, and emits a reviewable staging bundle plus a public export manifest and fingerprint. It does not commit or publish the result automatically.

An optional private audit manifest may retain internal source paths and hashes for local auditing, but the exporter refuses to place that artifact inside the public output directory.

### Adapters

`adapters/` describes how to transport the same canonical substrate into different systems: chat uploads, knowledge bases, project rules, RAG stores, system prompts, or local model wrappers. Adapters are intentionally disposable. The canonical substrate is not.

## Information flow

```text
private canonical context (optional, local)
              |
              | explicit field-level allowlist
              | + secret/private-reference scan
              v
       reviewable export staging
              |
              | deterministic canonicalisation
              | + manifest + fingerprint
              v
      QSOL-SUBSTRATE public records
              |
       future Phase 3 validation + CI
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

## Export flow

```text
QSOL-CONTEXT checkout
       |
       v
verify source protocol
       |
       v
load existing public payload baseline
       |
       v
apply enabled explicit grants only
       |
       +--> every directive visibility == public
       +--> every exported field visibility == public
       +--> every public source_ref already registered
       +--> no source-path escape
       +--> no private source-registry mutation
       |
       v
scan selected values and complete output
       |
       v
canonicalise JSON / JSONL
       |
       v
export-manifest.json + bundle SHA-256
       |
       v
human review
```

Failure at any boundary produces `EXPORT REFUSED`; there is no fallback publication path.

## Trust precedence

The substrate is a cache of public context, not a replacement for current primary evidence. A current repository commit, release, DOI record, or other primary source can supersede a stale substrate entry.

Consumers should preserve both the newer evidence and the fact that the substrate snapshot was stale rather than silently rewriting history.

Private context does not outrank public provenance merely because it is canonical inside QSOL-CONTEXT. A private candidate fact requires explicit publication authority and public source references before it can enter the public substrate.

## Determinism

Phase 2 defines deterministic public-export canonicalisation:

- `qsol-canonical-json-v1` uses UTF-8, lexicographically sorted object keys, compact separators, no NaN/Infinity, preserved Unicode, and one trailing newline;
- `qsol-canonical-jsonl-v1` canonicalises each record the same way while preserving declared record order;
- the public export manifest records SHA-256 and byte length for every canonical payload file;
- the bundle SHA-256 is derived from the ordered public path/hash/length table.

The public manifest deliberately excludes private source paths and private source hashes. Model inference itself need not be deterministic for the substrate and its generated artifacts to be version-identifiable.
