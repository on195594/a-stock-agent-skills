# Source provenance

Captured 2026-08-08 before canonical extraction.

| Source | Commit | Working tree |
|---|---|---|
| `/home/lin/.claude/skills/a-stock-research` | `9dfec3c687100ed389b89b69a5e96027030b1c53` | clean |
| `/home/lin/.claude/skills/a-stock-monitor` | `cab32fcec3019fddca6fa84dc64198ed1dc3a340` | clean |
| `/home/lin/.claude/skills/a-stock-qa` | `0212ad8ed260334e3ee31fc3877a0f2df981175f` | clean |
| `/home/lin/a-stock-lib` | `e52e12566067c5a6d8adf9247991a490636a7c36` | clean |
| `/home/lin/a-stock-tracker` | `8c095fc9e87fbdcac6464af0cc5f7082ef4d43be` | clean |

The tracked-file inventories are in `source-files-*.txt`. The canonical
mapping is recorded in `source-mapping.md`; excluded mutable and host-owned
files are listed in `excluded-files.md`.

The source research database was observed by file metadata only:

```text
/home/lin/.claude/skills/a-stock-research/cache.db 22904832 bytes
```

The host denied `crontab -l` during the non-invasive baseline. No cron state
was changed; production cron remains an M7-only concern.
