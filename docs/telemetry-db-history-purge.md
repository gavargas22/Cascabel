# cascabel_telemetry.db history purge

## Status (verified 2026-09-24 CT)

- **Working tree / tip (`master`)**: clean — file removed in PR #6; `.gitignore` lists `cascabel_telemetry.db` (hardened on this branch with `cascabel_telemetry.db*`, `*.sqlite`, `*.sqlite3`).
- **This branch history**: **purged**. `git filter-repo --path cascabel_telemetry.db --invert-paths` was applied via Actions and force-pushed to `chore/purge-telemetry-db-history`. Verified: `git rev-list --objects --all` has **no** `cascabel_telemetry.db`.
- **`master` history**: blobs **still reachable** (~61MB and ~37MB variants) until `master` is replaced with this tip.

## This branch contents

- Hardened `.gitignore` (prevents recommit of telemetry DB / sqlite sidecars).
- Docs note (this file).
- Optional one-shot workflow `.github/workflows/purge-telemetry-history.yml` (safe no-op when already clean).

## After CI is green — what Guillermo must do

A normal **merge** of this PR into `master` **will not** remove the blobs from `master` history (merge keeps old commits reachable).

To finish the purge after review (**force-push `master`**, do not merge-commit):

```bash
git fetch origin
git checkout master
git reset --hard origin/chore/purge-telemetry-db-history
git push --force-with-lease origin master
```

Then:

1. Reset or delete any other long-lived branches that still contain the old objects; ask collaborators to **re-clone** (or hard-reset).
2. Optionally delete `.github/workflows/purge-telemetry-history.yml` once `master` is purged.
3. Confirm: `git rev-list --objects --all | grep cascabel_telemetry` prints nothing on a fresh clone of `master`.

**Do not merge this PR with a merge commit if the goal is history purge** — replace `master` with the rewritten tip instead.
