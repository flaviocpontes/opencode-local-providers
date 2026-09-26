## Why

The project must be published to PyPI so it can be run ad-hoc with `uvx occfg`, but the current name `opencode_config` is already taken on PyPI (v0.0.0a1) and the bare name `occ` is burned by an abandoned 2019 package. The repository also has no CI: lint, tests, semgrep, SonarQube analysis, and publishing must run automatically on the self-hosted Gitea instance (primary), with GitHub acting as a backup remote.

## What Changes

- **BREAKING**: Rename distribution to `occfg` and rename the console-script entry point from `occ` to `occfg` (both must match for bare `uvx occfg`). Import package `opencode_config` and all code layout stay unchanged; `python -m opencode_config` keeps working.
- Add one shared CI workflow (`.github/workflows/ci.yml`) consumed by both Gitea Actions (primary) and GitHub Actions (mirror): lint (ruff), test (pytest + coverage XML), semgrep (`p/python`), SonarQube scan with quality-gate wait, and tag-triggered publish.
- Gate semgrep and sonar jobs so they run only on the Gitea instance; gate the publish job so it runs only on GitHub — the mirror runs lint + test on every push and publishes on tags, Gitea never touches PyPI.
- Publish to PyPI from GitHub Actions on `flaviocpontes/opencode-local-providers` on `v*` tags via PyPI OIDC trusted publishing (tokenless; unsupported by Gitea): `uv build && uv publish`. Tags reach GitHub via direct pushes to the `backup` remote. The project follows semver: `vMAJOR.MINOR.PATCH` tags, guarded against tag↔version mismatch before upload.
- Add coverage XML reporting (`--cov-report=xml`) for SonarQube ingestion.
- Update docs (AGENTS.md, PRD.md, README references) to use `occfg`.
- Configure repo infrastructure outside the repo: Gitea secrets/variables (`SONAR_TOKEN` secret, `SONAR_HOST_URL` variable), PyPI trusted-publisher configuration. Documented in tasks as manual steps.

## Capabilities

### New Capabilities
- `ci-pipeline`: Continuous integration behavior — what runs where (Gitea vs GitHub mirror), quality gates, and the conditions under which jobs execute or skip.
- `pypi-publish`: Release behavior — tag-triggered, Gitea-only, versioned PyPI publication of the `occfg` distribution, plus the `occfg` entry point contract (`uvx occfg` must work on a clean machine).

### Modified Capabilities
<!-- None: no existing specs are modified. `openspec/specs/` has no specs yet. -->

## Impact

- `pyproject.toml`: project `name`, `[project.scripts]` entry, pytest addopts gain `--cov-report=xml`.
- Docs: AGENTS.md and PRD.md references to `occ` → `occfg` (CLI invocation becomes `uv run occfg …`).
- New file `.github/workflows/ci.yml`; no source-code changes under `src/`.
- External systems: Gitea (secrets/variables, runner), SonarQube LAN instance (pre-created project `opencode_config`), PyPI (account, token, eventual `occfg` project).
- Tests: any CLI-invocation tests referencing the `occ` script name must be updated.
