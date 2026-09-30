# Review evidence archive

The review evidence formerly tracked in this directory was moved to the local
Git repository `/home/lin/a-stock-agent-evidence` on 2026-08-11.

- Last source commit containing all 247 evidence files: `c493aa8dc4f2649c6241587f55be94f0a11011fb`
- Evidence repository commit: `76d643b55c02c05f263a7c910c7c3cb6a843040f`
- Machine manifest: `/home/lin/a-stock-agent-evidence/MANIFEST.tsv`
- Manifest SHA256: `764454a8e079e416d9e4a95b547a8bf9fb21037c3a61b45f8262db0f0ee05072`

Read the original tracked evidence without restoring obsolete files into the
active tree:

```bash
git ls-tree -r --name-only c493aa8 docs/reviews
git show c493aa8:docs/reviews/<evidence-path>
```

The completed architecture-plan review added later is retained in source history:

```bash
git show f5307f7:docs/reviews/a-stock-codex-plan-agy-review.md
```

The external repository is the canonical location for the 2026-08-11 archived
packets. Historical reviews are evidence, not new execution instructions.
