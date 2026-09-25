#!/bin/sh
set -eu

PROJECT=/opt/jai-dontdelete-git
ENV_FILE=/etc/jai-dontdelete/collector.env
GIT_CONFIG=/root/.ssh/config.jai-dontdelete
LOG_DIR="$PROJECT/logs"
LABEL=${1:?snapshot label required}

umask 077
set -a
. "$ENV_FILE"
set +a
mkdir -p "$LOG_DIR"

status=0
if ! "$PROJECT/.venv/bin/python" -m collector --incremental --serpapi-label "$LABEL"; then
    status=1
fi

git -C "$PROJECT" add collector scripts README.md requirements.txt .gitignore .env.example data
if ! git -C "$PROJECT" diff --cached --quiet; then
    git -C "$PROJECT" -c user.name="jai-dontdelete-vm" -c user.email="jai-dontdelete-vm@users.noreply.github.com" commit -m "Update daily context data" || status=1
    if ! GIT_SSH_COMMAND="ssh -F $GIT_CONFIG" git -C "$PROJECT" pull --rebase origin main; then
        status=1
    elif ! GIT_SSH_COMMAND="ssh -F $GIT_CONFIG" git -C "$PROJECT" push origin main; then
        status=1
    fi
fi

exit "$status"
