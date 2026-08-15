# Contributing to QSOL-SUBSTRATE

QSOL-SUBSTRATE is both documentation and a machine-consumable public knowledge contract. Contributions therefore need to be readable by humans and predictable for automated consumers.

## Before contributing

Please understand three rules first:

1. public does not mean complete;
2. omission means unavailable, not false;
3. claims require an explicit epistemic and provenance basis.

## Contribution types

Useful contributions include corrections to public facts, improved provenance references, schema or validation improvements, clearer human documentation, vendor adapters that preserve canonical semantics, deterministic probe cases, reproducibility tooling, and privacy/export hardening.

## Public-data requirement

Do not submit private or ambiguously public information. Information should be intentionally public and suitable for indefinite indexing, mirroring, and machine ingestion. If you cannot establish that a record is safe for public export, do not add it.

## Structured data

Machine-readable additions should use stable canonical identifiers, identify provenance where practical, declare epistemic state, avoid free-form fields when a controlled vocabulary exists, avoid encoding conclusions stronger than the source supports, and validate against repository schemas once validation tooling is present.

## Human documentation

Human prose should explain purpose, limitations, trade-offs, and examples. It should not quietly redefine a machine contract.

## Adapter contributions

Adapters may translate canonical substrate into a target model's preferred context mechanism, but may not modify canonical facts or instruct a model to evade its own safety rules.

## Commit and PR expectations

Keep changes scoped and explain what changed, why it changed, whether machine semantics changed, whether schema changes are required, and whether public/private boundaries were affected.

Apache-2.0 applies to repository contributions under the terms of `LICENSE`.
