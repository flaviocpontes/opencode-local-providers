# cli-flags Specification

## Purpose

Defines the semantics and validation of the command-line interface: mode exclusivity, non-destructive dry runs, model visibility filtering, and version reporting.

## Requirements

### Requirement: Dry run MUST NOT write the config file

When invoked with `-n`/`--dry-run`, the tool SHALL NOT modify the target `opencode.json`. It SHALL instead print the generated provider configuration to stdout, clearly labeled as a dry run, and exit successfully.

#### Scenario: Dry run leaves file untouched
- **WHEN** the tool runs with `--dry-run` against an existing `opencode.json`
- **THEN** the file content is byte-identical before and after the run
- **AND** stdout contains the generated provider configuration

#### Scenario: Dry run without existing file
- **WHEN** the tool runs with `--dry-run` and the target `opencode.json` does not exist
- **THEN** no file is created
- **AND** stdout contains the generated provider configuration

### Requirement: Non-downloaded models are excluded by default

By default, sync and server listing SHALL include only models marked as downloaded. When `--show-all` is passed, both SHALL include models regardless of download status.

#### Scenario: Default sync filters undownloaded models
- **WHEN** the server reports a chat model with `downloaded: false` and sync runs without `--show-all`
- **THEN** that model does not appear in the generated configuration

#### Scenario: Show-all includes undownloaded models
- **WHEN** the server reports a chat model with `downloaded: false` and the tool runs with `--show-all`
- **THEN** that model appears in the output (sync config or listing)

#### Scenario: Non-chat models stay excluded under show-all
- **WHEN** the server reports a model whose recipe or labels exclude it from chat (e.g. image, tts, embeddings, transcription)
- **THEN** it is excluded regardless of `--show-all`

### Requirement: Mode flags MUST be mutually exclusive

`--init-servers` and `-l`/`--list-servers` SHALL be mutually exclusive. Passing both SHALL cause argparse to exit with a usage error (exit code 2) rather than silently ignoring one of them.

#### Scenario: Conflicting modes rejected
- **WHEN** the tool is invoked with both `--init-servers` and `--list-servers`
- **THEN** it exits with a usage error and runs neither mode

### Requirement: Version flag reports package version

`--version` SHALL print the installed package version and exit 0, using the package metadata as the source of truth (with a static fallback when the package is not installed).

#### Scenario: Version from installed metadata
- **WHEN** the package is installed and the tool runs with `--version**
- **THEN** stdout shows the installed version string and the exit code is 0
