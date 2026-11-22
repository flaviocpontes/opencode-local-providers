# Tasks — align-chat-model-filter

## 1. Label-driven classification in helpers

- [x] 1.1 Rewrite `is_chat_model()` in `src/opencode_config/use_cases/helpers.py` per design D1: exclude `collection.omni`/`collection.router` recipes; include on `chat` label; exclude on any deployment label; include when no mode label. Replace `CHAT_LABELS`/`CHAT_RECIPES` with `COLLECTION_RECIPES` and an extended `SKIP_LABELS` (`audio-generation`, `classification`, `classifier`, `3d` added). Verify with `uv run pytest tests/test_use_cases -q` after task 1.2 fixtures land.
- [x] 1.2 Update/extend use-case tests to cover every scenario in `specs/model-filtering/spec.md`: gufo-recipe chat model included; `[chat, vision, chat-transcription]` included; `[chat, transcription]` included (chat outranks deployment); `[embeddings]`, `[audio-generation]`, `[classification]`, `[3d]` excluded; `[vision, transcription]` (no chat) excluded; label-less `user.` model included; `[vision, tool-calling, mtp]` included; `collection.omni` with `[chat]` and `collection.router` excluded. Verify with `uv run pytest tests/test_use_cases -q` — all pass.

## 2. Regression and docs

- [x] 2.1 Run the full suite and lint: `uv run pytest -q` and `uv run ruff check` — zero failures, zero lint errors. Fix any fixture in `tests/test_cli/` or `tests/test_e2e/` that still pins recipe-allowlist behavior.
- [x] 2.2 Update the "Model filtering" section of `AGENTS.md`: replace the recipe include/exclude table with the label-priority rules (chat → include; deployment label → exclude; no mode label → include; collections excluded), update the deployment-label list with the four new labels, and note the reference upstream version. Verify by reading the section against `specs/model-filtering/spec.md` — no contradictions.
- [x] 2.3 Live smoke test: `uv run occfg sync -n` (dry run) against the Lemonade server at 192.168.0.20 — confirm `Qwen3.8-27B-Gufo` now appears and previously-included chat models (e.g. `Qwen3.8-27B-GGUF`) still do. Then run `uv run occfg sync` and check `opencode.json` contains `Qwen3.8-27B-Gufo` with `modalities.input` including `image` (it has the `vision` label).
