# Tasks — occ-server-management

## 1. Domain & registry foundation

- [x] 1.1 Add `id: str | None = None` to `Server` entity; extend `ServerRegistryPort` with `add_server`, `remove_server`, `set_enabled` (tests: fake registry in use-case tests still satisfies port)
- [x] 1.2 Make `JsonServerRegistry` read-write: load ALL entries (no disabled filtering, no zero-enabled error), derive+persist missing `id`s using slug(name) else slug(host), mutate raw dicts on write so unknown fields survive; implement the three mutation methods with duplicate-id guard on add
- [x] 1.3 Update registry adapter tests: all-disabled load succeeds, id migration (legacy file gains ids on write, ids match current provider-key derivation), unknown fields preserved, mutations round-trip

## 2. Use cases

- [x] 2.1 Extract per-server provider-entry build (key from `server.id`, base URL, models dict, warnings) from `sync_models` into a shared helper; sync uses `server.id` as provider key and keeps upsert-only semantics
- [x] 2.2 `sync_models`: filter to enabled servers in-loop (registry no longer pre-filters); zero enabled servers → no-op success with "nothing to do" message, no write
- [x] 2.3 New `use_cases/server_management.py`: `add_server` (probe via client → register with minted id → seed provider entry via shared helper), `remove_server` (registry entry + provider entry delete, tolerate missing provider), `set_server_enabled(id, enabled)` (registry flag + provider `disabled` flag add/remove)
- [x] 2.4 Use-case tests for all four operations with fake registry/config/clients: unreachable probe writes nothing, id collision suffixing, disable-then-sync skips server, enable flips both flags, remove cleans both files, unknown id raises/returns error

## 3. CLI surface

- [x] 3.1 Rewrite `cli/main.py` as subparser dispatch: `server add <host> [--type] [--port] [--name]`, `server remove|enable|disable <id>`, `server list`, `sync [-n|--dry-run] [--show-all]`; keep global `--servers`, `--opencode`, `--version`; no-args prints usage exit 0
- [x] 3.2 `server list` output: per-entry block (id, name, host:port, type, enabled state), probe enabled servers for chat-model counts (reuse `list_servers`), disabled unprobed, exit 1 on probe failure
- [x] 3.3 Error mapping in CLI: unknown id and add-probe failure → single-line message, exit 1; `ConfigError` → exit 2; drop `--init-servers` mode
- [x] 3.4 CLI tests: dispatch of every subcommand, exit codes (0/1/2), no-args usage, unknown subcommand usage error, `--version` still works

## 4. Packaging & docs

- [x] 4.1 Add `[project.scripts] occ = "opencode_config.cli.main:main"` to pyproject.toml; verify `uv run occ --version` and `uv run python -m opencode_config --version` both work
- [x] 4.2 Update AGENTS.md: new CLI surface, registry schema with `id`, dual-flag disable semantics, `occ` entry point
- [x] 4.3 Full check: `uv run pytest` green, `ruff check` clean; manual smoke: `occ server add` against fake server (pytest-httpserver), disable → inspect both files, enable, remove → both clean

## 5. Spec sync & archive prep

- [x] 5.1 Walk specs/server-management, cli-flags and error-handling deltas against implementation; confirm every scenario has a covering test or manual smoke; then archive per workflow
