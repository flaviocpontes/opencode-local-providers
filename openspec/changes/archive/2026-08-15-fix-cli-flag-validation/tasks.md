## 1. Use cases

- [x] 1.1 `sync.py`: add `SyncResult` dataclass (`summary: list[str]`, `config: dict`); change `sync_models` signature to `(server_registry, lemonade, opencode_config, dry_run=False, show_all=False)`; skip `write_config()` when `dry_run`; filter undownloaded models unless `show_all`
- [x] 1.2 `list_servers.py`: add `show_all: bool = False` param; filter undownloaded models unless `show_all`
- [x] 1.3 Update `tests/test_use_cases/test_sync.py` and `test_list_servers.py` for new signatures; add cases: dry-run writes nothing, default filters `downloaded=False`, `show_all=True` includes it, chat-only filter still applies with `show_all`

## 2. CLI

- [x] 2.1 `main.py`: add `--init-servers` and `-l/--list-servers` to a mutually exclusive group
- [x] 2.2 `main.py`: replace hand-rolled `--version` with `action="version"` using `importlib.metadata.version("opencode_config")` (fallback `"0.1.0"` on `PackageNotFoundError`)
- [x] 2.3 `main.py`: wire `dry_run`/`show_all` into `sync_models` and `list_servers` calls; on dry-run print `SyncResult.config["provider"]` as labeled JSON instead of the current re-read-the-file block
- [x] 2.4 Add `tests/test_cli/test_main.py` covering: conflicting modes exit with code 2; dry-run leaves file untouched (existing and missing-file cases); `--version` exits 0; `--show-all` passes through to use cases

## 3. Verification

- [x] 3.1 `uv run pytest` green, including new tests
- [x] 3.2 `ruff check` clean
- [x] 3.3 Manual smoke: `uv run python -m opencode_config --init-servers -l` errors; `-n` against a copy of a real config leaves it byte-identical
