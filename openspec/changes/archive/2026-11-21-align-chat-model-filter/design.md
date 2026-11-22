# Design — align-chat-model-filter

## Context

`is_chat_model()` in `src/opencode_config/use_cases/helpers.py` gates on a recipe allowlist (`CHAT_RECIPES = {llamacpp, flm, ryzenai-llm, vllm, ollama}`) mirroring Lemonade v11.7.0's `model_types.h`, then applies a label pass where a CHAT_LABELS superset (`chat`, `vision`, `reasoning`, `tool-calling`, `tools`, `chat-transcription`) forces inclusion and SKIP_LABELS excludes. Upstream's current `model_types.h` (server v11.9.0) rewrote classification: `find_deployment_mode()` dispatches on labels only — `chat` first, then deployment labels — and `get_model_type_from_labels()` defaults label-less models to LLM; recipe no longer determines chat-ness. The server's routing depends on the `chat` label, which makes it a contract. Registry evidence (v2026.48 `server_models.json`): every chat model across all 8 chat recipes carries `chat`; every non-chat model carries a deployment label; only collections carry `chat` while not being standalone chat models.

## Goals / Non-Goals

**Goals:**

- Classify Lemonade chat models by labels alone, mirroring upstream's deployment-mode semantics exactly (priority order included).
- Make future upstream engines self-include without occfg releases.
- Preserve current behavior for label-less `user.` models.

**Non-Goals:**

- Changing Ollama capability-based detection (spec'd in `ollama-support`).
- Changing field mapping (`vision` → modalities, `reasoning` → output limit, context warnings) — untouched.
- Surfacing "skipped unknown recipe" warnings (recipe is no longer consulted for chat classification).
- Covering `collection.*` recipes beyond excluding them.

## Decisions

### D1: Faithful mirror of `find_deployment_mode`, not strict require-`chat`

Classification in priority order, exactly like upstream:

1. recipe in `{collection.omni, collection.router}` → **exclude**
2. `chat` in labels → **include**
3. any deployment label in `{embeddings, embedding, reranking, transcription, tts, image, audio-generation, classification, classifier, 3d}` → **exclude**
4. no mode label → **include**

- Alternative rejected: strict `chat` required (step 4 → exclude). User-pulled models (`user.X`) are registered with optional labels (`POST /v1/pull` accepts `labels?`); the documented example `user.Qwen3.6-27B-GGUF-…` is included today precisely because of the label-less default. Strict would silently drop them. Default-include also matches upstream (`get_model_type_from_labels` → LLM) and the Ollama spec's conservative-include requirement — one philosophy across both server types.
- Step order matters: `chat` before deployment labels, so `[chat, transcription]` (omni declaring a standalone mode) stays chat — upstream added that check order deliberately for exactly this case.

### D2: Collection denylist by recipe, minimal

Collections (`collection.omni`, `collection.router`) carry the `chat` label but are composite routers; they must not become opencode provider entries. A two-value recipe denylist is the smallest mechanism that keeps D1 faithful. Alternatives: matching a `collection.` prefix (over-broad — upstream mints specific names) or filtering on collection-specific labels (none exist).

### D3: Drop the CHAT_LABELS superset

`vision`, `reasoning`, `tool-calling`, `tools`, `chat-transcription` stop forcing inclusion. Upstream's header comment is explicit: these describe capabilities and "never make one [a chat model]". Keeping them would diverge from the mirrored classifier for zero registry benefit (no chat model lacks `chat`). Consequence: `[vision, transcription]` with no `chat` flips from included to excluded — correct per upstream (it would deploy as transcription) and no such model exists today.

### D4: Constants rename, same module

`CHAT_RECIPES` → deleted; `SKIP_LABELS` gains `audio-generation`, `classification`, `classifier`, `3d`; new `COLLECTION_RECIPES = {"collection.omni", "collection.router"}`. All stay in `helpers.py` (domain-adjacent pure functions, no new module, no port changes). `Model.recipe` remains a field but no longer signals chat-ness anywhere: the Ollama adapter previously encoded "not a chat model" as `recipe=""` (relying on the old recipe gate) — it now stamps a `chat` or internal `not-chat` **label** instead, keeping the shared filter label-driven for both server types and preserving the `ollama-support` exclusion behavior verbatim.

## Risks / Trade-offs

- [Upstream mints a new deployment label we don't know (e.g. a future `video` mode)] → Such a model with no `chat` label and no known deployment label falls through to include. Same residual risk upstream's own default carries; bounded by upstream's routing needing the same labels. Monitor at upgrade time via the AGENTS.md reference table.
- [A label-less non-chat model appears (registry today: none)] → Included, and opencode would fail at runtime if selected. Accepted: identical to upstream's deployment decision and today's behavior for known recipes.
- [Behavioral flip for `[vision, transcription]`-style labels] → No observed instances in the v2026.48 registry; excluded-by-upstream anyway. Test fixtures pin the semantics.
- [Runtime dialect of new engines (gufo container backend) may differ] → Lemonade fronts all engines with one OpenAI-compat router; models classified LLM serve `/v1/chat/completions`. Implementation tasks include a smoke test against the live gufo model.

## Migration Plan

Single-pass change, no persisted-state migration: the filter is pure and recomputed every sync. Rollback = revert the commit; stale provider entries self-correct on the next sync (upsert-only). After implementation, run `occfg sync` and confirm `Qwen3.8-27B-Gufo` appears in `opencode.json`.

## Open Questions

None blocking. (Whether to also warn on excluded-with-`chat` collections can be decided during implementation without changing specs.)
