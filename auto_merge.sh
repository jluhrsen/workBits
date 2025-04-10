#!/usr/bin/env bash
set -xeuo pipefail

REPO="$1"
MERGE_TO="$2"
MERGE_FROM="$3"
ART_IMAGE_PATTERN='FROM .*registry'

pushd /tmp
#rm -rf $(basename "$REPO")
#git clone https://"$REPO"
pushd $(basename "$REPO")

echo "On branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Merging in $MERGE_FROM (no-ff, -X theirs, no-edit)…"
DATE=$(date +%m-%d-%Y)
git fetch origin --prune
git checkout release-"$MERGE_TO"
git reset --hard origin/release-"$MERGE_TO"
git checkout -b "$MERGE_TO"-sync-from-"$MERGE_FROM"-"$DATE"
git merge --no-ff -X theirs --no-edit origin/release-"$MERGE_FROM"

# Any file matching the ART_IMAGE_PATTERN may need to get reverted to what we have in MERGE_TO
# and not what was updated automatically by ART in the MERGE_FROM branch
readarray -t staged_files < <(
  git diff-tree --no-commit-id --name-only -r HEAD^1 HEAD \
    | xargs grep -lE "$ART_IMAGE_PATTERN" || true
)

if [ ${#staged_files[@]} -eq 0 ]; then
  echo "No merged files contain 'ART_IMAGE_PATTERN': ${ART_IMAGE_PATTERN}. Nothing to restore."
  popd > /dev/null
  exit 0
fi

echo "Files to restore:"
printf '  %s\n' "${staged_files[@]}"

for file in "${staged_files[@]}"; do
  echo
  echo "==== Restoring $file ===="

  # This magic finds the files that were actually updated with the merge process AND was specifically
  # updating the ART_IMAGE_PATTERN line. If so, it will revert those lines to what MERGE_TO previously
  # had
  mapfile -t originals < <(git show HEAD^1:"$file" | grep -E "$ART_IMAGE_PATTERN")

  idx=0
  {
    while IFS= read -r line; do
      if [[ $line =~ ^FROM\ .*registry ]]; then
        echo "${originals[idx++]}"
      else
        echo "$line"
      fi
    done
  } < "$file" > "$file.tmp"

  # Show what changed
  diff -u --label before/"$file" --label after/"$file" "$file" "$file.tmp" || true

  mv "$file.tmp" "$file"
done

git add -u

# in some cases (hopefully rarely if we only sync these branches with git merge) there may be some conflicts
# found in git merge. We are resolving those automatically with -X theirs in the git merge command, but there
# can still be some issues like duplicated lines, etc. Let's find these files and call them out more clearly
# in the merge commit message. If there is trouble in these files (or anywhere else) they can be fixed and
# added/amended to the merge commit.
conflicted_files=( $(git show --name-status HEAD | awk '/^MM/ {print $2}') )
file_list=$(printf '  - %s\n' "${conflicted_files[@]}")
git commit --amend --no-edit -m "$(git log -1 --pretty=%B)

Restored any pre-merge 'FROM registry' lines to avoid ART image-bumps made specifically for ${MERGE_FROM}

Auto‑merged files in this merge that may need inspection:
${file_list}"


popd

echo "Done."