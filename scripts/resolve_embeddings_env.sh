#!/bin/sh

set -eu

trim() {
  # ponytail: minimal whitespace trim; upgrade path = stricter POSIX parser if needed
  printf "%s" "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# If only OPENAI_API_KEY is set, reuse it for decK.
if [ -z "${DECK_OPENAI_API_KEY:-}" ] && [ -n "${OPENAI_API_KEY:-}" ]; then
  export DECK_OPENAI_API_KEY="$OPENAI_API_KEY"
fi

LM_URL_RAW="$(trim "${DECK_LM_STUDIO_URL:-}")"

if [ -n "$LM_URL_RAW" ]; then
  LM_URL="${LM_URL_RAW%/}/v1/embeddings"
  # Kong runs in Docker; localhost/127.0.0.1 must resolve to the host.
  LM_URL="$(printf "%s" "$LM_URL" | sed 's#://localhost#://host.docker.internal#g; s#://127\\.0\\.0\\.1#://host.docker.internal#g')"

  export DECK_EMBEDDINGS_MODEL="${DECK_LM_STUDIO_MODEL:-text-embedding-mxbai-embed-large-v1}"
  export DECK_EMBEDDINGS_UPSTREAM_URL="$LM_URL"
  export DECK_EMBEDDINGS_API_KEY="${DECK_LM_STUDIO_API_KEY:-}"

  echo "[embeddings] using LM Studio: model=${DECK_EMBEDDINGS_MODEL} upstream_url=${DECK_EMBEDDINGS_UPSTREAM_URL}" >&2
else
  export DECK_EMBEDDINGS_MODEL="text-embedding-3-small"
  export DECK_EMBEDDINGS_UPSTREAM_URL="https://api.openai.com/v1/embeddings"
  export DECK_EMBEDDINGS_API_KEY="${DECK_OPENAI_API_KEY:-}"

  echo "[embeddings] using OpenAI: model=${DECK_EMBEDDINGS_MODEL} upstream_url=${DECK_EMBEDDINGS_UPSTREAM_URL}" >&2
fi

