#!/usr/bin/env bash
set -euo pipefail

step() { echo; echo "──────────────────────────────────────────"; echo "  $*"; echo "──────────────────────────────────────────"; }
ok()   { echo "[OK] $*"; }
fail() { echo "[FAIL] $*"; exit 1; }
run()  {
  local label="$1"; shift
  local out
  out=$("$@" 2>&1) && { echo "$out"; return 0; }
  local code=$?
  echo "$out"
  fail "$label (exit $code)"
}

# ── Validate required env vars ───────────────────────────────────────────────
: "${GIT_REPO_URL:?GIT_REPO_URL is required}"
: "${HOST_WORK_ROOT:?HOST_WORK_ROOT is required (absolute host path to work/ directory)}"

# ── Git identity ─────────────────────────────────────────────────────────────
git config --global user.name  "${GIT_USER_NAME:-planner-bot}"
git config --global user.email "${GIT_USER_EMAIL:-bot@example.com}"

# ── Step 1: Derive names ─────────────────────────────────────────────────────
step "Step 1/11 — Derive names"
ISSUE_KEY="${JIRA_ISSUE_KEY:?JIRA_ISSUE_KEY is required}"
SPEC_NAME="${ISSUE_KEY}.md"
BRANCH="plan/${ISSUE_KEY}-$(date +%s)"
# /repo is the isolated clone inside this container — never touches host project files
REPO_DIR="/repo"
WORKTREE_PATH="/work/${BRANCH}"
# Host path forwarded to docker run -v for sibling (planner) containers
HOST_WORKTREE_PATH="${HOST_WORK_ROOT}/${BRANCH}"
ok "Issue:           $ISSUE_KEY"
ok "Branch:          $BRANCH"
ok "Repo dir:        $REPO_DIR"
ok "Worktree (host): $HOST_WORKTREE_PATH"

# ── Step 2: Clone repo ───────────────────────────────────────────────────────
step "Step 2/11 — Clone repo"
# Embed token in URL for authenticated push
if [ -n "${GITHUB_TOKEN:-}" ]; then
  AUTHED_URL=$(echo "$GIT_REPO_URL" | sed "s|https://|https://${GITHUB_TOKEN}@|")
else
  AUTHED_URL="$GIT_REPO_URL"
fi
run "git clone" git clone --depth=1 --branch "${BASE_BRANCH:-main}" "$AUTHED_URL" "$REPO_DIR"
ok "Cloned to $REPO_DIR"

# ── Step 3: Create git worktree ──────────────────────────────────────────────
step "Step 3/11 — Create git worktree"
mkdir -p /work
run "git worktree add" git -C "$REPO_DIR" worktree add "$WORKTREE_PATH" -b "$BRANCH"
ok "Worktree created: $WORKTREE_PATH"

# ── Step 4: Fetch Jira ticket and write spec into worktree ───────────────────
step "Step 4/11 — Fetch Jira ticket: $ISSUE_KEY"
SPEC_FILE="$WORKTREE_PATH/app/docs/spec/${SPEC_NAME}"
mkdir -p "$WORKTREE_PATH/app/docs/spec"
mkdir -p "$WORKTREE_PATH/app/docs/plan"

JIRA_JSON=$(curl -s -f \
  -u "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Accept: application/json" \
  "${JIRA_BASE_URL}/rest/api/2/issue/${ISSUE_KEY}?fields=summary,description,subtasks,attachment") \
  || fail "Jira fetch failed for ${ISSUE_KEY}"

SUMMARY=$(echo "$JIRA_JSON"     | jq -r '.fields.summary')
DESCRIPTION=$(echo "$JIRA_JSON" | jq -r '.fields.description // "No description provided."')
SUBTASKS=$(echo "$JIRA_JSON"    | jq -r '.fields.subtasks[]?.fields.summary // empty' | sed 's/^/- /')
ATTACHMENTS=$(echo "$JIRA_JSON" | jq -r '.fields.attachment[]? | "- [\(.filename)](\(.content))"')

