## 1. Domain errors

- [x] 1.1 Add `ConfigError` and `LemonadeError(server_label, cause)` to `src/opencode_config/domain/ports.py` (chained via `from exc` at raise sites)

## 2. Adapter translation

- [x] 2.1 `JsonServerRegistry`: raise `ConfigError` naming path on JSON parse failure and on entry missing `host` (name the entry index); raise `ConfigError` when file has entries but zero enabled after filtering
- [x] 2.2 `JsonOpenCodeConfig.load_config`: raise `ConfigError` naming path and cause on parse failure
- [x] 2.3 `HttpLemonadeClient`: set `httpx.Timeout(30, connect=5)` as client default; wrap `fetch_models` body in `except (httpx.HTTPError, ValueError)` → `LemonadeError`; map exceptions to short causes (refused / timeout / `HTTP {code}` / invalid response)
- [x] 2.4 Adapter tests: closed local port → `LemonadeError`; pytest-httpserver 500 and garbage body → `LemonadeError` with short cause; bad registry JSON, missing `host`, zero enabled, bad `opencode.json` → `ConfigError` (real temp files, no mocks)

## 3. Use cases: fail-soft

- [x] 3.1 `sync_models`: per-server try/except `LemonadeError` → `failures` list on `SyncResult`, `continue`; skipped server contributes no provider key (stale entry survives)
- [x] 3.2 `list_servers`: same catch; failed server becomes a row with `"error"` cause instead of aborting
- [x] 3.3 Use-case tests with fake adapters: A raises `LemonadeError`, B returns models → B synced/listed, A in failures, no raise

## 4. CLI: rendering and exit codes

- [x] 4.1 Render `✗ {label}: {cause} — entry left unchanged, skipped` lines for sync; `✗ {label} — {cause}` rows for `-l`; reachable servers render as today
- [x] 4.2 Exit codes: 0 all good, 1 any server failure, 2 config errors (top-level `except ConfigError` → print message, exit 2)
- [x] 4.3 CLI tests (capsys + `SystemExit`): dead server among healthy → `✗` line, good provider written, exit 1; bad registry JSON → exit 2, no traceback, no write; zero enabled servers → exit 2; `-l` with dead server → status row, exit 1

## 5. Verification

- [x] 5.1 `uv run main.py` (no args) still prints usage, exit 0
- [x] 5.2 `uv run pytest` green; `ruff check` clean
