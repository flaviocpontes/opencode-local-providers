## 1. Rename to occfg

- [x] 1.1 Update `pyproject.toml`: `name = "occfg"`, `[project.scripts] occfg = "opencode_config.cli.main:main"`, add `--cov-report=xml` to pytest addopts
- [x] 1.2 Sweep docs (AGENTS.md, PRD.md, README if present) replacing `occ` CLI invocations with `occfg` (`uv run occfg …`)
- [x] 1.3 Update any tests referencing the `occ` script name; run `uv run pytest` and `uv run ruff check` to verify green

## 2. CI workflow

- [x] 2.1 Create `.github/workflows/ci.yml` with jobs: lint (ruff), test (pytest), semgrep (`p/python --error`), sonar (scanner + `sonar.qualitygate.wait=true`), publish (`uv build` + `uv publish`)
- [x] 2.2 Gate semgrep, sonar, and publish on `env.GITHUB_SERVER_URL == 'https://gitea.gatospingados.net'`; gate publish additionally on tag `v*` with `needs: [lint, test, semgrep, sonar]`
- [x] 2.3 Verify workflow syntax locally (actionlint if available, else YAML parse)
- [x] 2.4 Rework publish job: GitHub-only gate (`github.server_url == 'https://github.com'`), `needs: [lint, test]`, OIDC (drop `UV_PUBLISH_TOKEN`, add `id-token: write`), semver guard `tag == v{pyproject.toml version}` before `uv build`

## 3. Gitea configuration (manual, outside repo)

- [x] 3.1 Configure PyPI trusted publisher for project `occfg`: publisher `flaviocpontes/opencode-local-providers`, workflow `ci.yml` (account + 2FA first)
- [x] 3.2 Add Gitea secret `SONAR_TOKEN` and variable `SONAR_HOST_URL` (token from LAN SonarQube, project key `opencode_config`)
- [ ] 3.3 Configure Gitea push mirror to `git@github.com:flaviocpontes/opencode-local-providers.git`

## 4. Verify before first publish

- [x] 4.1 Push to Gitea; confirm pipeline runs exactly once, lint+test green, semgrep+sonar execute
- [ ] 4.2 Confirm mirror triggered GitHub Actions: lint+test ran, semgrep/sonar skipped; publish skipped on branch pushes on both instances
- [x] 4.3 Confirm SonarQube project auto-created with coverage data and quality gate result wired to pipeline status

## 5. First release

- [ ] 5.1 Bump version in `pyproject.toml` to release version, push, wait for green pipeline
- [ ] 5.2 Tag `v<version>` and push tag to Gitea; confirm mirror syncs it and the GitHub publish job uploads to PyPI
- [ ] 5.3 On a clean machine: `uvx occfg --version` runs without `--from`; `uv tool install occfg` puts `occfg` on PATH
