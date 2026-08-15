# About QSOL-SUBSTRATE

QSOL-SUBSTRATE is a public context layer intended to make the public QSOL ecosystem legible to AI systems without giving those systems access to private working memory or a specialised runtime.

Large language models are often asked questions about interconnected projects, unusual terminology, releases, research claims, and historical relationships. When the required background is missing, a model may guess, collapse similarly named concepts together, or infer a relationship that was never established. QSOL-SUBSTRATE addresses that problem by providing a common, versioned body of public context plus rules for reasoning over it.

The project is intentionally vendor-neutral. Its canonical form should not depend on one model provider's memory feature, system prompt format, knowledge-base product, or agent framework. Vendor integrations live at the edge as adapters.

## What “substrate” means here

The term refers to an external informational layer beneath a model interaction. The substrate does not modify neural weights. Instead, it supplies context, provenance, terminology, identity relationships, uncertainty rules, and retrieval guidance before or during inference.

A useful substrate can make a model functionally better informed without pretending that the model was retrained.

## Public by design

This repository should be safe to hand to any model, researcher, crawler, or indexing service. That requires a strong boundary: private context is not merely hidden from the README; it does not belong in the repository at all.

The public substrate is therefore a projection, not a complete memory archive.

## Success criteria

QSOL-SUBSTRATE is successful when a consumer can resolve public QSOL terms and entities consistently, identify relevant primary sources, distinguish fact from inference and deliberate fiction, recognise when information is missing, avoid inventing private or unsupported relationships, reproduce the context state used during a model evaluation, and swap model vendors without rebuilding the knowledge model from scratch.
