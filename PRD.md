# PRD: Lemonade → OpenCode Provider Sync

## Problem

Running opencode against local LLMs via a Lemonade Server requires manually maintaining the `provider` section in `opencode.json`. Every time a model is pulled, loaded, or removed on the server, the user must update the config by hand — model IDs, display names, context windows, and capability labels all need to stay in sync.

## Goal

A single-command CLI tool that queries one or more Lemonade Servers' `GET /api/v1/models` endpoint and writes the resulting models into `opencode.json` as properly configured OpenAI-compatible providers.

## Functional Requirements

### 1. Query Lemonade Server

- **Source**: `GET /api/v1/models` on each configured server.
- **Filter**: Respect the `downloaded` field from the API; only include models where `downloaded == true` by default. Flag `--show-all` to include undownloaded models.

### 2. Server registry config file

Instead of passing servers via CLI flags, the user maintains a list of lemonade servers in a separate config file (default: `~/.config/opencode/lemonade-servers.json`).

**Format**:
```json
{
  "servers": [
    { "host": "192.168.0.20", "port": 13305, "name": "Lemonade Big" },
    { "host": "192.168.0.19", "port": 13305, "name": "Lemonade Small" }
  ]
}
```

- `host` and `port` are required. Port defaults to `13305` if omitted.
- `name` is optional; if omitted, the provider key and display name are auto-derived from the host.
- Path override via `--servers PATH` flag.

### 3. Translate servers to opencode provider entries

Each server in the registry becomes one provider entry. The provider key is derived from `name` (slugified lowercase, spaces → hyphens) or from `host` if no name is given.

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
- Strip `-it-`, `-MTP-` infixes for readability

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

- **Provider block**:
  - `npm`: `"@ai-sdk/openai-compatible"`
  - `name`: the `name` field from the server registry entry (or a human-readable name derived from host).
  - `options.baseURL`: `http://{host}:{port}/api/v1`.

**Output example** (under `opencode.json` top-level `provider` key, singular):
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

### 4. Output modes

| Mode | Flag | Behaviour |
|---|---|---|
| **Write** (default) | *(none)* | Read existing `opencode.json`, merge/overwrite providers for each server, write back. |
| **Dry-run** | `--dry-run`, `-n` | Print the generated JSON to stdout; do not modify any file. |
| **Print servers** | `--list-servers`, `-l` | Print the server registry and the models found on each, then exit. |
| **Init servers** | `--init-servers` | Create a default `lemonade-servers.json` in the config directory if none exists. |

### 5. Config file targeting

- Default: write to `./opencode.json` (project-level).
- Fallback if file does not exist: `~/.config/opencode/opencode.json` (global).
- Explicit path: `--opencode PATH`.

### 6. Preserve existing config

- Only touch `provider` entries whose key matches one of the derived server keys.
- All other keys (`model`, `small_model`, `enabled_providers`, other providers, etc.) must be preserved verbatim.
- If the target file does not exist, create it from scratch with only the new provider blocks.

### 7. Error handling

- Server unreachable → clear error message with connection hint.
- No models returned → warn and exit cleanly.
- Invalid JSON in existing config → abort with parse error details.

## Non-functional Requirements

- **Zero runtime dependencies** (stdlib only: `json`, `urllib.request`, `argparse`, `os`, `sys`).
- **Runs on Python 3.10+**.
- **Idempotent** — running twice produces the same result (provided the server state hasn't changed).
- **Follows the existing project conventions**: single module (`main.py`), managed by `uv`.

## CLI Interface

```
usage: uv run main.py [options]

Query all lemonade servers from the registry and sync models into opencode.json.

options:
  --servers PATH           Lemonade server registry file
                            [default: ~/.config/opencode/lemonade-servers.json]
  --opencode PATH          Target opencode config file
                            [default: ./opencode.json or ~/.config/opencode/opencode.json]
  --show-all               Include models that are not downloaded
  -l, --list-servers       Print server registry with model summaries and exit
  --init-servers           Create a default server registry file and exit
  -n, --dry-run            Print generated config to stdout, don't write
  --version                Show version and exit
```

## Examples

```bash
# First-time setup — create the server registry
$ uv run main.py --init-servers
✗ No server registry found at ~/.config/opencode/lemonade-servers.json
  Created default file — edit it with your server addresses and re-run.

# After editing lemonade-servers.json:
$ uv run main.py
✓ Fetched 3 models from Lemonade Desktop (192.168.0.20:13305)
✓ Fetched 5 models from Lemonade Laptop (192.168.0.7:13305)
✓ Updated providers in ./opencode.json
  Added: lemonade-desktop, lemonade-laptop

# Preview changes without writing
$ uv run main.py -n
--- opencode.json (dry-run) ---
{
  "provider": {
    "lemonade-desktop": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Lemonade Desktop",
      "options": { "baseURL": "http://192.168.0.20:13305/api/v1" },
      "models": { ... }
    },
    "lemonade-laptop": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Lemonade Laptop",
      "options": { "baseURL": "http://192.168.0.7:13305/api/v1" },
      "models": { ... }
    }
  }
}

# List servers and their models
$ uv run main.py -l
Lemonade Desktop (192.168.0.20:13305)
  Llama-3.2-1B-Instruct-Hybrid  128K  ✓
  DeepSeek-R1-Distill-Qwen-7B   128K  ✓  reasoning
Lemonade Laptop (192.168.0.7:13305)
  Llama-3.2-3B-Instruct         128K  ✓
  Qwen2.5-7B-Instruct           128K  ✓
  nomic-embed-text-v1.5         2048  ✓  embeddings
```

## Out of Scope

- Managing lemonade models (pull, delete, load/unload) — use `lemonade` CLI or the Lemonade API directly.
- Automatic re-sync on server changes (daemon/watch mode).
- Non-OpenAI-compatible endpoints (e.g., Anthropic native, Google AI).
