# pypi-publish Specification

## Purpose

Defines the release behavior: how tagged versions of the `occfg` distribution are published to PyPI from GitHub Actions on `flaviocpontes/opencode-local-providers` (triggered by semver tags pushed to the GitHub backup remote), and the end-user installation contract the published package must satisfy.

## Requirements

### Requirement: Distribution is named occfg with a matching entry point
The published distribution SHALL be named `occfg` and SHALL provide a console script named `occfg`. The distribution name and entry point MUST match so the tool can be executed without a `--from` qualifier.

#### Scenario: Ad-hoc execution on a clean machine
- **WHEN** a user runs `uvx occfg --version` on a machine with uv installed
- **THEN** the command executes without requiring `--from` or any other qualifier

#### Scenario: Persistent install
- **WHEN** a user runs `uv tool install occfg`
- **THEN** the `occfg` command is available on PATH

### Requirement: Publishing is triggered only by semver tags on GitHub
The publish job SHALL execute only when a tag following semantic versioning (`vMAJOR.MINOR.PATCH`, optional prerelease suffix) is pushed to the GitHub repository, and SHALL never execute on the Gitea instance.

#### Scenario: Version tag pushed to GitHub
- **WHEN** a semver tag is pushed to the GitHub backup remote and lint and test jobs pass
- **THEN** the built distribution is uploaded to PyPI

#### Scenario: Tag present only on Gitea
- **WHEN** a version tag exists on the Gitea instance but was not pushed to GitHub
- **THEN** no publish attempt occurs on Gitea

#### Scenario: Regular push
- **WHEN** a commit (not a tag) is pushed to either repository
- **THEN** no publish attempt occurs

#### Scenario: Non-semver tag
- **WHEN** a tag not following `vMAJOR.MINOR.PATCH` (e.g. `vlatest`) is pushed
- **THEN** the publish job fails before any upload

### Requirement: Published version matches the tag
The publish job SHALL fail before any upload when the tag does not exactly equal the version declared in `pyproject.toml` prefixed with `v`, and every upload SHALL use a version not previously published to PyPI.

#### Scenario: Tag with stale version
- **WHEN** a tag `v0.2.0` is pushed while `pyproject.toml` declares `0.1.1`
- **THEN** the publish job fails before upload and nothing reaches PyPI

#### Scenario: Matching version
- **WHEN** the pushed tag equals `v` + the `pyproject.toml` version
- **THEN** the build and upload proceed

### Requirement: Module invocation remains available
The published package SHALL continue to support `python -m opencode_config` as an entry mechanism alongside the `occfg` script.

#### Scenario: Module invocation after rename
- **WHEN** the installed package is invoked via `python -m opencode_config`
- **THEN** the CLI behaves identically to the `occfg` script
