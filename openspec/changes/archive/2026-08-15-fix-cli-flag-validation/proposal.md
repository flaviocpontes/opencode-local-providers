# Proposal: fix-cli-flag-validation

## Why

The CLI accepts flags it silently ignores or actively misrepresents: `--dry-run` writes the config file anyway, `--show-all` is parsed but never read, and mode flags (`--init-servers`, `-l`, `-n`, `--version`) combine without validation so unrelated flags are silently dropped. The flag whose entire job is "don't touch anything" mutates the user's real config.

## What Changes

- Fix `--dry-run` (`-n`): sync must not write `opencode.json`; it prints the config that *would* be written to stdout instead.
- Wire `--show-all`: listing and sync include models with `downloaded: false` only when this flag is passed; default behavior filters them out.
- Add a mutually exclusive group for mode flags `--init-servers` and `--list-servers` (`-l`) so argparse rejects invalid combinations instead of silently ignoring them.
- Replace the hand-rolled `--version` with `action="version"` sourcing the version from installed package metadata (fallback to a literal for uninstalled runs).
- Sync use case returns the merged config so the CLI can print it in dry-run mode.

Not in scope (possible follow-up): subcommand restructure, friendly JSON error handling for a malformed registry, auto-creating the `--opencode` parent directory.

## Capabilities

### New Capabilities

- `cli-flags`: semantics and validation of the command-line interface — mode exclusivity, dry-run non-destructiveness, model visibility filtering, version reporting.

### Modified Capabilities

(none — no existing specs)

## Impact

- `src/opencode_config/cli/main.py` — parser changes, dry-run/show-all wiring.
- `src/opencode_config/use_cases/sync.py` — signature change (`dry_run`, `show_all` params; return value includes merged config).
- `src/opencode_config/use_cases/list_servers.py` — `show_all` param.
- `tests/test_cli/` (new) and `tests/test_use_cases/test_sync.py`, `tests/test_use_cases/test_list_servers.py` — updated/new tests.
- No adapter or domain changes (`Model.downloaded` is already parsed by `HttpLemonadeClient`).
- Not breaking: flag names and default behavior (other than dry-run no longer writing, which is the documented contract).
