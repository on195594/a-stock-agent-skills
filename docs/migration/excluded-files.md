# Excluded source files

The extraction intentionally excludes mutable or host-owned material:

- `.git/`, `.claude/`, `.agents/`, `.hermes/`, and AI-collaboration state;
- `memory/`, scratch/review state, logs, locks, caches, databases and WAL/SHM;
- `.env`, token material, and tracker production configuration;
- source-project virtual environments and generated artifacts.

Only tracked Skill instructions, references, deterministic source modules and
tests were copied into the canonical tree.
