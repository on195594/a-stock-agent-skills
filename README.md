# Portable A-Stock Agent Skills Suite

Canonical source for the `a-stock-research`, `a-stock-monitor`, and
`a-stock-qa` Agent Skills.

The runtime is intentionally small and exposes only:

```text
a-stock-cache
a-stock-fetch
a-stock-install
```

Research and monitor state lives outside this repository under the XDG data
directory. QA is a pure-text rubric checker and does not require the Python
runtime or market-data credentials.

Bootstrap with Python 3.13+ and an explicit `a-stock-lib` source checkout or
wheel:

```bash
python3 scripts/install.py --client all --mode symlink \
  --source "$PWD" --a-stock-lib-source /path/to/a-stock-lib
```

See the migration records in `docs/migration/` and the governing Spec for
production cutover boundaries.
