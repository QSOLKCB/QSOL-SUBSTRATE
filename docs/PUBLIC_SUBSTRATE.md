# Canonical Public Substrate

Phase 1 populates QSOL-SUBSTRATE with a selective, machine-readable snapshot of public QSOL context.

The payload is intentionally **not exhaustive**. Inclusion means a public record was materially relevant to the current substrate and supported by public first-party evidence at the snapshot date. Omission means only that the item is unavailable from this snapshot.

## Payload

- `sources/index.json` — public provenance/source registry.
- `identity/public.json` — public identity and affiliation records.
- `context/public.json` — recurring public design/research context.
- `terminology/index.json` — canonical terms, expansions, aliases, and disambiguation notes.
- `projects/index.json` — selective active-public project registry.
- `publications/index.json` — selective verified DOI/publication registry.
- `relationships/graph.json` — project, publication, person, and research-topic relationships.
- `chronology/current.jsonl` — materially relevant public events.

## Snapshot semantics

The snapshot date is `2026-08-15`.

Live primary repository and publication state can supersede this snapshot. Consumers should record the substrate commit used for a task or evaluation, then consult current primary evidence when freshness matters.

## Relationship semantics

A relationship edge appears only when the Phase 1 source set supports it. Missing edges are `unknown`, not `false`. Generic adjacency, thematic similarity, shared authorship, or plausible lineage is not enough to create an edge.

## Publication semantics

The publication registry is deliberately selective. It contains DOI records that could be tied to first-party public repository or release evidence during Phase 1. It is not a complete bibliography of Trent Slade, QSOL-IMC, QSOLKCB, or every repository.

## Privacy boundary

No private repository content is required to use this payload. Phase 1 was assembled from public-facing evidence. Future automated exports from private canonical context remain governed by the explicit-allow/fail-closed policy described in `docs/PRIVACY_AND_EXPORT.md` and `ai/public-boundary.json`.
