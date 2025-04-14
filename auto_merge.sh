#!/usr/bin/env bash
set -xeuo pipefail

REPO="$1"
MERGE_TO="$2"
MERGE_FROM="$3"

pushd /tmp
rm -rf $(basename "$REPO")
git clone https://"$REPO"
pushd $(basename "$REPO")

echo "On branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Merging in $MERGE_FROM (no-ff, -X theirs, no-edit)…"
DATE=$(date +%m-%d-%Y)
git fetch origin --prune
git checkout release-"$MERGE_TO"
git reset --hard origin/release-"$MERGE_TO"
git checkout -b "$MERGE_TO"-sync-from-"$MERGE_FROM"-"$DATE"
git merge --no-ff -X theirs --no-edit origin/release-"$MERGE_FROM"

# in some cases (hopefully rarely if we only sync these branches with git merge) there may be some conflicts
# found in git merge. We are resolving those automatically with -X theirs in the git merge command, but there
# can still be some issues like duplicated lines, etc. Let's find these files and call them out more clearly
# in the merge commit message. If there is trouble in these files (or anywhere else) they can be fixed and
# added/amended to the merge commit.
conflicted_files=( $(git show --name-status HEAD | awk '/^MM/ {print $2}') )
file_list=$(printf '  - %s\n' "${conflicted_files[@]}")
git commit --amend --no-edit -m "$(git log -1 --pretty=%B)

Auto‑merged files in this merge that may need inspection:
${file_list}"

popd

echo "Done."