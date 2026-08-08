# Client shadow invocation record

Captured 2026-08-08 without changing any user-level active Skill entry.

| Client | Version | Isolated discovery recipe | Result |
|---|---|---|---|
| Claude Code | 2.1.226 | `HOME=$SHADOW_ROOT CLAUDE_CONFIG_DIR=$SHADOW_ROOT/.claude claude -p --permission-mode plan --no-session-persistence --add-dir $SUITE ...` | available; M6 smoke |
| Codex | 0.147.0 | `HOME=$SHADOW_ROOT CODEX_HOME=$SHADOW_ROOT/.codex codex exec -s read-only -C $SHADOW_ROOT --add-dir $SUITE --ephemeral ...` | available; M6 smoke |
| Hermes | 0.20.0 (2026.8.3) | `HERMES_HOME=$SHADOW_ROOT/.hermes hermes chat -q -Q -t file,skills -s a-stock-research --max-turns 4 ...` | available; M6 smoke |

The target root is a temporary directory populated by the canonical installer;
no active user-level Skill path is replaced. Hermes shadow deliberately does
not use `-z/--oneshot`, which would bypass dangerous-command approvals.
