# Frequently Asked Questions

## Does QSOL-SUBSTRATE train a model?

No. It supplies external context and reasoning contracts. It does not modify model weights.

## Will it eliminate hallucinations?

No. It can reduce a useful class of errors caused by missing QSOL-specific context, ambiguous terminology, stale project relationships, and unsupported inference. Models can still reason incorrectly.

## Is this QSOL-NEXUS?

No. QSOL-SUBSTRATE is a portable public context layer. It does not reproduce a specialised runtime, persistent world state, agent governance, or other runtime-specific behaviour.

## Is this the complete private QSOL context?

No. It is intentionally incomplete and public-facing. Absence means unavailable from this substrate, not false.

## Why JSON for AI documentation?

Structured contracts reduce ambiguity, support validation, and let different tooling consume the same semantics without scraping prose.

## Why keep a human README at all?

Humans need rationale, examples, trade-offs, maintenance guidance, and a comprehensible entrypoint. The two surfaces serve different readers.

## Can another project reuse this architecture?

Yes, subject to the repository's Apache-2.0 license. The protocol concepts are intentionally vendor-neutral.
