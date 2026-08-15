# Sider Adapter

Phase 4 implements the Sider transport as a deterministic two-file bundle:

```text
dist/adapters/sider/
├── prompt.txt
└── knowledge-base.md
```

`prompt.txt` contains compact persistent epistemic/bootstrap rules. `knowledge-base.md` contains the complete canonical public substrate projection.

This split allows the selected underlying model to change without changing the substrate evidence supplied to it.

The adapter never reads or copies private QSOL-CONTEXT data.

See `docs/ADAPTERS.md` for build, identity, and validation rules.
