## Context

Repo pushes to two remotes: `local` (gitea.gatospingados.net — primary, private, sandboxed act_runner with internet egress) and `backup` (github.com — backup). Commits and tags are pushed to both remotes explicitly from the dev machine; no Gitea mirror functionality is used. Gitea Actions reads the same workflow syntax as GitHub Actions and scans both `.gitea/workflows/` and `.github/workflows/`; a file in both directories would double-run on Gitea. PyPI OIDC trusted publishing supports GitHub/GitLab but not Gitea, so publication runs on GitHub only. `occ` and `opencode-config` are taken on PyPI; `occfg` is free. A SonarQube instance runs on the LAN (Community Build assumed — no PR decoration, branch analysis limited).

## Goals / Non-Goals

**Goals:**
- One workflow file drives both platforms; platform-specific jobs self-disable elsewhere (semgrep/sonar on Gitea only, publish on GitHub only)
- Publishing happens only from GitHub tags; Gitea never touches PyPI
- `uvx occfg` works bare on a clean machine
- Quality gate (SonarQube) blocks the Gitea pipeline on failure
- Releases follow semver with a tag↔version guard before upload

**Non-Goals:**
- Dynamic versioning from git tags (manual `pyproject.toml` bump + tag; solo repo)
- PR decoration in SonarQube (needs Developer Edition + ALM plugin for Gitea)
- Publishing artifacts to GitHub Releases, or dual-registry publishing (e.g. Gitea package registry)
- Python version matrix beyond a single modern runner Python plus the declared `>=3.10` floor enforced by pip at install time
- Release notes automation / changelog generation

## Decisions

### D1: One file at `.github/workflows/ci.yml`, URL-gated jobs
Jobs: `lint` → `test` → `semgrep` + `sonar` (parallel) → `publish` (needs: `[lint, test]`, tag-gated).

Gitea-only jobs (semgrep, sonar) carry `if: github.server_url == 'https://gitea.gatospingados.net'`; publish carries `if: startsWith(github.ref, 'refs/tags/v') && github.server_url == 'https://github.com'` — the `github` context is used because job-level `if` cannot access the `env` context on GitHub Actions. Publish cannot list semgrep/sonar in `needs`: on GitHub those jobs skip, and a skipped dependency would prevent publish from ever running. Consequence: quality gates do not hard-block releases; tag only after the Gitea pipeline is green (solo-repo discipline).
*Alternative rejected*: two files — double-runs on Gitea; *alternative rejected*: `secrets.SONAR_HOST_URL == ''` gating — misleading semantics, breaks if a mirror token ever lands on GitHub.

### D2: Rename dist and entry point to `occfg`; keep module `opencode_config`
`pyproject.toml`: `name = "occfg"`, `[project.scripts] occfg = "opencode_config.cli.main:main"`. Import layout, `python -m opencode_config`, and all src/tests paths unchanged — smallest possible rename surface. Rename happens *before* first publish so the PyPI name is claimed correctly once.
*Alternative rejected*: keep entry `occ` with dist `occfg` — forces `--from` on every uvx use; *alternative rejected*: renaming the Python package — large diff, no user-visible benefit.

### D3: Publish from GitHub via PyPI OIDC trusted publishing, with a semver tag↔version guard
Publisher: GitHub Actions on `flaviocpontes/opencode-local-providers`, workflow `ci.yml`, environment unset (no `environment: pypi` pin — can be added later for manual-approval releases). `uv publish` on a GitHub runner with `permissions: id-token: write` performs OIDC tokenless auth; no `UV_PUBLISH_TOKEN` secret exists anywhere. Tags reach GitHub via direct pushes to the `backup` remote. Before building, the publish job asserts the tag equals `v` + the `pyproject.toml` version (one shell comparison) — this enforces semver shape (`vMAJOR.MINOR.PATCH`) and fail-fast on drift; PyPI's duplicate-version rejection remains the backstop. The workflow trigger glob stays `v*` because glob filters cannot express semver; the guard provides exactness.
*Alternative rejected*: OIDC from Gitea — unsupported by PyPI; *alternative rejected*: API token on GitHub — standing credential, exists only to avoid a one-time PyPI publisher config; *alternative rejected*: Twine — extra dependency, uv already builds and publishes.

### D4: Semgrep OSS, no cloud account
`semgrep scan --config p/python --error` (rules fetched from registry at run time; runner has egress). No SARIF upload — Gitea code-scanning UI is not a thing and GitHub is the backup.

### D5: SonarQube via sonar-scanner-cli, gate enforced by wait
Analysis of `main` only (Community Build). `sonar.qualitygate.wait=true` fails the job on gate failure; coverage XML produced by pytest (`--cov-report=xml` added to addopts) and passed via `sonar.python.coverage.reportPaths`. Project pre-created on SonarQube with key `opencode_config` (the CI token is scoped to it). `SONAR_TOKEN` lives in Gitea secrets; `SONAR_HOST_URL` in Gitea variables (it's a non-sensitive URL; the workflow reads `vars.SONAR_HOST_URL` — the sonar job is Gitea-only, so no GitHub variable is needed).

### D6: GitHub backup via direct `backup` remote (no Gitea mirror)
The working repo carries a `backup` remote pointing at GitHub; commits and tags are pushed to both remotes explicitly. GitHub Actions triggers on those pushes, where the URL gates disable semgrep/sonar/publish.

## Risks / Trade-offs

- **`github.server_url` exact value**: act_runner derives it from the instance ROOT_URL; a trailing slash or different scheme would defeat the gate. Mitigation: first Gitea run verifies the condition; log/dump the context in a debug step if jobs mis-skip. Publish is additionally tag-gated, and PyPI rejects duplicate versions, so a mis-gate cannot silently double-publish the same file.
- **Quality gates don't hard-block publish**: skipped-`needs` mechanics force semgrep/sonar out of publish's dependencies, so a tag on a red Gitea pipeline still publishes after lint+test pass. Mitigation: tag only after Gitea is green; `environment: pypi` pin is the upgrade path.
- **Forgotten backup push means no release**: a semver tag pushed only to Gitea silently never publishes. Detectable: no GitHub Actions run for the tag. The Gitea-side gates still rely on act_runner's ROOT_URL matching `https://gitea.gatospingados.net` exactly; the GitHub-side publish gate compares against the constant `https://github.com`, which is stable.
- **Community SonarQube**: no PR decoration, branch-limited analysis — accepted (see Non-Goals).
- **Version discipline**: the guard fails fast on tag↔pyproject drift; residual ceiling is prerelease spelling (`1.2.3rc1` vs `1.2.3-rc.1` — PEP 440 vs semver differ; normalize or forgo prerelease tags if it bites). Upgrade path is `hatch-vcs`/`uv-dynamic-versioning` if manual bumps annoy.
