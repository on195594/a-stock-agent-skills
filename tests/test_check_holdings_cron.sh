#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/home" "$TMP/state"
cat > "$TMP/bin/a-stock-cache" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_CALLS"
printf '%s\n' "${FAKE_OUTPUT:-无预警}"
[[ "${FAKE_FAIL:-0}" == 1 ]] && exit 3
exit 0
SH
chmod +x "$TMP/bin/a-stock-cache"
cat > "$TMP/runtime.env" <<EOF
A_STOCK_STATE_DIR=$TMP/state
A_STOCK_LOG_DIR=$TMP/state/logs
A_STOCK_LOCK_DIR=$TMP/state/locks
A_STOCK_NOTIFY_MODE=disabled
EOF
chmod 600 "$TMP/runtime.env"
export HOME="$TMP/home" PATH="$TMP/bin:/usr/bin:/bin" A_STOCK_CONFIG_FILE="$TMP/runtime.env" FAKE_CALLS="$TMP/calls"

FAKE_OUTPUT='无预警' bash "$ROOT/scripts/check-holdings-cron.sh"
grep -Fq 'check-holdings' "$TMP/calls"
! test -e "$TMP/curl_calls"
grep -Fq '持仓止损检查：无预警' "$TMP/state/logs/check-holdings.log"

FAKE_OUTPUT='招商银行 🔴 已跌破止损线' bash "$ROOT/scripts/check-holdings-cron.sh"
grep -Fq '持仓止损检查：触发预警' "$TMP/state/logs/check-holdings.log"
! test -e "$TMP/curl_calls"

if FAKE_FAIL=1 bash "$ROOT/scripts/check-holdings-cron.sh"; then
  echo 'failed cache command was masked' >&2
  exit 1
fi
grep -Fq '持仓止损检查命令失败' "$TMP/state/logs/check-holdings.log"

chmod 644 "$TMP/runtime.env"
if bash "$ROOT/scripts/check-holdings-cron.sh"; then
  echo 'insecure runtime config was accepted' >&2
  exit 1
fi
chmod 600 "$TMP/runtime.env"
printf '%s\n' 'A_STOCK_NOTIFY_MODE=telegram' >> "$TMP/runtime.env"
if bash "$ROOT/scripts/check-holdings-cron.sh"; then
  echo 'missing Telegram credentials were masked' >&2
  exit 1
fi
printf '%s\n' 'A_STOCK_NOTIFY_MODE=unknown' >> "$TMP/runtime.env"
if bash "$ROOT/scripts/check-holdings-cron.sh"; then
  echo 'unknown notification mode was accepted' >&2
  exit 1
fi
mkdir -p "$TMP/home/.local/bin"
cat > "$TMP/home/.local/bin/curl" <<'SH'
#!/usr/bin/env bash
exit 7
SH
chmod +x "$TMP/home/.local/bin/curl"
cat >> "$TMP/runtime.env" <<'EOF'
A_STOCK_NOTIFY_MODE=telegram
TELEGRAM_BOT_TOKEN=test-token
TELEGRAM_CHAT_ID=test-chat
EOF
if FAKE_OUTPUT='招商银行 🔴 已跌破止损线' bash "$ROOT/scripts/check-holdings-cron.sh"; then
  echo 'failed Telegram request was masked' >&2
  exit 1
fi
grep -Fq 'Telegram request failed' "$TMP/state/logs/check-holdings.log"

if rg -n 'a-stock-tracker/\.env|\.claude/skills|cache\.py|python3' "$ROOT/scripts/check-holdings-cron.sh"; then
  echo 'legacy cron path found' >&2
  exit 1
fi
echo 'cron smoke passed'
