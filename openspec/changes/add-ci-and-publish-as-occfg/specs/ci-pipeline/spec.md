## Purpose

Defines the continuous-integration behavior for pushes and tags: which quality jobs run, on which platform they run, and how the primary Gitea instance and the GitHub mirror — which owns release publication — divide responsibilities without duplicating side effects.

## ADDED Requirements

### Requirement: Lint and test on every push
The CI pipeline SHALL run ruff lint checks and the pytest suite (with coverage collected) on every push and pull request, on both the primary Gitea instance and the GitHub mirror.

#### Scenario: Push to main on Gitea
- **WHEN** a commit is pushed to a branch on the primary Gitea instance
- **THEN** lint and test jobs execute and the commit status reflects their result

#### Scenario: Mirror synchronizes to GitHub
- **WHEN** the Gitea push mirror synchronizes a commit to GitHub
- **THEN** GitHub Actions runs lint and test jobs only

### Requirement: Security and quality analysis only on the primary instance
Semgrep static analysis and SonarQube scanning (with quality-gate enforcement) SHALL execute only on the primary Gitea instance and SHALL be skipped on the GitHub mirror.

#### Scenario: Push on the GitHub mirror
- **WHEN** the mirrored repository triggers CI on GitHub
- **THEN** semgrep and sonar jobs are skipped without failing the pipeline

#### Scenario: SonarQube quality gate fails
- **WHEN** the SonarQube quality gate is not passed on the primary instance
- **THEN** the CI pipeline fails for that commit

### Requirement: Test coverage report artifact
The test job SHALL produce a coverage XML report consumable by SonarQube.

#### Scenario: Test job completes
- **WHEN** the pytest job finishes successfully
- **THEN** a coverage XML file exists for the SonarQube scan

### Requirement: Single shared workflow definition
Both platforms SHALL consume one workflow file; the repository MUST NOT contain duplicate or platform-specific workflow copies that would cause double execution on the primary instance.

#### Scenario: Push on the primary Gitea instance
- **WHEN** CI is triggered on Gitea
- **THEN** the pipeline runs exactly once per event
