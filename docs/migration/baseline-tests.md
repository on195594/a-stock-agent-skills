# Baseline

The historical Spec records the pre-migration baseline as 155 `a-stock-lib`
tests, 12 monitor tests, and 558 research tests with one version-contract
failure. This repository does not claim those external results were rerun
during M0; later gates must run the migrated tests and record their output.

The source DB was inspected without opening a SQLite connection. `crontab -l`
was attempted and denied by the host; no write or scheduling operation was
performed.
