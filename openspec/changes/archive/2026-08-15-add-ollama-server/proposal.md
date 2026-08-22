## Why

The tool only supports Lemonade servers, but Ollama is a widely-used local inference server that exposes an OpenAI-compatible API — exactly the provider shape we already emit to `opencode.json` (Ollama's own opencode integration docs prescribe the identical `@ai-sdk/openai-compatible` entry). Supporting it means one registry file manages every local inference server.

## What Changes

- `lemonade-servers.json` entries gain an optional `type` field (`"lemonade"` default, `"ollama"` new). Omitting `type` keeps existing files working unchanged.
- New `HttpOllamaClient` adapter: `GET /api/tags` for the model list, `POST /api/show` per model for capabilities and context length.
- Ollama models are normalized into the existing `Model` entity (capabilities → labels, `recipe="ollama"`) so existing filtering and mapping logic applies with a one-constant change.
- Sync emits one provider entry per Ollama server with `baseURL http://host:port/v1` (Ollama default port 11434).
- Sync prints a warning for Ollama models whose context window is below 64k (opencode's documented minimum; Ollama's default `num_ctx` is much smaller).
- **BREAKING** (internal only, no user-facing behavior change): `LemonadeClient` port renamed to a server-neutral name (`ModelServerClient`), `LemonadeError` → `ServerError`. Renamed now while the surface is small.
- Ollama Cloud (`https://ollama.com/api`, API keys) is explicitly out of scope.

## Capabilities

### New Capabilities
- `ollama-support`: Register Ollama servers in the registry; fetch and normalize their models; emit provider entries with correct baseURL; per-model degradation when `/api/show` fails; below-64k context warning.

### Modified Capabilities
- `error-handling`: Adds a fail-fast cause — a registry entry with an unknown `type` value is a config error (exit 2, no file written), alongside the existing missing-field causes.

## Impact

- `src/opencode_config/domain/entities.py` — `Server.type` field
- `src/opencode_config/domain/ports.py` — port/exception renames
- `src/opencode_config/adapters/ollama_client.py` — new
- `src/opencode_config/adapters/server_registry.py` — read `type`, per-type default port
- `src/opencode_config/use_cases/sync.py` — client dispatch by type, per-type baseURL
- `src/opencode_config/use_cases/list_servers.py` — works over both server types
- `src/opencode_config/use_cases/helpers.py` — `CHAT_RECIPES` gains `"ollama"`; `:latest` suffix strip
- Tests mirroring all of the above; no new dependencies (httpx already used)
