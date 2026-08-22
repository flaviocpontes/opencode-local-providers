## Context

Clean Architecture layering (see AGENTS.md): `domain` → `use_cases` → `adapters` → `cli`, dependencies inward only. Today every adapter raises raw library exceptions (`json.JSONDecodeError`, `KeyError`, `httpx.ConnectError`) that propagate through use cases to an unguarded `main()`. The tool is multi-server by design (registry file), so error handling must distinguish user-file problems (deterministic, must abort) from per-server problems (independent, should not block siblings).

## Goals / Non-Goals

**Goals:**

- No tracebacks on any anticipated failure path; one-line messages with actionable context (file path, server name, cause).
- Fail-soft per server in both `sync` and `list-servers` use cases.
- Domain-owned error types so use cases and CLI never import `httpx`/`json` error details.
- Stable exit codes: 0 success, 1 runtime failure (some server failed), 2 config/usage error.

**Non-Goals:**

- Retry/backoff for flaky servers — a re-run is the retry.
- Removing or annotating stale provider entries in `opencode.json` on failure (preserved byte-identical instead).
- Validating `opencode.json` beyond JSON parseability (schema of provider entries is opencode's concern).
- Friendly handling of malformed Lemonade API payloads (e.g. model item missing `id`) — that is an upstream schema bug; traceback is acceptable and honest. Marked with a `ponytail:` comment.

## Decisions

### D1: Two exception classes in `domain/ports.py`, beside the ports

`ConfigError(message)` and `LemonadeError(server_label, cause)`.

- **Why here:** domain owns the vocabulary; ports file already exists, zero new files. CLI can catch `ConfigError` without knowing which adapter raised it.
- **Alternative:** a `domain/errors.py` module — rejected, one more file for two small classes.
- **Alternative:** catch-all `Exception` handler in `main()` — rejected: lives outside the per-server loop, so fail-soft is impossible, and it hides programming errors.

`LemonadeError` carries the server label (`server.name or host:port`) so the CLI renders without re-deriving display names. The original exception is chained (`raise ... from exc`).

### D2: Adapters translate at the boundary

- `JsonServerRegistry.load_servers()` / `JsonOpenCodeConfig.load_config()`: wrap parse in try/except → `ConfigError(f"could not parse {path}: {msg}")`. Missing `host` → `ConfigError` naming the entry index and path. Zero enabled servers is checked where the count is known — in the registry adapter on load — and raised as `ConfigError` (deterministic, file-content problem).
- `HttpLemonadeClient.fetch_models()`: one `except (httpx.HTTPError, ValueError)` clause wrapping connect/read/timeout/status/JSON failures → `LemonadeError(label, short cause)`. One catch, not six: `httpx.HTTPError` is the common base; `ValueError` covers `json.JSONDecodeError` for non-JSON bodies. Message extraction: `str(exc)` truncated, with connect errors rendered as "connection refused"/"timeout" rather than httpx's nested phrasing where cheap.

**Why adapter-side, not use-case-side:** use cases depend on the domain only (dependency rule); catching `httpx` there would bend the rule the same way catching it in the CLI would. The adapter is the only layer that already knows the transport.

### D3: Fail-soft loop lives in the use cases

Both `sync_models` and `list_servers` wrap `fetch_models(server)` in try/except `LemonadeError`, append to a `failures` list, `continue`. 

- `SyncResult` gains `failures: list[tuple[str, str]]` (label, cause).
- `list_servers` result rows gain `"error": cause` (or `None`).

**Alternative:** catch in CLI per mode — rejected: duplicates the loop knowledge in layer 3 and couples rendering to control flow.

**Stale-entry semantics:** merge in `sync_models` is already `config["provider"].update(providers)` — a skipped server simply contributes no key, so its old entry survives untouched by construction. No extra code; the CLI message states it.

### D4: CLI renders and maps exit codes

`main()` gains, after both modes: print `✗ {label}: {cause} — entry left unchanged, skipped` per failure; set exit code 1 if any. One top-level `except ConfigError` around dispatch prints the message and exits 2. `SystemExit` codes: reuse argparse's 2 for config errors so "bad input" is one family for callers.

### D5: Explicit timeouts in `HttpLemonadeClient`

`httpx.Timeout(30, connect=5)`. LAN context: 5s TCP connect is generous (refused is instant; blackholed hosts fail at 5s), 30s read covers slow first-token on model listing.

**Alternative:** env-var-configurable timeout — rejected, YAGNI; constructor parameter already exists for tests.

## Risks / Trade-offs

- [Registry adapter raising on zero enabled servers] → changes `load_servers()` semantics from "returns list" to "raises if empty". Mitigation: only raise when the filtered list is empty and the file had entries (a missing/empty file already produces a distinct friendly message in the CLI); covered by use-case tests.
- [`str(exc)` of httpx exceptions can be verbose] → Mitigation: derive short cause strings in the adapter (`ConnectError` → "connection refused", `TimeoutException` → "timeout", `HTTPStatusError` → `HTTP {code}`); a mapping dict, ~5 entries.
- [Exit code 1 on partial failure may surprise scripts assuming 0/2 only] → Mitigation: documented in spec; 0/1/2 matches argparse convention (0 ok, nonzero = attention).
- [Two error classes invite future taxonomy creep] → Mitigation: resist; add a third class only when a behavior needs a third exit code.

## Migration Plan

Single PR, backward compatible except: full-failure runs that previously crashed (traceback, exit 1 via unhandled exception) now exit 1 with clean messages — same code, better output; partial-failure runs that previously crashed now succeed partially (exit 1). No config format changes. Rollback = revert commit; no data migration.

## Open Questions

None. (Timeout values 5s/30s are judgement calls; both are constructor-tunable, changing them later is not a design change.)
