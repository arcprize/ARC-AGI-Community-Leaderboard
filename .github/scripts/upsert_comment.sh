#!/usr/bin/env bash
#
# Post or update a SINGLE marked advisory comment on a PR (never spams).
# Finds an existing comment containing the marker and edits it; otherwise creates one.
#
# Usage:
#   upsert_comment.sh <pr_number> <owner/repo> <body_file>
#
# Requirements:
#   - gh (GitHub CLI), authenticated with pull-requests:write (GH_TOKEN in CI)
#
set -euo pipefail

PR_NUMBER="${1:?usage: upsert_comment.sh <pr_number> <owner/repo> <body_file>}"
REPO="${2:?usage: upsert_comment.sh <pr_number> <owner/repo> <body_file>}"
BODY_FILE="${3:?usage: upsert_comment.sh <pr_number> <owner/repo> <body_file>}"

MARKER="<!-- arc-community-reviewer -->"

if [[ ! -s "$BODY_FILE" ]]; then
  echo "ERROR: comment body file is empty: $BODY_FILE" >&2
  exit 1
fi

# Ensure the marker is present so future runs can find and update this comment.
BODY_TMP="$(mktemp)"
if grep -qF "$MARKER" "$BODY_FILE"; then
  cp "$BODY_FILE" "$BODY_TMP"
else
  { printf '%s\n\n' "$MARKER"; cat "$BODY_FILE"; } > "$BODY_TMP"
fi

# Find an existing marked comment.
EXISTING_ID="$(gh api --paginate "repos/${REPO}/issues/${PR_NUMBER}/comments" \
  --jq ".[] | select(.body | contains(\"${MARKER}\")) | .id" | head -n1 || true)"

if [[ -n "${EXISTING_ID}" ]]; then
  gh api -X PATCH "repos/${REPO}/issues/comments/${EXISTING_ID}" \
    -F "body=@${BODY_TMP}" >/dev/null
  echo "Updated existing comment ${EXISTING_ID}"
else
  gh api -X POST "repos/${REPO}/issues/${PR_NUMBER}/comments" \
    -F "body=@${BODY_TMP}" >/dev/null
  echo "Created new comment"
fi
