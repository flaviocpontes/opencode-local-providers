## Why

Every failure path in the tool today surfaces as a raw Python traceback (or, for an unreachable server, a 30-second hang followed by one). For a multi-server registry this is worst-case: one dead machine on the LAN aborts the entire sync, and a typo in the user's own `opencode.json` looks like a bug in the tool. The tool is at the point where non-expert users run it; error output is part of the interface.

## What Changes

- Introduce two error families with distinct behavior:
  - **Config errors** (registry or `opencode.json` unreadable/unparseable/invalid, no enabled servers): fail fast with a one-line message naming the file and cause. Exit code 2. No file is written.
  - **Runtime errors** (per-server: connection refused, timeout, HTTP 4xx/5xx, non-JSON response): skip that server, report it as a `✗` line, continue syncing the rest. Exit code 1 if any server failed, 0 otherwise.
- Translate transport/HTTP/JSON failures in `HttpLemonadeClient` into a domain error carrying the server label; adapters raise domain errors, use cases catch per-server, CLI renders.
- Set an explicit connect timeout (5s, read 30s) so a dead host fails in seconds, not 30s.
- Apply the same fail-soft behavior to `-l/--list-servers`: an unreachable server appears as a status row instead of aborting the listing.
- Stale-entry semantics on partial failure: a skipped server's existing provider entry in `opencode.json` is left unchanged, and the skip message says so.
- No-args invocation prints usage and exits 0 (already implemented; covered by spec for completeness).

## Capabilities

### New Capabilities

- `error-handling`: Classification of failure modes (config vs runtime), per-server fail-soft sync and listing, exit code contract (0/1/2), friendly one-line messages, connect timeout, and stale-entry preservation on partial failure.

### Modified Capabilities

(none — `cli-flags` flag semantics are unchanged)

## Impact

- `src/opencode_config/domain/ports.py` — add `ConfigError`, `LemonadeError` exception classes.
- `src/opencode_config/adapters/lemonade_client.py` — translate `httpx`/JSON errors, add `httpx.Timeout(30, connect=5)`.
- `src/opencode_config/adapters/server_registry.py`, `opencode_config.py` — raise `ConfigError` with file path and cause on parse/validation failures.
- `src/opencode_config/use_cases/sync.py` — per-server try/except; `SyncResult` gains failures.
- `src/opencode_config/use_cases/list_servers.py` — same per-server catch; result rows gain error status.
- `src/opencode_config/cli/main.py` — render `✗` lines, map exit codes, catch `ConfigError`.
- Tests: adapter (closed port, httpserver 500/garbage), use case (fake client), CLI (capsys + exit codes).
- No new dependencies.
