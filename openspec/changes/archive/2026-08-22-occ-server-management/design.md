# Design — occ-server-management

## Context

Today the CLI is a single argparse surface with mode flags (`-l`, `--init-servers`, implicit sync). The registry adapter is read-only, filters disabled servers at load, and treats zero-enabled as a config error. `ProviderConfig.disabled` exists in entities but is unused. Sync upserts via `dict.update()` and never removes entries.

Target: verb subcommands (`occ server add|remove|enable|disable|list`, `occ sync`), a read-write registry, immutable ids, and dual-file consistency after every command. Linux-only; no new dependencies; argparse subparsers suffice.

## Goals / Non-Goals

**Goals**
- Every lifecycle command exits with registry and `opencode.json` mutually consistent — no deferred cleanup for sync to discover.
- Ids minted once, never re-derived — renames never orphan provider entries.
- Legacy registries migrate transparently, adopting existing provider keys.

**Non-Goals**
- Model-level management (`occ models …`, `occ use …`) — separate future change.
- Auto-detection of server type on `add` — explicit `--type`, defaulted to `lemonade`.
- Duplicate host:port rejection — allowed; `-2` suffix handles the id collision.
- Windows/macOS support.

## Decisions

### D1: Remove-time deletion instead of sync-time reconciliation

`remove` deletes both the registry entry and the provider entry in the same invocation. Sync therefore never deletes anything; it stays an upsert-only refresh of enabled servers.

*Why not tracked-keys reconcile*: tracking which provider keys the tool owns (a `managed` list or `"occ": true` markers) adds bookkeeping to every write path and a new failure mode (list drift). Deleting at remove time — when the id is known — needs none of it.

*Trade-off*: a hand-deleted registry entry leaves an orphaned provider entry. Acceptable: the file is tool-managed, and `occ server list` shows only registry truth; orphans are visible by diffing against `occ server list`.

### D2: Identity — `id` field on registry entries, minted at add

Slug of `--name` else slug of host; `-2`/`-3`… on collision. `id` is the provider key and the argument to `remove`/`enable`/`disable`. `name` is display-only and freely editable.

*Migration*: entries without `id` get one derived with today's exact key derivation (slug of name, else slug of host), persisted on the next registry write. Existing `opencode.json` keys adopt by construction — no rename pass, no backup dance.

*Alternative rejected*: deriving keys from name on every sync (current behavior) — orphans entries on rename.

### D3: Disable maps to opencode's native `"disabled"` flag

Registry uses `"enabled": false` (defaults true, add if missing — per decision with user); `opencode.json` provider gets `"disabled": true`. `enable` sets/removes it back. opencode's schema (verified against opencode-schema.json) honors per-provider `disabled`, hiding the server from the model picker while keeping the models map cached for instant re-enable.

*Note*: the two files use inverted polarities by design — each file speaks its native dialect.

### D4: Registry becomes read-write; load stops filtering

`JsonServerRegistry` gains `add_server`, `remove_server`, `set_enabled` (load-modify-save whole file). `load_servers` returns **all** entries including disabled; filtering to enabled moves to the single place that wants it (sync; list wants all). The zero-enabled `ConfigError` is deleted — that state is now legitimate, and sync handles it as a no-op success.

*Alternative rejected*: keeping the filter in load and un-filtering — two call sites want different subsets; the loader should be truthful.

### D5: Add probes and seeds via the existing use-case path

`server add` = probe (existing `fetch_models` against the type's models path) → on success, register + run the same provider-entry build as sync for that one server. Unreachable → single-line `✗`, exit 1, nothing written. This reuses `sync.py`'s entry construction rather than duplicating it; extract the per-server entry build into a shared helper so add and sync can't drift.

### D6: One new use case module, thin CLI

`use_cases/server_management.py` hosts add/remove/enable/disable logic as plain functions over the ports. `cli/main.py` becomes a subparser dispatcher calling use cases — no business logic in the CLI layer, preserving the dependency rule (cli → use_cases → domain).

### D7: `occ` via console script

`[project.scripts] occ = "opencode_config.cli.main:main"` in pyproject.toml. `python -m opencode_config` keeps working. No renaming of the package itself.

## Risks / Trade-offs

- [Legacy registry has hand-mangled entries (e.g. duplicate names)] → id derivation collides → `-2` suffix mints a *new* key, orphaning the second entry's old provider. Mitigation: one-time manual check after first write; the tool never rewrites ids once present.
- [`disable` writes to `opencode.json` which may be mid-edit by opencode itself] → Same exposure as today's sync (full-file rewrite). Mitigation: none added — opencode does not hot-reload config mid-write in practice; keep atomic-ish write (single `write_text`) as today.
- [Registry write loses unknown/extra fields (comments impossible in JSON, but extra keys per entry)] → load-modify-save currently drops unknown entry fields if we reconstruct entries. Mitigation: mutate the raw dict, don't rebuild from dataclasses, so unknown keys survive round-trips.

## Migration Plan

1. Ship the CLI; on first registry write, ids appear. Existing `opencode.json` entries keep their keys (D2 adoption).
2. Rollback: revert the package; the registry with `id` fields still parses for the old code (unknown fields ignored by old loader), and provider entries are unchanged. No irreversible migration.
3. `--init-servers` users: `occ server add` replaces it; the old flag is removed (breaking, called out in proposal).

## Open Questions

- Should `occ sync` also refresh a just-enabled server automatically (i.e. `enable` implies a targeted sync)? Current answer per spec: no, models stay stale until sync. Cheap to revisit after usage.
