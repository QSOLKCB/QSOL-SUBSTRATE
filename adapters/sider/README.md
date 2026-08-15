# Sider Adapter

The Sider integration should use a compact persistent bootstrap together with indexed or uploaded QSOL-SUBSTRATE records.

Recommended split:

- persistent prompt: epistemic rules, public-boundary semantics, retrieval precedence;
- knowledge base: larger canonical substrate payload;
- task prompt: the user's actual question.

This makes it possible to compare multiple underlying models against the same substrate while changing only the model.

Do not copy private QSOL-CONTEXT records into Sider merely because the public adapter exists.
