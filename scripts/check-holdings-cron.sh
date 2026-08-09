#!/usr/bin/env bash
# Candidate cron entry. It only calls the stable CLI and external config.
set -eEuo pipefail

export PATH="${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

if [[ -n "${A_STOCK_CONFIG_FILE:-}" ]]; then
    [[ -f "$A_STOCK_CONFIG_FILE" ]] || { echo 'runtime config does not exist' >&2; exit 2; }
    config_owner="$(stat -c '%u' -- "$A_STOCK_CONFIG_FILE")"
    config_mode="$(stat -c '%a' -- "$A_STOCK_CONFIG_FILE")"
    (( config_owner == EUID && (8#$config_mode & 077) == 0 )) || {
        echo 'runtime config must be owned by the current user and mode 600 or stricter' >&2
        exit 2
    }
    set -a
    # shellcheck disable=SC1090
    . "$A_STOCK_CONFIG_FILE"
    set +a
fi

NOTIFY_MODE="${A_STOCK_NOTIFY_MODE:-disabled}"
LOG_DIR="${A_STOCK_LOG_DIR:-${HOME}/.local/share/a-stock-agent/logs}"
LOCK_DIR="${A_STOCK_LOCK_DIR:-${HOME}/.local/share/a-stock-agent/locks}"
LOG="${LOG_DIR}/check-holdings.log"
LOCK_FILE="${LOCK_DIR}/check-holdings.lock"
TIMEOUT="${CHECK_HOLDINGS_TIMEOUT:-30s}"
mkdir -p -m 700 "$LOG_DIR" "$LOCK_DIR"
touch "$LOG"
chmod 600 "$LOG"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"; }

if [[ "$NOTIFY_MODE" != disabled && "$NOTIFY_MODE" != telegram ]]; then
    log "ERROR: unsupported notification mode: ${NOTIFY_MODE}"
    exit 2
fi
if [[ "$NOTIFY_MODE" == telegram && ( -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ) ]]; then
    log 'ERROR: Telegram credentials missing in external runtime config'
    exit 2
fi

tg_send() {
    local text="$1"
    [[ "$NOTIFY_MODE" == telegram ]] || return 0
    local token="${TELEGRAM_BOT_TOKEN:-}" chat_id="${TELEGRAM_CHAT_ID:-}"
    if [[ -z "$token" || -z "$chat_id" ]]; then
        log 'ERROR: Telegram credentials missing in external runtime config'
        return 1
    fi
    if ! curl -fsS -m 10 -X POST "https://api.telegram.org/bot${token}/sendMessage" \
        -d "chat_id=${chat_id}" --data-urlencode "text=${text}" >/dev/null \
    ; then
        log 'ERROR: Telegram request failed'
        return 1
    fi
}

alert() {
    local message="$1"
    log "🚨 告警: ${message}"
    tg_send "⚠️ a-stock-agent 告警：${message}"
}

exec 9>>"$LOCK_FILE"
flock -n 9 || { alert 'another instance仍在运行，本次跳过' || true; exit 1; }

log '=== 持仓止损检查开始 ==='
status=0
if ! result=$(timeout -k 10s "$TIMEOUT" a-stock-cache check-holdings 2>>"$LOG"); then
    alert '持仓止损检查命令失败（check-holdings exit 非0，详见日志）' || true
    status=1
else
    if grep -qE '🔴|⚠️' <<<"$result"; then
        log '持仓止损检查：触发预警'
        tg_send "🚨 持仓止损预警\n\n${result}" || status=1
    else
        log '持仓止损检查：无预警'
    fi
fi
log '=== 持仓止损检查完成 ==='
exit "$status"
