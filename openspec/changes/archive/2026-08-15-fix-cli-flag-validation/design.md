# Design: fix-cli-flag-validation

## Context

See proposal.md — Why. Current state: `main()` builds adapters and calls use cases unconditionally; `sync_models()` always writes via `OpenCodeConfigPort.write_config()`; `Model.downloaded` is parsed by `HttpLemonadeClient` (defaults `True`) but never consumed. Constraint: clean architecture — the write lives inside the use case, so dry-run must be threaded through rather than intercepted at the CLI layer.

## Goals / Non-Goals

**Goals:**

- Flags do what their help text promises; invalid combinations fail loudly.
- Minimal diff — Option A (patch flags), no subcommand restructure.

**Non-Goals:**

- Subcommand restructure, registry JSON error messages, `--opencode` parent dir creation (explicitly deferred; see proposal).
- Any adapter or domain changes.

## Decisions

### D1: Dry-run as a parameter on `sync_models`, not a CLI-side intercept

`sync_models(..., dry_run: bool = False)` skips `write_config()` when set. Alternative considered: split the use case into `merge`/`write` and let the CLI decide — rejected, it doubles the call sites and the port surface for one boolean.

Return type changes from `list[str]` to a small result: `SyncResult(summary: list[str], config: dict)` (dataclass in `use_cases/sync.py`). The CLI needs the merged config to print in dry-run mode; returning it avoids re-reading/re-merging in `main()`. Alternative: return tuple — dataclass is self-documenting for the same line count.

### D2: `show_all` filtered in the use cases, not the adapter

Both `sync_models` and `list_servers` take `show_all: bool = False` and filter `[m for m in models if show_all or m.downloaded]` after the existing `is_chat_model` filter. Alternative: filter in `HttpLemonadeClient` — rejected, it would make the adapter lossy for any future caller that wants full inventory. `Model.downloaded` defaulting to `True` in the adapter means real Lemonade servers that omit the field keep working unchanged.

### D3: Mutually exclusive group for the two file/mode flags

`parser.add_mutually_exclusive_group()` containing `--init-servers` and `-l/--list-servers`. `--version` uses `action="version"` (which exits itself, no interaction with the group). `-n` and `--show-all` stay independent modifiers — they may combine with sync or listing.

### D4: Version via `importlib.metadata`

`importlib.metadata.version("opencode_config")` with `except PackageNotFoundError` falling back to `"0.1.0"`, passed to `action="version"` as `version=`. Avoids a second hardcoded string drifting from `pyproject.toml`. (Ponytail note: stdlib, zero deps.)

### D5: Dry-run output shape

When `dry_run`, print the summary lines as usual, then `json.dumps(merged_config["provider"], indent=2)` under a `--- <path> (dry-run) ---` header. Only the `provider` key we own — printing the whole merged config invites confusion about which keys the tool manages.

## Risks / Trade-offs

- [Signature changes break existing tests] → Update `test_sync.py` / `test_list_servers.py` in the same change; defaults keep old call sites compiling.
- [`downloaded` semantics unverified against real Lemonade API] → Adapter already defaults `True`; worst case (field never sent) behavior is identical to today. Spec scenario covers the `false` case.
- [Mutual exclusion is argparse-level, exit code 2 not 1] → Matches argparse convention for usage errors; acceptable and testable.
