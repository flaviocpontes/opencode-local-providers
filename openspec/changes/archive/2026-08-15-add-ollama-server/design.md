## Context

The codebase already has the right shape for this: `fetch_models(server) -> list[Model]` is a server-agnostic port, `sync_models()` maps `list[Model]` to the opencode provider format, and Ollama's opencode integration docs prescribe the exact provider entry structure we already emit (same npm package; baseURL path `/v1` instead of `/api/v1`). Ollama's native API differs from Lemonade's: model listing is `GET /api/tags`, and capabilities/context live only in per-model `POST /api/show` responses (`capabilities` array, `model_info.<arch>.context_length`).

## Goals / Non-Goals

**Goals:**
- One registry file manages Lemonade and Ollama servers with zero migration for existing files.
- Ollama models flow through the *same* filtering/mapping code path as Lemonade models (normalize at the adapter boundary, not downstream).
- Server-neutral naming in ports so further server types (llama.cpp server, vLLM) are additive.

**Non-Goals:**
- Ollama Cloud (`https://ollama.com/api` + API key auth).
- Pulling/creating models, changing `num_ctx` — read-only sync, same as Lemonade today.
- Concurrent `/api/show` requests.

## Decisions

**1. `Server.type` discriminator, default `"lemonade"`.**
Registry reads `type` per entry; unknown value raises `ConfigError` (spec: error-handling delta). Default port resolved per type in the registry adapter (`13305` / `11434`) so `sync` stays dumb about defaults. Alternative rejected: separate registry files per server type — two files to keep in sync and no benefit.

**2. Normalize Ollama → `Model` at the adapter boundary.**
`HttpOllamaClient` translates Ollama concepts into the existing entity: `capabilities` → `labels` (`"vision"`→`vision`, `"thinking"`→`reasoning`), `recipe="ollama"`, context length → `max_context_window`. This makes the whole downstream pipeline (filter, map, entry build) shared. Cost: the `Model` fields carry slightly borrowed names for Ollama models; accepted, the entity is the tool's internal lingua franca.

**3. Chat filtering by positive gate.**
`is_chat_model` gains: `"ollama"` recipe models pass iff the adapter recorded a `completion` capability, or recorded no capability info at all (conservative include, per spec). Embedding/audio models don't report `completion`, so no blocklist of capability names is needed. Concretely: the adapter sets `recipe="ollama"` only for models that passed the gate, else `recipe=""` which already fails the `CHAT_RECIPES` check.

**4. `POST /api/show` per model, sequential.**
Capabilities and context are unavailable from `/api/tags`, so enrichment requires one `show` call per model. Sequential httpx calls on a LAN/local server cost milliseconds each; a `# ponytail:` comment marks the ceiling (parallelize with a small worker pool if a server ever lists hundreds of models). A failed `show` for one model degrades to an unenriched entry — never drops the model, never fails the server.

**5. Context length extraction order.**
Prefer `num_ctx` from the `parameters` text block when the user overrode it, else `model_info` key ending in `.context_length`. Capabilities come from the `capabilities` array; `details.family`/`parameter_size`/`quantization_level` are ignored (display names come from the id).

**6. Renames now: `LemonadeClient` → `ModelServerClient`, `LemonadeError` → `ServerError`.**
Internal-only (protocol names and exception class), no CLI or file-format impact. Done in this change because post-change "LemonadeClient" would be serving Ollama traffic — a lie. One rename commit while the surface is ~6 files beats a later mechanical rename across a bigger codebase.

**7. 64k warning lives in the sync use case.**
After filtering, models with `0 < max_context_window < 65536` get one warning line each in the summary output. Rationale: Ollama defaults `num_ctx` low (2048–8k) and opencode documents 64k as its minimum — this is the integration's main footgun. Warning (not exclusion) keeps the tool non-opinionated.

## Risks / Trade-offs

- [Capability string uncertainty: docs show `completion`/`vision`; embedding models' exact capability name (`embed` vs `embedding`) unverified] → The positive gate doesn't depend on the embedding name — only on `completion` being present for chat models. Verify with a live `curl /api/show` during implementation; if some chat model lacks `completion`, fall back to conservative-include via the no-info path.
- [N+1 `show` calls against a remote/slow server] → Sequential with the existing 30s/5s timeouts; per-model failure degrades instead of aborting. Parallelism deferred (see Decision 4).
- [Rename churn in tests] → Mechanical find/replace; CI green is the check.

## Migration Plan

No user-facing migration: `type` is optional and defaults to `lemonade`. Rollback is `git revert` — no persisted format changes beyond additive registry fields.
