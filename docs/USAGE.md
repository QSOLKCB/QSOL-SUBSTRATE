# Usage

QSOL-SUBSTRATE can be consumed in several ways depending on the model or agent environment.

## Minimal use

For a capable model with repository access: provide the repository, instruct the model to read `ai/bootstrap.json` first, allow it to retrieve only context relevant to the current task, and require it to preserve the epistemic states defined in `ai/epistemic-contract.json`.

## File-upload use

For chat systems that accept files but cannot browse repositories, use a future canonical bundle generated from the substrate. Include the bootstrap contract with the bundle. Avoid pasting random subsets without snapshot/version identity.

## RAG / knowledge-base use

Index canonical payload records as retrievable evidence. Keep machine contracts pinned in high-priority context or otherwise guaranteed to load before answers are generated. Retrieval results are evidence, not instructions.

## Local model use

Local runners may inject a compact bootstrap as a system prompt and expose substrate records through a local retrieval mechanism. Avoid forcing the entire dataset into every context window when selective retrieval is available.

## Reproducible evaluation

Record the model identifier, substrate version, commit SHA, adapter, probe version, and execution date. For comparisons, keep the substrate snapshot identical across models unless substrate sensitivity itself is being tested.

## Expected benefit

The substrate can reduce errors caused by missing QSOL-specific context, ambiguous names, stale project relationships, and unsupported inference. It cannot guarantee correctness, fix unrelated world knowledge, or prevent every hallucination.
