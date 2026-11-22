# align-chat-model-filter

## Why

`occ sync` silently drops Lemonade chat models served by engines the recipe allowlist does not know. The allowlist mirrors Lemonade v11.7.0's `model_types.h`, but the server is now v11.9.0 and upstream has added chat engines since: `gufo` (container backend), `llamacpp-hrx` (29 registry models), `ds4`, `rocmfpx`, and `halogen`. Meanwhile upstream rewrote its classifier to be **label-driven**: only the `chat` label makes a model deploy as an LLM, and the server's own routing now depends on that label — making it a stable contract occfg can mirror instead of a recipe snapshot it must chase every release.

## What Changes

- Replace the recipe allowlist gate in `is_chat_model()` with a faithful mirror of upstream's deployment-mode classification:
  1. `chat` in labels → include (upstream checks it first, so omni models like `[chat, vision, chat-transcription]` stay chat)
  2. any deployment label (`embeddings`, `embedding`, `reranking`, `transcription`, `tts`, `image`, plus new `audio-generation`, `classification`, `classifier`, `3d`) → exclude
  3. no mode label at all → include (upstream defaults to LLM; preserves today's handling of label-less `user.` models)
- Exclude collection recipes (`collection.omni`, `collection.router`) via a small denylist — composite models carry the `chat` label but are not standalone chat models.
- Remove the CHAT_LABELS superset (`vision`, `reasoning`, `tool-calling`, `tools`, `chat-transcription` no longer force inclusion). Only `chat` does, matching upstream's documented semantics ("they never make one").
- Behavioral edge: a model with a deployment label but no `chat` label that was previously included via the superset (e.g. hypothetical `[vision, transcription]`) is now excluded. No such model exists in the current upstream registry, and upstream would deploy it as a non-LLM anyway.
- Update the stale recipe/label table in `AGENTS.md` (currently documents v11.7.0).

## Capabilities

### New Capabilities

- `model-filtering`: how sync decides which Lemonade server models become opencode provider entries — label-driven chat classification mirroring Lemonade's deployment-mode semantics, instead of a version-pinned recipe allowlist. (Ollama's capability-based detection stays in `ollama-support`.)

### Modified Capabilities

(none — `ollama-support`'s requirement covers Ollama capability detection, which is unchanged.)

## Impact

- `src/opencode_config/use_cases/helpers.py` — `is_chat_model()`, `CHAT_LABELS`/`SKIP_LABELS`/`CHAT_RECIPES` constants.
- `tests/test_use_cases/` — new label-based fixtures (gufo/hrx-style chat models, audio-generation/classification/3d skips, collections, label-less user models).
- `AGENTS.md` — model filtering reference table.
- No CLI surface, registry schema, `opencode.json` schema, or dependency changes.
