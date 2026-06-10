#!/bin/sh
# Reads build.md + AGENT.md to build opencode.json with instructions[],
# then runs opencode with the named agent.
# Called by each agent's own entrypoint.sh after it has symlinked knowledge.
set -e

AGENT_DIR="${AGENT_DIR:-/agent}"
CONFIG_FILE="/workspace/opencode.json"
AGENT_NAME="${AGENT_NAME:-build}"

# ---------- helpers ----------
# Escape a string for JSON: backslash, double-quote, then collapse newlines to \n
json_escape() {
  printf '%s' "$1" \
    | sed 's/\\/\\\\/g' \
    | sed 's/"/\\"/g' \
    | awk '{printf "%s\\n", $0}' \
    | sed 's/\\n$//'
}

# ---------- Build opencode.json ----------
printf '{\n' > "$CONFIG_FILE"
printf '  "$schema": "https://opencode.ai/config.json",\n' >> "$CONFIG_FILE"
printf '  "model": "%s"' "${OPENCODE_MODEL:-google/gemma-4-31b-it}" >> "$CONFIG_FILE"

# Use same model for title generation to avoid burning quota on a separate small model
SMALL_MODEL="${OPENCODE_SMALL_MODEL:-${OPENCODE_MODEL:-google/gemma-4-31b-it}}"
printf ',\n  "small_model": "%s"' "$SMALL_MODEL" >> "$CONFIG_FILE"

# Optional temperature from OPENCODE_TEMPERATURE env var
if [ -n "${OPENCODE_TEMPERATURE:-}" ]; then
  printf ',\n  "temperature": %s' "$OPENCODE_TEMPERATURE" >> "$CONFIG_FILE"
fi

printf ',\n  "instructions": [\n' >> "$CONFIG_FILE"

NEED_COMMA=0

# 1. build.md body (strip YAML frontmatter between first two ---)
BUILD_MD="$AGENT_DIR/build.md"
if [ -f "$BUILD_MD" ]; then
  BODY=$(awk '/^---/{found++; next} found>=2{print}' "$BUILD_MD")
  ESCAPED=$(json_escape "$BODY")
  printf '    "%s"' "$ESCAPED" >> "$CONFIG_FILE"
  NEED_COMMA=1
fi

# 2. AGENT.md — plain bullet list of .md paths, one per line
#    Format:  - path/to/file.md   OR   - _shared/path.md (resolved from /opencode-knowledge)
AGENT_MD="$AGENT_DIR/AGENT.md"
if [ -f "$AGENT_MD" ]; then
  while IFS= read -r line; do
    # Strip leading whitespace and "- "
    STRIPPED=$(printf '%s' "$line" | sed 's/^[[:space:]]*//' | sed 's/^-[[:space:]]*//')
    # Must end in .md and not be a header or blank
    case "$STRIPPED" in
      \#*|'') continue ;;
      *.md) ;;
      *) continue ;;
    esac
    # Strip inline comment (everything after " —" or " -")
    FILE=$(printf '%s' "$STRIPPED" | sed 's/ —.*//' | sed 's/ -.*//' | sed 's/[[:space:]]*$//')
    [ -z "$FILE" ] && continue

    # Resolve path: _shared/ → /opencode-knowledge/_shared/, else → AGENT_DIR/
    case "$FILE" in
      _shared/*) FULL_PATH="/opencode-knowledge/$FILE" ;;
      *)         FULL_PATH="$AGENT_DIR/$FILE" ;;
    esac

    [ -f "$FULL_PATH" ] || continue

    CONTENT=$(cat "$FULL_PATH")
    ESCAPED=$(json_escape "$CONTENT")

    [ "$NEED_COMMA" = "1" ] && printf ',\n' >> "$CONFIG_FILE"
    printf '    "%s"' "$ESCAPED" >> "$CONFIG_FILE"
    NEED_COMMA=1
  done < "$AGENT_MD"
fi

printf '\n  ]\n}\n' >> "$CONFIG_FILE"

# ---------- Protect opencode.json from git ----------
GITIGNORE="/workspace/.gitignore"
if [ -f "$GITIGNORE" ]; then
  grep -qF "opencode.json" "$GITIGNORE" || printf '\nopencode.json\n' >> "$GITIGNORE"
else
  printf 'opencode.json\n' > "$GITIGNORE"
fi

# ---------- Run ----------
PROMPT="${PROMPT:-Read docs/requirement.md and begin your task.}"
exec opencode run --print-logs --agent "$AGENT_NAME" "$PROMPT"
