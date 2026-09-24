# cascabel_telemetry.db history purge

## Status (verified 2026-09-24)

- **Working tree / tip (`master`)**: clean — file removed in PR #6 (`c9dae88`); `.gitignore` lists `cascabel_telemetry.db`.
- **Git history**: blobs still reachable (`git rev-list --objects --all` showed `cascabel_telemetry.db`, ~61MB and ~37MB variants) until this branch is rewritten.

## This branch

Branch `chore/purge-telemetry-db-history` hardens `.gitignore` and includes a **workflow_dispatch-only** workflow that runs `git filter-repo --path cascabel_telemetry.db --invert-paths` and **force-pushes this branch only** (never `master`).

## After CI is green — what Guillermo must do

A normal merge of this PR into `master` **will not** remove the blobs from `master` history (merge keeps old commits reachable).

To finish the purge after review:

1. Ensure this branch tip has rewritten history (run **Actions → Purge telemetry DB history → Run workflow** with ref `chore/purge-telemetry-db-history`, or rewrite locally with `git filter-repo`).
2. **Force-push `master`** to the purged tip (or replace the default branch), e.g.:
   ```bash
   git fetch origin
   git checkout master
   git reset --hard origin/chore/purge-telemetry-db-history
   git push --force-with-lease origin master
   ```
3. Re-fetch / reset any other long-lived branches that still contain the old objects; ask collaborators to re-clone.
4. Optionally delete `.github/workflows/purge-telemetry-history.yml` after the one-shot succeeds.

**Do not merge this PR with a merge commit if the goal is history purge** — replace `master` with the rewritten tip instead.
