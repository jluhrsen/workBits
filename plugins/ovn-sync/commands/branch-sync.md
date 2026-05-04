---
description: Analyze automated branch sync status between release branches, identify pending commits, detect duplicates, and check for blockers
argument-hint: "[scope]"
---

## Name
ovn-sync:branch-sync

## Synopsis
```bash
/ovn-sync:branch-sync [scope]
```

## Description

Analyzes the status of automated branch syncing across OVN-Kubernetes downstream release branches. This command helps identify what's ready to merge, what's blocked, detects duplicate commits (already backported manually), and flags dependency issues or conflicts.

**Repository:** openshift/ovn-kubernetes (downstream)

**Branch Strategy:**
- **Bundle 1:** release-5.0 → release-4.22 → release-4.21 (all should be identical)
- **Bundle 2:** release-4.20 → release-4.19 → release-4.18 (all should be identical)
- **Upstream sync:** ovn-kubernetes/ovn-kubernetes master → openshift/ovn-kubernetes master → release-5.0, release-4.23 (mirrored)

**Automation:**
- Runs hourly via `/home/jamoluhrsen/repos/RedHat/openshift/release/ci-operator/step-registry/github/`
- Creates one PR per branch pair
- Uses specific title patterns for detection

## Implementation

### 1. Setup and Branch Pairs

Fetch all relevant branches and define sync pairs:

```bash
# Fetch branches
git fetch origin release-5.0 release-4.23 release-4.22 release-4.21 release-4.20 release-4.19 release-4.18

# Define sync pairs to check
BUNDLE_1_PAIRS=(
  "release-5.0:release-4.22"
  "release-4.22:release-4.21"
)

BUNDLE_2_PAIRS=(
  "release-4.20:release-4.19"
  "release-4.19:release-4.18"
)
```

### 2. For Each Sync Pair

Check the following for each pair:

#### A. Find Open Sync PR

**Branch sync title pattern:** `Branch Sync {SOURCE} to {TARGET} \[MM-DD-YYYY\]`
**Conflict title pattern:** `MERGE CONFLICT! Branch Sync {SOURCE} to {TARGET} \[MM-DD-YYYY\]`

```bash
# Extract source and target from pair
SOURCE="release-4.20"
TARGET="release-4.19"

# Search for open PR using title pattern
gh pr list --base "$TARGET" --state open \
  --json number,title,createdAt,updatedAt,isDraft \
  --jq ".[] | select(.title | test(\"Branch Sync ${SOURCE} to ${TARGET}\"))"
```

#### B. Find Last Successful Sync

```bash
# Get most recent merged sync PR
gh pr list --base "$TARGET" --state merged \
  --search "Branch Sync ${SOURCE} to ${TARGET}" \
  --json number,title,mergedAt --limit 1
```

#### C. Get New Commits Since Last Sync

```bash
# List commits in source not in target
git log origin/$TARGET..origin/$SOURCE --format="%H %s" --no-merges
```

**CRITICAL:** Count these carefully - this tells you what SHOULD be in the next sync.

#### D. Analyze Current Sync PR (if exists)

If an open sync PR exists:

```bash
# Get commits in the PR
gh pr view $PR_NUMBER --json commits \
  --jq '.commits[] | "\(.oid[0:9]) \(.messageHeadline)"'

# Check for duplicates by searching target branch by MESSAGE not SHA
for commit_msg in "${COMMIT_MESSAGES[@]}"; do
  git log origin/$TARGET --format="%H %s" --grep="$commit_msg" --fixed-strings
done
```

**Output:**
- How many commits in the PR
- How many are duplicates (already in target)
- Recommendation: close if all duplicates, otherwise ready to merge

#### E. Get Merged PRs to Source Branch Since Last Sync

```bash
# Find PRs merged to source branch after last sync date
gh pr list --base "$SOURCE" --state merged \
  --search "merged:>LAST_SYNC_DATE" \
  --json number,title,mergedAt --limit 20
```

#### F. Check Open PRs on Source Branch

