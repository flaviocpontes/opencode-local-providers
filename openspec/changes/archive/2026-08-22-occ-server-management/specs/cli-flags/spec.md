## MODIFIED Requirements

### Requirement: Dry run MUST NOT write the config file

When invoked with `-n`/`--dry-run` on the `occ sync` subcommand, the tool SHALL NOT modify the target `opencode.json`. It SHALL instead print the generated provider configuration to stdout, clearly labeled as a dry run, and exit successfully.

#### Scenario: Dry run leaves file untouched
- **WHEN** `occ sync --dry-run` runs against an existing `opencode.json`
- **THEN** the file content is byte-identical before and after the run
- **AND** stdout contains the generated provider configuration

#### Scenario: Dry run without existing file
- **WHEN** `occ sync --dry-run` runs and the target `opencode.json` does not exist
- **THEN** no file is created
- **AND** stdout contains the generated provider configuration

## ADDED Requirements

### Requirement: CLI exposes verb subcommands

The `occ` command SHALL expose the subcommands `server add`, `server remove`, `server enable`, `server disable`, `server list`, and `sync`. Running `occ` with no subcommand SHALL print usage and exit 0. An unknown subcommand SHALL produce an argparse usage error (exit 2). The executable SHALL be installable as `occ` via the package's console scripts entry point, and `python -m opencode_config` SHALL remain a working invocation.

#### Scenario: No subcommand prints usage
- **WHEN** `occ` runs with no arguments
- **THEN** usage instructions listing the subcommands are printed and the exit code is 0

#### Scenario: Unknown subcommand
- **WHEN** `occ frobnicate` runs
- **THEN** argparse exits with a usage error (exit code 2)

#### Scenario: Installed as occ
- **WHEN** the package is installed via pip/uv
- **THEN** the `occ` executable is available on PATH and behaves identically to `python -m opencode_config`

## REMOVED Requirements

### Requirement: Mode flags MUST be mutually exclusive

**Reason**: The mode flags `-l`/`--list-servers` and `--init-servers` are replaced by subcommands; mutual exclusion is enforced structurally by argparse subparsers.

**Migration**: Use `occ server list` instead of `-l`/`--list-servers`, and `occ server add <host>` instead of `--init-servers`.