cat > "$SPEC_FILE" << SPECEOF
# ${ISSUE_KEY}: ${SUMMARY}

## Description

${DESCRIPTION}

## Subtasks

${SUBTASKS:-_No subtasks._}

## Attachments

${ATTACHMENTS:-_No attachments._}

---
_Source: ${JIRA_BASE_URL}/browse/${ISSUE_KEY}_
SPECEOF
ok "Spec written: $SPEC_FILE"

# ── Step 5: Write opencode.json into worktree ────────────────────────────────
step "Step 5/11 — Write opencode.json"
cat > "$WORKTREE_PATH/opencode.json" << 'JSONEOF'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "google": {
      "models": {
        "gemma-4-31b-it":     { "reasoning": false },
        "gemma-4-26b-a4b-it": { "reasoning": false }
      }
    }
  }
}
JSONEOF
echo "opencode.json" >> "$WORKTREE_PATH/.git/info/exclude" 2>/dev/null || true
ok "opencode.json written"

# ── Step 6: Run planner sub-agent ────────────────────────────────────────────
step "Step 6/11 — Run planner agent"
docker run --rm \
  --network "${DOCKER_NETWORK:-opencode-agents_agents}" \
  --env GOOGLE_GENERATIVE_AI_API_KEY \
  -e PROMPT="Read the specification from app/docs/spec/${SPEC_NAME} and write an implementation plan to app/docs/plan/${SPEC_NAME}." \
  -v "${HOST_WORKTREE_PATH}:/workspace" \
  opencode-planner:latest \
  || fail "planner exited with error"

# ── Step 7: Verify plan file ──────────────────────────────────────────────────
step "Step 7/11 — Verify plan file"
PLAN_FILE="$WORKTREE_PATH/app/docs/plan/$SPEC_NAME"
[ -f "$PLAN_FILE" ] || fail "plan file not found at $PLAN_FILE"
ok "Plan file verified: $PLAN_FILE"

# ── Step 8: Commit spec and plan ─────────────────────────────────────────────
step "Step 8/11 — Commit spec and plan"
git -C "$WORKTREE_PATH" add "app/docs/spec/${SPEC_NAME}" "app/docs/plan/${SPEC_NAME}"
git -C "$WORKTREE_PATH" commit -m "plan(${ISSUE_KEY}): generate spec and implementation plan"
ok "Committed"

# ── Step 9: Push branch ───────────────────────────────────────────────────────
step "Step 9/11 — Push branch: $BRANCH"
run "git push" git -C "$WORKTREE_PATH" push origin "$BRANCH"
ok "Pushed"

# ── Step 10: Create GitHub PR ──────────────────────────────────────────────────
step "Step 10/11 — Create GitHub PR"
PR_ERROR=$(mktemp)
PR_URL=$(gh pr create \
  --title "plan(${ISSUE_KEY}): implementation plan" \
  --body "## ${ISSUE_KEY}

Auto-generated from Jira ticket [${ISSUE_KEY}](${JIRA_BASE_URL}/browse/${ISSUE_KEY}).

| File | Purpose |
|------|---------|
| \`app/docs/spec/${SPEC_NAME}\` | Spec fetched from Jira |
| \`app/docs/plan/${SPEC_NAME}\` | Implementation plan generated by planner agent |" \
  --base "${BASE_BRANCH:-main}" \
  --head "$BRANCH" \
  --repo "${GIT_REPO_URL}" 2>"$PR_ERROR") \
  || { echo "ERROR: $(cat "$PR_ERROR")"; rm -f "$PR_ERROR"; fail "PR creation failed"; }
rm -f "$PR_ERROR"
ok "PR created: $PR_URL"

# ── Step 11: Done ─────────────────────────────────────────────────────────────
step "Step 11/11 — Done"
echo
echo "ORCHESTRATION_COMPLETE"
