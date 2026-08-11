# Review evidence archive

The review evidence formerly tracked in this directory was moved to the local
Git repository `/home/lin/a-stock-agent-evidence` on 2026-08-11.

- Last source commit containing all 247 evidence files: `c493aa8dc4f2649c6241587f55be94f0a11011fb`
- Evidence repository commit: `76d643b55c02c05f263a7c910c7c3cb6a843040f`
- Machine manifest: `/home/lin/a-stock-agent-evidence/MANIFEST.tsv`
- Manifest SHA256: `764454a8e079e416d9e4a95b547a8bf9fb21037c3a61b45f8262db0f0ee05072`

Restore the original tracked directory from the source repository history:

```bash
git restore --source=c493aa8dc4f2649c6241587f55be94f0a11011fb -- docs/reviews
```

The external repository is the canonical location for retained review packets.