These are potential future syncs. Look for:
- CI status (passing/failing)
- Labels (do-not-merge/hold, approved, lgtm)
- Human comments indicating blockers

```bash
gh pr list --base "$SOURCE" --state open \
  --json number,title,author,labels,statusCheckRollup \
  | jq -r '.[] | select((.title | test("DNM|TEST"; "i")) | not)'
```

For each open PR with interesting status, check comments:

```bash
gh pr view $PR_NUM --json comments \
  --jq '.comments[] | select(.author.login != "openshift-ci[bot]" and .author.login != "openshift-merge-bot[bot]") | select(.body | test("hold|wait|block|conflict|dependency"; "i")) | "[\(.createdAt | split("T")[0])] \(.author.login): \(.body)"' \
  | head -20
```

**Flag these issues:**
- `/hold` with reason
- Waiting for another PR (especially if that PR targets a DIFFERENT branch - that's backwards!)
- CI failures on required tests
- Missing labels (qe-approved, backport-risk-assessed, etc.)

### 3. Output Format

For each sync pair, produce a structured summary:

```markdown
## 📊 release-4.20 → release-4.19

### Current Sync PR: #3138
- **Status:** OUTDATED (all commits are duplicates)
- **Created:** 2026-04-15
- **Commits in PR:** 1
  - ✅ PR #3099 → Already in 4.19 as PR #3100 (ab20d0a28)
- **Recommendation:** ❌ Close and wait for automation

### New Commits Ready to Sync: 2
1. ✅ **PR #3152** (merged Apr 24) - virt: fix SyncVirtualMachines deleting UDN DHCP options
   - Commit: ef7ea17cd
   - NOT in release-4.19
2. ✅ **PR #3093** (merged Apr 23) - Fix NAD Controller syncAll for networkID upgrade
   - Commit: 8df3403fa
   - NOT in release-4.19

### Open PRs on release-4.20: 4
1. **PR #3102** - CUDN: cleanup NADs in terminating namespaces
   - ✅ All 30 CI checks passing
   - ⏸️ **ON HOLD** - waiting for PR #3087 (targets 4.21!)
   - 🚨 **DEPENDENCY ISSUE:** Backwards dependency detected (4.20 waiting on 4.21)
   - Updated today: kyrtapz added `/verified` and `/label backport-risk-assessed`
   
2. **PR #3070** - kubevirt DHCP router option
   - ⚠️ 2 optional tests failing (non-required)
   - ✅ All required CI passing
   - Labels: approved, lgtm, qe-approved, backport-risk-assessed

3. **PR #2927** - Manual backport bug fixes
   - 🐛 jira/invalid-bug label
   - ✅ All CI passing
   - Comment: "Wait until 4.21 JIRAs are backported"

4. **PR #2919** - Remove forced V(5) logging
   - 🔄 needs-rebase
   - 🐛 jira/invalid-bug label

---
```

### 4. Special Case: Downstream Sync (Upstream Master → Downstream Master)

Check separately with different title pattern:

**Title pattern:** `DownStream Merge \[MM-DD-YYYY\]`
**Conflict patterns:** `CONFLICT!`, `GO MOD FAILED!`, `TEST ANNOTATIONS FAILED!`

```bash
gh pr list --base master --state open \
  --json number,title,isDraft,createdAt \
  --jq '.[] | select(.title | test("DownStream Merge"))'
```

### 5. Summary Recommendations

At the end, provide actionable recommendations:

```markdown
## 🎯 Action Items

### Immediate Actions:
- Close PR #3138 (4.20→4.19) - all commits are duplicates
- Investigate PR #3102 dependency issue - why is 4.20 waiting on 4.21?

### Ready to Merge (source branches):
- PR #3102 (4.20) - blocked by hold, otherwise ready
- PR #3070 (4.20) - ready except optional tests

### Waiting on Fixes:
- PR #2927 (4.20) - JIRA validation
- PR #2919 (4.20) - needs rebase

### Expected Next Syncs:
When automation runs next (hourly), expect new PRs:
- 4.20→4.19: Will include 2 commits (PR #3152, #3093)
- 4.19→4.18: Check status separately
```

## Key Logic Points

### Duplicate Detection

**CRITICAL:** Search by commit MESSAGE, not SHA!

```bash
# Wrong (will miss duplicates):
git log origin/release-4.19 --oneline | grep "2a5bf31ca"

# Correct (finds all copies):
SUBJECT="node: fix serviceUpdateNotNeeded nil pointer comparison"
git log origin/release-4.19 --format="%H %s" --grep="^${SUBJECT}$" --fixed-strings
```

Also check for manual backports via JIRA numbers:

```bash
# If source PR is OCPBUGS-81477, check target for same JIRA
gh pr list --base release-4.19 --state merged \
  --search "81477" --json number,title
```

### Dependency Issue Detection

If a PR comment says "wait for PR #XXXX":
1. Fetch that PR's base branch
2. Compare to current PR's base branch
3. **Flag if backwards** (e.g., 4.20 waiting on 4.21)

```bash
BLOCKING_PR=3087
BLOCKING_BASE=$(gh pr view $BLOCKING_PR --json baseRefName --jq .baseRefName)
CURRENT_BASE="release-4.20"

# Extract version numbers and compare
BLOCKING_VER=${BLOCKING_BASE#release-}
CURRENT_VER=${CURRENT_BASE#release-}

# If current version < blocking version, that's backwards!
if [[ "$CURRENT_VER" < "$BLOCKING_VER" ]]; then
  echo "🚨 BACKWARDS DEPENDENCY: $CURRENT_BASE waiting on $BLOCKING_BASE"
fi
```

### Conflict Detection

If sync PR title starts with "MERGE CONFLICT!", check for:
- Draft status
- `/hold` comment
- "needs conflict resolution" message

## What NOT to Check

- Don't read code diffs (too verbose)
- Don't check individual commit SHAs across branches (messages are canonical)
- Don't try to predict merge conflicts (automation handles that)
- Don't check upstream repo directly (only downstream matters here)

## Parallel Execution

When checking multiple sync pairs, you can:
1. Fetch all branches in one call
2. Run PR queries in parallel for different base branches
3. Process each pair independently

But OUTPUT should be structured by bundle and in order:
1. Downstream sync (upstream→master)
2. Bundle 1 (5.0→4.22, 4.22→4.21)
3. Bundle 2 (4.20→4.19, 4.19→4.18)

## Error Handling

- If no open sync PR exists and commits are pending, note "Automation will create PR next run"
- If a branch doesn't exist, skip that pair and note it
- If gh/git commands fail, show error but continue with other pairs

## Return Value

- **Claude agent text**: Structured markdown report including:
  - Status of each sync pair (current PR, pending commits, duplicates)
  - Analysis of open PRs on source branches (blockers, holds, dependencies)
  - Actionable recommendations
  - Detected issues (backwards dependencies, conflicts, duplicate commits)

## Examples

1. **Check all sync pairs** (default):
   ```
   /ovn-sync:branch-sync
   ```
   Analyzes downstream sync + Bundle 1 + Bundle 2

2. **Check specific bundle**:
   ```
   /ovn-sync:branch-sync bundle-2
   ```
   Only checks 4.20→4.19→4.18

3. **Check specific sync pair**:
   ```
   /ovn-sync:branch-sync 4.20:4.19
   ```
   Only checks that one pair

4. **Skip open PR analysis**:
   ```
   /ovn-sync:branch-sync --sync-only
   ```
   Only checks sync status, not future work

## Arguments

- **scope** (optional): Limit the analysis scope
  - `all` - Check all active sync pairs (default)
  - `bundle-1` - Only Bundle 1 (5.0→4.22→4.21)
  - `bundle-2` - Only Bundle 2 (4.20→4.19→4.18)
  - `{source}:{target}` - Specific pair (e.g., `4.20:4.19`)
  - `--sync-only` - Skip open PR analysis on source branches
