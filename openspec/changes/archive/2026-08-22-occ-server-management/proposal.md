## Why

The tool is a flag-driven one-shot sync. Managing local inference servers (adding a box, retiring one, temporarily disabling a machine that's off) means hand-editing `local-inference-servers.json` and re-running. We want a verb-driven CLI (`occ`) that owns the full server lifecycle, keeping the registry and `opencode.json` consistent after every command.

## What Changes

- **BREAKING**: Replace the flag-driven CLI (`-l`, `--init-servers`, default-sync-on-no-args) with argparse subcommands: `occ server add|remove|enable|disable|list` and `occ sync`.
- New `server` command group managing entries in `~/.config/opencode/local-inference-servers.json`:
  - `add` probes the server's `/models` endpoint first and refuses unreachable hosts; mints an immutable id (`--name` slug, else host slug; `-2` suffix on collision).
  - `disable` writes `"enabled": false` in the registry AND `"disabled": true` on the opencode.json provider entry (models kept).
  - `enable` flips both flags back.
  - `remove` deletes the registry entry and the opencode.json provider entry.
  - `list` shows the registry with live model counts for enabled servers; disabled servers shown unprobed.
- Registry entries gain an `id` field (immutable after minting; `--name` becomes display-only). Old registries without ids migrate transparently on first write using today's key-derivation.
- Sync keeps current fail-soft behavior for unreachable servers, but no longer errors when the registry has zero enabled servers (disabling your last server is legitimate).
- Executable renamed to `occ` via `[project.scripts]` in pyproject.toml.
- Linux-only clients and servers (no platform abstraction; `~/.config/opencode/` path stays hardcoded).

## Capabilities

### New Capabilities
- `server-management`: Lifecycle commands (add/remove/enable/disable/list) for local inference servers, including id minting/immutability, reachability probe on add, dual-flag disable semantics (registry `enabled` ⟷ opencode `disabled`), remove-time cleanup of both files, and legacy registry migration to ids.

### Modified Capabilities
- `cli-flags`: Flag-driven modes (`-l`/`--list-servers`, `--init-servers`, implicit default sync) are replaced by the `occ server <verb>` and `occ sync` subcommand surface. `--dry-run`, `--show-all`, `--servers`, `--opencode`, `--version` survive as flags on the relevant subcommands.
- `error-handling`: The "registry contains no enabled servers → exit 2" rule is removed (zero enabled servers is now a valid state). New failure modes added: `add` on unreachable server, `remove/enable/disable` on unknown id, duplicate id minting.

## Impact

- **Code**: `cli/main.py` (rewrite to subcommands), `adapters/server_registry.py` (read+write, id migration, drop disabled-filtering and all-disabled error), `use_cases/sync.py` (drop redundant enabled filter, disable write-through), `domain/entities.py` (Server.id), `domain/ports.py` (registry port gains mutations), new `use_cases/server_management.py`.
- **Registry schema**: entries gain `id`; file remains a list under `"servers"`.
- **opencode.json**: provider entries gain `"disabled": true` when disabled; sync output otherwise unchanged.
- **Packaging**: `[project.scripts] occ = "opencode_config.cli.main:main"`; `python -m opencode_config` keeps working.
- **Docs**: AGENTS.md structure section becomes stale (documented elsewhere; update on archive).
