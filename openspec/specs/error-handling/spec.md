# error-handling Specification

## Purpose

Defines how the tool reports and recovers from failures: friendly one-line messages instead of tracebacks, fail-fast on malformed user files, per-server fail-soft sync and listing, and a stable exit-code contract (0/1/2).

## Requirements

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

### Requirement: Lifecycle command failures report single-line errors

`occ server remove|enable|disable <id>` with an id not present in the registry SHALL print a single-line error naming the id and exit 1, without writing any file. `occ server add` on an unreachable or erroring server follows the same contract (single-line `✗`, exit 1, nothing written).

#### Scenario: Unknown id
- **WHEN** `occ server disable ghost` runs and no entry with id `ghost` exists
- **THEN** a single-line error names the id `ghost`
- **AND** the exit code is 1 and neither file is written

### Requirement: Unreachable or erroring servers are skipped without aborting sync

When a server cannot be reached (connection refused, timeout), returns an HTTP error status, or returns a non-JSON response, sync SHALL skip that server, print a `✗` line naming the server and the failure reason including that its provider entry was left unchanged, continue processing remaining servers, and exit with code 1 (if any server failed) or 0 (if all succeeded). A connect timeout SHALL be enforced at 5 seconds so an unresponsive host fails in seconds.

#### Scenario: One dead server among several
- **WHEN** server A refuses connections and server B responds normally, and sync runs
- **THEN** a `✗` line for A naming the connection failure is printed
- **AND** B's providers are written to `opencode.json`
- **AND** A's pre-existing provider entry in `opencode.json`, if any, is unchanged
- **AND** the exit code is 1

#### Scenario: HTTP error from server
- **WHEN** a server answers with HTTP 500
- **THEN** a `✗` line names the server and the HTTP status
- **AND** remaining servers are still processed and the exit code is 1

#### Scenario: Connect timeout
- **WHEN** a server host accepts no TCP connection within 5 seconds
- **THEN** the tool reports that server as failed within a few seconds (not hanging for the full read timeout)
- **AND** remaining servers are still processed

#### Scenario: All servers healthy
- **WHEN** every enabled server responds normally
- **THEN** no `✗` lines are printed and the exit code is 0

### Requirement: Server listing degrades per server

`-l`/`--list-servers` SHALL apply the same per-server fail-soft behavior: an unreachable or erroring server appears as a `✗` status row naming the server and failure reason, while reachable servers are listed normally. The exit code SHALL be 1 if any server failed, 0 otherwise.

#### Scenario: Listing with one dead server
- **WHEN** `-l` runs and server A is unreachable while server B responds
- **THEN** output contains a `✗` row for A with the failure reason and a normal listing for B
- **AND** the exit code is 1

### Requirement: No-args invocation prints usage

When invoked with no arguments, the tool SHALL print usage instructions to stdout and exit with code 0.

#### Scenario: Bare invocation
- **WHEN** the tool runs with no arguments
- **THEN** usage instructions are printed and the exit code is 0

### Requirement: Partial failure preserves existing provider entries

When a server is skipped due to failure, its existing provider entry in `opencode.json` SHALL be left byte-identical (not removed, not replaced), and other servers' entries SHALL still be updated. The skip message SHALL state that the entry was left unchanged.

#### Scenario: Stale entry preserved
- **WHEN** sync previously wrote an entry for server A and A fails on a later run
- **THEN** A's provider entry in `opencode.json` is unchanged by this run
- **AND** the `✗` message for A mentions the entry was left unchanged

### Requirement: Unknown server type is a config error

When a registry entry declares a `type` value other than `lemonade` or `ollama`, the tool SHALL treat it as a config error: a single-line message naming the registry path and the offending entry, no output file written, exit code 2.

#### Scenario: Registry entry with unknown type
- **WHEN** a registry entry declares `"type": "vllm"` and any mode other than `--init-servers` runs
- **THEN** a single-line error names the registry path and the entry
- **AND** the exit code is 2 and no output file is written
