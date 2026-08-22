## 1. Domain & registry

- [x] 1.1 Add `type: str = "lemonade"` to `Server` in `domain/entities.py`; add per-type default-port lookup (13305/11434) in `adapters/server_registry.py` honoring explicit `port` overrides
- [x] 1.2 Reject unknown `type` values in `adapters/server_registry.py` with `ConfigError` (single-line, names file and entry)
- [x] 1.3 Tests in `tests/test_adapters/test_server_registry.py`: omitted type → lemonade; ollama default port 11434; explicit port wins; unknown type raises

## 2. Server-neutral ports

- [x] 2.1 Rename `LemonadeClient` → `ModelServerClient` and `LemonadeError` → `ServerError` in `domain/ports.py`; update all references (`lemonade_client.py`, `sync.py`, `list_servers.py`, CLI wiring, tests) — behavior unchanged
- [x] 2.2 Run test suite; all green after mechanical renames

## 3. Helpers for Ollama models

- [x] 3.1 In `use_cases/helpers.py`: accept `"ollama"` in `CHAT_RECIPES`; strip trailing `:latest` in `derive_display_name`
- [x] 3.2 Tests in `tests/test_use_cases/` (or existing helpers test home): ollama-recipe chat model passes gate; embed-style model (recipe `""`) excluded; `gemma4:latest` → name `gemma4`, id unchanged

## 4. Ollama adapter

- [x] 4.1 Create `adapters/ollama_client.py`: `GET /api/tags` → list; per model `POST /api/show` → capabilities + context; map to `Model` (`vision`→labels, `thinking`→`reasoning` label, `recipe="ollama"` only when `completion` capability present or info missing, context via `num_ctx` param else `model_info.*.context_length`); failed `show` → unenriched model, no server failure; sequential calls with `# ponytail:` note on parallelism ceiling
- [x] 4.2 Verify capability strings against a live server (`curl http://localhost:11434/api/show -d '{"model":"..."}'`) if one is available; adjust mapping only if chat models lack `completion`
- [x] 4.3 Tests in `tests/test_adapters/test_ollama_client.py` using real HTTP fixtures (no mocks): tags+show happy path; show failure degrades; context extraction both ways; vision/thinking labels

## 5. Sync integration

- [x] 5.1 In `use_cases/sync.py`: select client per `server.type`; build `baseURL` per type (`/api/v1` vs `/v1`); emit one warning line per model with `0 < max_context_window < 65536`
- [x] 5.2 Confirm `use_cases/list_servers.py` works over both types (adjust only if it hardcodes lemonade assumptions)
- [x] 5.3 Tests: mixed registry writes both entries with correct baseURLs; sub-64k model warns and is still included; unknown-context model silent; existing lemonade sync tests unchanged

## 6. Verification

- [x] 6.1 `uv run pytest` — full suite green
- [x] 6.2 `uv run ruff check` — clean
- [x] 6.3 `openspec validate add-ollama-server` — passes
