## Purpose

Manages the lifecycle of local inference servers (add, remove, enable, disable, list) from the CLI, keeping the server registry and `opencode.json` consistent after every command, with immutable server identities and reachability probing at add time.

## ADDED Requirements

### Requirement: Server add probes the server before registering it

`occ server add <host>` SHALL connect to the server's type-specific models endpoint (Lemonade `/api/v1/models`, Ollama `/v1/models`) before writing anything. If the server is unreachable, returns an HTTP error, or returns a non-JSON response, the command SHALL print a single-line `✗` message naming the host and the failure reason, write neither the registry nor `opencode.json`, and exit 1. If the probe succeeds, the command SHALL add the entry to the registry with `enabled: true` and immediately write the provider entry to `opencode.json` using the models just fetched.

#### Scenario: Add reachable server
- **WHEN** `occ server add 192.168.0.20 --name "Lemonade Desktop"` runs and the server responds to the models endpoint
- **THEN** the registry contains the new entry with `enabled: true`
- **AND** `opencode.json` contains the provider entry with the server's chat models

#### Scenario: Add unreachable server
- **WHEN** `occ server add 10.0.0.99` runs and the connection is refused or times out
- **THEN** a single-line `✗` message names the host and reason
- **AND** the registry file is unchanged and `opencode.json` is unchanged
- **AND** the exit code is 1

#### Scenario: Add with type and port options
- **WHEN** `occ server add 192.168.0.30 --type ollama` runs and the server responds on port 11434
- **THEN** the probe targets `http://192.168.0.30:11434/v1/models` and the entry is registered with type `ollama` and port 11434

### Requirement: Server ids are minted at add time and immutable

Each registry entry SHALL carry an `id`. The id SHALL be the slug of `--name` when provided, else the slug of the host; if the minted id collides with an existing entry, a `-2`, `-3`, … suffix SHALL be appended until unique. After minting, the id SHALL NOT change: later changes to `name` or `host` leave the id and the corresponding `opencode.json` provider key untouched. The id SHALL be accepted as the argument to `remove`, `enable`, and `disable`.

#### Scenario: Id from name
- **WHEN** a server is added with `--name "Lemonade Desktop"` and no entry with id `lemonade-desktop` exists
- **THEN** the entry id is `lemonade-desktop` and the provider key in `opencode.json` is `lemonade-desktop`

#### Scenario: Collision suffix
- **WHEN** a second server would mint the id `lemonade-desktop` and that id already exists
- **THEN** the new entry gets id `lemonade-desktop-2`

#### Scenario: Rename preserves identity
- **WHEN** a registry entry's `name` is edited by hand after registration
- **THEN** the entry `id` and its `opencode.json` provider key are unaffected by subsequent syncs

#### Scenario: Legacy registry without ids
- **WHEN** the registry contains entries without `id` (pre-existing file)
- **THEN** the tool derives each entry's id using the same derivation as today's provider keys (slug of `name`, else slug of `host`) and persists the ids on the next registry write
- **AND** existing `opencode.json` provider entries with those keys are treated as the same servers

### Requirement: Disabling a server hides it without deleting it

`occ server disable <id>` SHALL set `"enabled": false` on the registry entry and SHALL set `"disabled": true` on the corresponding `opencode.json` provider entry, keeping the provider entry's models intact. Disabled servers SHALL be skipped by sync (no fetch attempted) and SHALL appear in listings without being probed.

#### Scenario: Disable writes both flags
- **WHEN** `occ server disable lemonade-desktop` runs
- **THEN** the registry entry has `"enabled": false`
- **AND** the `lemonade-desktop` provider entry in `opencode.json` has `"disabled": true` and retains its `models`

#### Scenario: Sync skips disabled servers
- **WHEN** sync runs and the registry contains a disabled server
- **THEN** no connection is attempted to that server and its `opencode.json` entry is left as-is

#### Scenario: Disabling the last enabled server is allowed
- **WHEN** the registry has one enabled server and `occ server disable <its-id>` runs
- **THEN** the command succeeds (exit 0) and both files are updated

### Requirement: Enabling a server restores it

`occ server enable <id>` SHALL set `"enabled": true` on the registry entry and SHALL remove the `"disabled"` flag (set it false or delete the key) on the corresponding `opencode.json` provider entry. The provider's model list MAY be stale after enabling; a subsequent `occ sync` refreshes it.

#### Scenario: Enable flips both flags
- **WHEN** `occ server enable lemonade-desktop` runs on a disabled entry
- **THEN** the registry entry has `"enabled": true` and the provider entry is no longer disabled
- **AND** the models map is unchanged until the next sync

### Requirement: Removing a server cleans up both files

`occ server remove <id>` SHALL delete the registry entry and SHALL delete the corresponding provider entry from `opencode.json`, in the same command invocation. If the provider entry does not exist in `opencode.json`, the command SHALL still remove the registry entry and succeed.

#### Scenario: Remove deletes entry and provider
- **WHEN** `occ server remove lemonade-desktop` runs on a registered server
- **THEN** the registry no longer contains the entry
- **AND** `opencode.json` no longer contains the `lemonade-desktop` provider key

#### Scenario: Remove tolerates missing provider entry
- **WHEN** `occ server remove <id>` runs and the registry has the entry but `opencode.json` has no provider with that key
- **THEN** the registry entry is removed and the command exits 0

### Requirement: Server list shows state and live model counts

`occ server list` SHALL print one block per registry entry: id, display name, host:port, type, and enabled/disabled state. Enabled servers SHALL be probed live, showing the count (or a `✗` failure line with reason) of downloadable chat models. Disabled servers SHALL be listed without probing. The exit code SHALL be 1 if any probed server failed, else 0.

#### Scenario: Mixed registry listing
- **WHEN** `occ server list` runs with one enabled reachable server and one disabled server
- **THEN** the enabled server shows its model count and the disabled server is marked disabled without any connection attempt

#### Scenario: Enabled server down during listing
- **WHEN** `occ server list` runs and an enabled server is unreachable
- **THEN** its block shows a `✗` line with the failure reason and the exit code is 1

### Requirement: Sync with no enabled servers is a successful no-op

When the registry parses but contains zero enabled servers, `occ sync` SHALL print a message stating there is nothing to do, SHALL NOT write `opencode.json`, and SHALL exit 0.

#### Scenario: All servers disabled
- **WHEN** `occ sync` runs and every registry entry is disabled
- **THEN** a nothing-to-do message is printed, no file is written, and the exit code is 0

### Requirement: Registry and opencode config live in the opencode config directory

The default registry path SHALL be `~/.config/opencode/local-inference-servers.json` and the default `opencode.json` path SHALL be `./opencode.json` when present in the working directory, else `~/.config/opencode/opencode.json`. Explicit path overrides SHALL remain available as global options.

#### Scenario: Default paths
- **WHEN** any `occ` command runs without path overrides and no `opencode.json` exists in the working directory
- **THEN** the registry is read from `~/.config/opencode/local-inference-servers.json` and `opencode.json` is read/written at `~/.config/opencode/opencode.json`
