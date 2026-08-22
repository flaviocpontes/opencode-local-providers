# AGENTS.md

`occfg` — manages local inference servers (Lemonade, Ollama) and syncs their models into `opencode.json` providers.

## CLI surface

```
occfg server add <host> [--type lemonade|ollama] [--port N] [--name NAME]
occfg server remove <id>
occfg server enable <id>
occfg server disable <id>
occfg server list [--show-all]
occfg sync [-n|--dry-run] [--show-all]
```

Global flags: `--servers <path>`, `--opencode <path>`, `--version`. Defaults: registry at `~/.config/opencode/local-inference-servers.json`; `opencode.json` at `./opencode.json` if present else `~/.config/opencode/opencode.json`. Linux-only.

## Server lifecycle semantics

- **id**: minted at `add` time (slug of `--name`, else slug of host; `-2` suffix on collision). Immutable afterwards — `name` is display-only. Legacy registry entries without ids adopt the old provider-key derivation on the next write.
- **add**: probes the server's models endpoint first; unreachable → nothing written, exit 1. Success → registry entry (`enabled: true`) + seeded provider entry in `opencode.json`.
- **disable**: registry `"enabled": false` + provider `"disabled": true` (models kept; opencode hides it from the picker). Sync skips disabled servers.
- **enable**: flips both flags back. Models refresh on next `occfg sync`.
- **remove**: deletes the registry entry AND the provider entry in one command.
- **sync**: upsert-only refresh of enabled servers. Zero enabled servers → no-op success. Unreachable server → entry left unchanged, exit 1.

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
│       │   ├── list_servers.py      #   Summarise servers & models
│       │   ├── server_management.py #   add/remove/enable/disable use cases
│       │   └── helpers.py           #   chat-model filter, provider entry build
│       ├── adapters/                # Layer 2 — Interface adapters
│       │   ├── __init__.py
│       │   ├── lemonade_client.py   #   HTTP → Lemonade /api/v1/models
│       │   ├── ollama_client.py     #   HTTP → Ollama /api/tags + /api/show
│       │   ├── server_registry.py   #   Read/write local-inference-servers.json
│       │   └── opencode_config.py   #   Read/write opencode.json
│       └── cli/                     # Layer 3 — Frameworks & drivers
│           ├── __init__.py
│           └── main.py              #   argparse subcommand dispatcher
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures (tmp paths, fake server)
│   ├── test_domain/
│   │   ├── __init__.py
│   │   └── test_entities.py
│   ├── test_use_cases/
│   │   ├── __init__.py
│   │   ├── test_sync.py
│   │   ├── test_list_servers.py
│   │   └── test_server_management.py
│   ├── test_adapters/
│   │   ├── __init__.py
│   │   ├── test_lemonade_client.py
│   │   ├── test_ollama_client.py
│   │   ├── test_server_registry.py
│   │   └── test_opencode_config.py
│   ├── test_cli/
│   │   └── test_main.py
│   └── test_e2e/
│       └── test_empty_models.py
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

Only LLM-type chat models are included (Lemonade v11.7.0). The `recipe` field determines inclusion:

| `recipe` | Type | Include? |
|---|---|---|
| `llamacpp` | LLM (text/vision) | ✅ |
| `flm` | LLM (FastFlowLM, NPU) | ✅ |
| `ryzenai-llm` | LLM (ONNX NPU) | ✅ |
| `vllm` | LLM (vLLM GPU, experimental) | ✅ |
| `ollama` | LLM (Ollama servers) | ✅ |
| `sd-cpp` | Image generation | ❌ |
| `whispercpp` | Audio transcription | ❌ |
| `kokoro` | Text-to-speech | ❌ |
| `collection.omni` | Composite model | ❌ |

Labels follow Lemonade's classifier priority: chat-indicator labels (`chat`, `vision`, `reasoning`, `tool-calling`, `tools`, `chat-transcription`) force inclusion; otherwise deployment labels (`embeddings`, `embedding`, `reranking`, `transcription`, `tts`, `image`) exclude the model. So an any-to-text LLM labelled `["vision", ..., "transcription"]` is included, while a pure Whisper model is not.

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
| `labels` contains `"embeddings"`, `"embedding"`, `"reranking"`, `"transcription"`, `"tts"`, `"image"` (and no chat-indicator label) | Skip model entirely |

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

- **Package manager**: `uv`. Run with `uv run occfg …`, `uv run python -m opencode_config`, or `uv run pytest`.
- **Tests**: `pytest` with `pytest-cov` for coverage. Config in `pyproject.toml`.
- **Dependencies**: `httpx` (HTTP), `pytest` / `pytest-cov` / `pytest-httpserver` (dev).
- **Entry points**: `occfg` console script (`[project.scripts]` in pyproject.toml) and `python -m opencode_config`.
- **Lint**: `ruff` (dev dependency). Format check with `ruff check`.
- **PyCharm project** — `.idea/` directory may appear; ignore it.
