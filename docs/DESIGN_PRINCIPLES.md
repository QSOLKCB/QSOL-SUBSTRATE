# Design Principles

QSOL-SUBSTRATE follows a small set of architectural principles.

## Canonical meaning, disposable adapters

The public substrate should outlive any particular AI vendor. Canonical records and contracts are stable; adapters are replaceable transport layers.

## Public means intentionally public

Publication is explicit-allow only. The project does not rely on a blacklist to protect private context.

## Unknown is a valid answer

The substrate should make it easier for a model to say `unknown`, not merely give it more material from which to improvise.

## Provenance before fluency

A smooth answer is less important than preserving where information came from and how strongly it is supported.

## Truth does not spread by adjacency

A supported claim does not make a neighbouring claim supported. Every substantive claim must be evaluated against its own evidence and provenance rather than inheriting credibility from surrounding true material.

Normative guard: `ADJACENT_TRUTH != INHERITED_TRUTH`.

## Smallest sufficient context

Consumers should retrieve only what is necessary for the task. Larger prompts are not automatically better prompts.

## Live primary evidence wins

A current primary repository or publication record can supersede stale substrate state. Reproducibility still requires recording which substrate snapshot was used.

## Fiction stays fiction

Satire, game lore, personas, simulation, and deliberate absurdity must not silently become biography or empirical fact.

## Machine semantics are structured

Human prose explains the system. JSON contracts define machine semantics.
