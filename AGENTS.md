# AGENTS.md

Syncs models from Lemonade Servers into opencode.json providers.

## Project Structure (Clean Architecture)

```
opencode_config/
├── src/
│   └── opencode_config/
│       ├── __init__.py
│       ├── __main__.py              # python -m opencode_config entrypoint
│       ├── domain/                  # Layer 0 — Enterprise business rules
│       │   ├── entities.py          #   Server, Model, ProviderConfig dataclasses
│       │   └── ports.py             #   Abstract base classes / protocols
│       ├── use_cases/               # Layer 1 — Application business rules
│       │   ├── __init__.py
│       │   ├── sync.py              #   Orchestrate fetch + merge per server
│       │   └── list_servers.py      #   Summarise servers & models
│       ├── adapters/                # Layer 2 — Interface adapters
│       │   ├── __init__.py
│       │   ├── lemonade_client.py   #   HTTP → Lemonade /api/v1/models
│       │   ├── server_registry.py   #   Read/write lemonade-servers.json
│       │   └── opencode_config.py   #   Read/write opencode.json
│       └── cli/                     # Layer 3 — Frameworks & drivers
│           ├── __init__.py
│           └── main.py              #   argparse dispatcher
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures (tmp paths, fake server)
│   ├── test_domain/
│   │   ├── __init__.py
│   │   └── test_entities.py
│   ├── test_use_cases/
│   │   ├── __init__.py
│   │   ├── test_sync.py
│   │   └── test_list_servers.py
│   └── test_adapters/
│       ├── __init__.py
│       ├── test_lemonade_client.py
│       ├── test_server_registry.py
│       └── test_opencode_config.py
├── main.py                          # Legacy entrypoint (delegates to src)
├── pyproject.toml
├── PRD.md
└── AGENTS.md
```

## Conventions

- **Dependency rule**: inward only. `adapters/` depends on `domain/` and `use_cases/` (by implementing ports). `cli/` depends on `use_cases/`. `domain/` depends on nothing.
- **Tests**: one file per source module under `tests/`, mirroring the `src/` layout.
- **Dataclasses** for domain entities; **Protocol** (or ABC) for ports.
- **No mocks in adapter tests** — use real HTTP fixtures (`responses` lib or `pytest-httpserver`) and temp files.
- **Use case tests** inject fake adapters implementing the ports.

## Output format

The tool writes to `opencode.json` under the top-level `provider` key (singular, matching the opencode docs). Each server becomes one entry with `npm`, `name`, `options.baseURL`, and `models`.

### Model filtering

Only LLM-type chat models are included. The `recipe` field determines inclusion:

| `recipe` | Type | Include? |
|---|---|---|
| `llamacpp` | LLM (text/vision) | ✅ |
| `sd-cpp` | Image generation | ❌ |
| `whispercpp` | Audio transcription | ❌ |
| `kokoro` | Text-to-speech | ❌ |
| `collection.omni` | Composite model | ❌ |

### Display name derivation

The Lemonade API has no separate `name` field. The display name is derived from `id`:
- Strip `user.` prefix (user-installed models)
- Strip `-GGUF` and trailing quantisation tags (`-UD-Q4_K_XL`, `-Q4_K_M`, etc.)
- Strip `-it-` infix for readability (MTP is preserved, it's an important capability flag)

| API `id` | Derived `name` |
|---|---|
| `user.Qwen3.6-27B-GGUF-UD-Q4_K_XL` | `Qwen3.6-27B` |
| `Gemma-4-31B-it-GGUF` | `Gemma-4-31B` |
| `Hermes-4.3-36B-GGUF-Q4_K_M` | `Hermes-4.3-36B` |
| `Qwen3.5-27B-GGUF` | `Qwen3.5-27B` |
| `gpt-oss-120b-mxfp-GGUF` | `gpt-oss-120b-mxfp` |

### Lemonade API → opencode model mapping

| Lemonade API field | opencode mapping |
|---|---|
| `id` | Model key under `provider.<key>.models` |
| `id` (cleaned, see above) | `models.<id>.name` |
| `max_context_window` (if present, > 0) | `models.<id>.limit.context` |
| `labels` contains `"vision"` | `models.<id>.modalities.input: ["text", "image", "pdf"]` |
| `labels` contains `"reasoning"` | `models.<id>.limit.output`: higher cap (e.g. 65536) |
| `labels` contains `"embeddings"`, `"transcription"`, `"tts"`, `"image"` | Skip model entirely |

```json
{
  "provider": {
    "lemonade-desktop": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Lemonade Desktop",
      "options": { "baseURL": "http://192.168.0.20:13305/api/v1" },
      "models": {
        "user.Qwen3.6-27B-GGUF-UD-Q4_K_XL": {
          "name": "Qwen3.6-27B",
          "limit": { "context": 262144, "output": 32768 }
        },
        "Gemma-4-26B-A4B-it-GGUF": {
          "name": "Gemma-4-26B-A4B",
          "limit": { "context": 256000, "output": 128000 },
          "modalities": {
            "input": ["text", "image", "pdf"],
            "output": ["text"]
          }
        }
      }
    }
  }
}
```

Schema reference: https://github.com/opencode-ai/opencode/blob/main/opencode-schema.json

## Tooling

- **Package manager**: `uv`. Run with `uv run python -m opencode_config` or `uv run pytest`.
- **Tests**: `pytest` with `pytest-cov` for coverage. Config in `pyproject.toml`.
- **Dependencies**: `requests` (HTTP), `pytest` / `pytest-cov` (dev).
- **Entry point**: `uv run python -m opencode_config` (via `src/opencode_config/__main__.py`).
- **Lint**: `ruff` (dev dependency). Format check with `ruff check`.
- **PyCharm project** — `.idea/` directory may appear; ignore it.
