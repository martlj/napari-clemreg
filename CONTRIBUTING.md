# Contributing

## Branching strategy

This fork (`martlj/napari-clemreg`) is doing substantial modernisation work (see
[docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md))
while the upstream owner is away. To keep that work reviewable and `main` safe
to sync from upstream later, branches follow a simple structure:

- **`main`** — a clean mirror of upstream (`krentzd/napari-clemreg`). Nothing
  fork-specific is merged here. Keeping it untouched means `git fetch upstream
  && git merge upstream/main` stays a clean fast-forward whenever upstream
  moves, and it's what an eventual PR back to upstream would be based on.
- **`modernisation`** — the integration branch for this fork's own work.
  Everything from the plan lands here first, via per-issue branches (below),
  not by committing to it directly once an issue has its own branch.
- **One branch per issue or theme**, branched off `modernisation`, named
  `<issue-number>-<short-slug>` (e.g. `6-mobie-export`, `12-em-mask-sample-data`).
  Open a PR into `modernisation` when the work is ready, even if it's a
  self-review/self-merge — a real PR gives a diff boundary, a description, CI
  results, and a revert point that a growing pile of commits on one branch
  doesn't.

Rationale for the split: `modernisation` started as a single branch named for
one specific task (splitting out the `clemreg` core, §6) and accumulated
unrelated work instead — testing, packaging, CI, bug fixes, docs. The name no
longer matched the content, and there was no PR boundary to review any of it
in reviewable chunks. Renamed and restructured 2026-09-22.

### Workflow

1. Pick up a GitHub issue.
2. `git checkout modernisation && git pull`
3. `git checkout -b <issue-number>-<short-slug>`
4. Do the work, commit (see commit message convention below), push.
5. Open a PR into `modernisation`. Merge once CI is green.
6. Delete the branch after merging.

When `modernisation` itself is ready to go back upstream (or once the
upstream owner is back to review), it becomes a single PR from
`modernisation` into `krentzd/napari-clemreg`'s `main` — see
[docs/napari-clemreg-modernisation-plan.md §7](docs/napari-clemreg-modernisation-plan.md#7-repository--release-strategy)
for the full repository/release plan.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/) —
`type(scope): short imperative description`, types: `feat`, `fix`, `docs`,
`style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

## Before merging a branch into `modernisation`

- Run the test suite (`tox`, or `pytest` against an active env — see
  [CLAUDE.md](CLAUDE.md) for which local env to use and why).
- Check CI is green.
- Update the relevant GitHub issue (and
  [docs/napari-clemreg-modernisation-plan.md](docs/napari-clemreg-modernisation-plan.md)
  if the change affects the plan) rather than letting them drift out of sync
  with what actually landed.
