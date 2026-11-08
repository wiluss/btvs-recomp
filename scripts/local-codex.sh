#!/bin/sh
set -eu
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 MODEL_ID [CODEX_ARGS...] (exact ID exposed by LM Studio)" >&2
    exit 2
fi
MODEL_ID=$1
shift
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if command -v codex >/dev/null 2>&1; then
    CODEX_BIN=$(command -v codex)
elif [ -x '/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex' ]; then
    CODEX_BIN='/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
else
    echo "Codex CLI was not found. See docs/IA-LOCALE.md." >&2
    exit 1
fi
exec "$CODEX_BIN" --oss --local-provider lmstudio -m "$MODEL_ID" --sandbox read-only -C "$PROJECT_ROOT" "$@"
