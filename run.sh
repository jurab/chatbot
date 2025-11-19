#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_NAME="chatbot"

if [ ! -d "${REPO_DIR}" ]; then
    echo "repo dir not found at ${REPO_DIR}, bruh."
    exit 1
fi

if [ ! -d "${REPO_DIR}/.venv" ]; then
    echo "no venv found in ${REPO_DIR}/.venv, fakt smůla."
    exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux not installed. icannothelp."
    exit 1
fi

# kill old session if present
tmux has-session -t "${SESSION_NAME}" 2>/dev/null && tmux kill-session -t "${SESSION_NAME}"

PROJECT_CMD="cd ${REPO_DIR} && source .venv/bin/activate"

# start session w/ frontend
tmux new-session -d -s "${SESSION_NAME}" \
    "${PROJECT_CMD} && python -m http.server 5500"

# split horizontally for backend
tmux split-window -h -t "${SESSION_NAME}" \
    "${PROJECT_CMD} && uvicorn main:app --reload"

tmux select-layout tiled >/dev/null 2>&1 || true

tmux attach -t "${SESSION_NAME}"
