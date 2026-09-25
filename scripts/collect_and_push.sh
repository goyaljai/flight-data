#!/bin/sh
set -eu

PROJECT=/opt/jai-dontdelete
ENV_FILE=/etc/jai-dontdelete/collector.env
GIT_CONFIG=/root/.ssh/config.jai-dontdelete
LOG_DIR="$PROJECT/logs"
LABEL=${1:?snapshot label required}

umask 077
set -a
. "$ENV_FILE"
set +a
cd "$PROJECT"
mkdir -p "$LOG_DIR"

status=0
if ! "$PROJECT/.venv/bin/python" -m collector --incremental --serpapi-label "$LABEL"; then
    status=1
fi

if git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$PROJECT" add collector README.md requirements.txt .gitignore .env.example data
    if ! git -C "$PROJECT" diff --cached --quiet; then
        git -C "$PROJECT" -c user.name="jai-dontdelete-vm" -c user.email="jai-dontdelete-vm@users.noreply.github.com" commit -m "Update daily context data" || status=1
        if ! GIT_SSH_COMMAND="ssh -F $GIT_CONFIG" git -C "$PROJECT" push origin main; then
            status=1
        fi
    fi
fi

exit "$status"
