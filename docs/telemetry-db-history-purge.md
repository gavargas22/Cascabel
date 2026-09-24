# cascabel_telemetry.db history purge

## Status (verified 2026-09-24 CT)

- **Working tree / tip (`master`)**: clean — file removed in PR #6; `.gitignore` lists `cascabel_telemetry.db`.
- **`.gitignore` on this PR**: hardened with `cascabel_telemetry.db*`, `*.sqlite`, `*.sqlite3` (no tracked DB fixtures).
- **History on `master`**: blobs still reachable (~61MB and ~37MB) until `master` is replaced.
- **Purged ref (ready to force-push)**: branch `chore/purge-telemetry-db-history` @ `120b044311cf5b041835b3fd8f0fd86ddc878ce7` — history rewritten with `git filter-repo --path cascabel_telemetry.db --invert-paths`; verified no `cascabel_telemetry.db` objects on that branch.

GitHub cannot open a normal PR from the rewritten branch into `master` (unrelated histories after rewrite). This PR carries the safe tip-level changes; finishing the purge is a **force-push of `master`** to the purged tip (see below).

## Exact next step for Guillermo (after review / CI green)

Do **not** merge-commit if the goal is history purge. Instead:

```bash
git fetch origin
git checkout master
git reset --hard origin/chore/purge-telemetry-db-history
# tip should be 120b044311cf5b041835b3fd8f0fd86ddc878ce7 (or newer docs-only commits on that branch)
git push --force-with-lease origin master
```

Then reset/delete other long-lived branches that still contain the old objects; ask collaborators to re-clone. Optionally delete `.github/workflows/purge-telemetry-history.yml` from the purged tip after `master` is updated.

Confirm on a fresh clone of `master`:

```bash
git rev-list --objects --all | grep cascabel_telemetry || echo CLEAN
```
