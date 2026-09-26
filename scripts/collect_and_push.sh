#!/bin/sh
set -eu

PROJECT=/opt/jai-dontdelete-git
RUNTIME=/var/lib/jai-dontdelete
ENV_FILE=/etc/jai-dontdelete/collector.env
GIT_CONFIG=/root/.ssh/config.jai-dontdelete
LOG_DIR="$PROJECT/logs"
LABEL=${1:?snapshot label required}

umask 077
set -a
. "$ENV_FILE"
set +a
mkdir -p "$LOG_DIR"
cd "$PROJECT"
export PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
export COLLECTOR_RUNTIME_ROOT="$RUNTIME"
mkdir -p "$RUNTIME/data" "$PROJECT/data" "$LOG_DIR"
if [ ! -f "$RUNTIME/.migrated" ]; then
    for month in "$PROJECT"/data/*/*; do
        [ -d "$month" ] || continue
        relative=${month#"$PROJECT/data/"}
        mkdir -p "$RUNTIME/data/$relative"
        for file in calendar.csv holidays.csv weather.csv weather_snapshots.csv; do
            if [ -f "$month/$file" ] && [ ! -f "$RUNTIME/data/$relative/$file" ]; then
                cp "$month/$file" "$RUNTIME/data/$relative/$file"
            fi
        done
    done
touch "$RUNTIME/.migrated"
fi
GIT_SSH_COMMAND="ssh -F $GIT_CONFIG" git -C "$PROJECT" pull --rebase --autostash origin main || printf '%s git sync before collection failed; continuing\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf '%s collector start label=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$LABEL"

status=0
if ! "$PROJECT/.venv/bin/python" -m collector --incremental --serpapi-label "$LABEL"; then
    status=1
fi

git -C "$PROJECT" add collector scripts/collect_and_push.sh README.md requirements.txt .gitignore .env.example
find "$PROJECT/data" -type f -name 'daily_context.csv' -print0 | xargs -0 -r git -C "$PROJECT" add
if ! git -C "$PROJECT" diff --cached --quiet; then
    git -C "$PROJECT" -c user.name="jai-dontdelete-vm" -c user.email="jai-dontdelete-vm@users.noreply.github.com" commit -m "Update daily context data" || status=1
    if ! GIT_SSH_COMMAND="ssh -F $GIT_CONFIG" git -C "$PROJECT" pull --rebase --autostash origin main; then
        status=1
    elif ! GIT_SSH_COMMAND="ssh -F $GIT_CONFIG" git -C "$PROJECT" push origin main; then
        status=1
    fi
fi

exit "$status"
