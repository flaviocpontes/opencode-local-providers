## MODIFIED Requirements

### Requirement: Config errors fail fast without writing files

When the server registry or target `opencode.json` is unparseable JSON or lacks a required field, the tool SHALL print a single-line error naming the offending file and the cause, SHALL NOT write or create any output file, and SHALL exit with code 2. No Python traceback SHALL be shown.

#### Scenario: Registry with invalid JSON
- **WHEN** the server registry file contains invalid JSON and any `occ` subcommand other than `server add` runs
- **THEN** a single-line message names the registry path and the parse error
- **AND** the exit code is 2 and no traceback is printed

#### Scenario: Registry entry missing host
- **WHEN** a registry entry lacks the `host` field
- **THEN** the error message names the registry path and the offending entry
- **AND** the exit code is 2

#### Scenario: Target opencode.json is invalid JSON
- **WHEN** the target `opencode.json` exists but is not parseable JSON
- **THEN** a single-line message names the file path and states nothing was written
- **AND** the exit code is 2 and the file content is unchanged

## ADDED Requirements

### Requirement: Lifecycle command failures report single-line errors

`occ server remove|enable|disable <id>` with an id not present in the registry SHALL print a single-line error naming the id and exit 1, without writing any file. `occ server add` on an unreachable or erroring server follows the same contract (single-line `✗`, exit 1, nothing written).

#### Scenario: Unknown id
- **WHEN** `occ server disable ghost` runs and no entry with id `ghost` exists
- **THEN** a single-line error names the id `ghost`
- **AND** the exit code is 1 and neither file is written
