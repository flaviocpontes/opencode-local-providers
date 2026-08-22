# opencode_config

Syncs models from [Lemonade Server](https://lemonade-server.ai/) (and Ollama) instances into your [opencode](https://opencode.ai/) config, so local models show up as opencode providers.

## Install

Requires Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev   # or: uv sync for runtime deps only
```

## Quick start

```bash
# 1. Create the server registry (refuses to overwrite an existing one)
uv run python -m opencode_config --init-servers

# 2. Edit ~/.config/opencode/local-inference-servers.json with your hosts

# 3. Preview what would be written
uv run python -m opencode_config -n

# 4. Write opencode.json
uv run python -m opencode_config
```

## Server registry

`~/.config/opencode/local-inference-servers.json` (override with `--servers`):

```json
{
  "servers": [
    { "host": "192.168.0.20", "port": 13305, "name": "Lemonade Desktop" },
    { "host": "192.168.0.30", "type": "ollama", "name": "Ollama Box" },
    { "host": "192.168.0.99", "name": "Old Server", "enabled": false }
  ]
}
```

| Field | Default | Notes |
|---|---|---|
| `host` | required | IP or hostname |
| `port` | `13305` (lemonade) / `11434` (ollama) | |
| `name` | derived from `host` | Also becomes the provider key (slugified) |
| `type` | `lemonade` | `lemonade` or `ollama` |
| `enabled` | `true` | Set `false` to skip a server without deleting it |

## Commands

Run from the project root with `uv run python -m opencode_config` (or `uv run main.py`).

| Command | What it does |
|---|---|
| *(no flags)* | Sync all enabled servers into `opencode.json` |
| `-n`, `--dry-run` | Print the generated `provider` block to stdout, don't write |
| `-l`, `--list-servers` | Show each server with its models, context window, and labels |
| `--init-servers` | Create a starter registry file |
| `--show-all` | Include models not yet downloaded on the server |
| `--servers PATH` | Use a different registry file |
| `--opencode PATH` | Write to a different opencode config |
| `--version` | Print version |

Target file resolution: `./opencode.json` if it exists, else `~/.config/opencode/opencode.json`.

## What gets synced

Each server becomes one entry under the top-level `provider` key (singular, per the [opencode schema](https://github.com/opencode-ai/opencode/blob/main/opencode-schema.json)):

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
        }
      }
    }
  }
}
```

Only LLM chat models are included (rules follow Lemonade v11.7.0):

- **Included recipes**: `llamacpp`, `flm`, `ryzenai-llm`, `vllm` (Lemonade); `ollama` (Ollama)
- **Excluded recipes**: `sd-cpp` (image), `whispercpp` (ASR), `kokoro` (TTS), `collection.omni` (composite)
- **Labels**: chat-indicator labels (`chat`, `vision`, `reasoning`, `tool-calling`, `tools`, `chat-transcription`) force inclusion; otherwise deployment labels (`embeddings`, `embedding`, `reranking`, `transcription`, `tts`, `image`) exclude the model
- Unreachable servers are reported and skipped — their existing entries in `opencode.json` are left untouched
- Other providers and keys in `opencode.json` are preserved; re-running only rewrites entries for servers in the registry

Per-model mapping:

| Server reports | opencode gets |
|---|---|
| `max_context_window` | `limit.context` |
| `reasoning` label | `limit.output: 65536` (else `32768`) |
| `vision` label | `modalities.input: ["text", "image", "pdf"]` |

## Development

```bash
uv run pytest          # tests + coverage
uv run ruff check      # lint
```

Clean Architecture layout: `domain/` (entities, ports) ← `use_cases/` (sync, list) ← `adapters/` (HTTP clients, registries) ← `cli/`. Dependencies point inward only. See `AGENTS.md` for conventions.
