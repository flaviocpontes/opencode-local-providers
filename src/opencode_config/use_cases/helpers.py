import re

from opencode_config.domain.entities import Server, Model


# Mirrors Lemonade v11.7.0 model_types.h: chat-indicator labels beat deployment labels,
# so an any-to-text LLM labelled ["vision", ..., "transcription"] is still chat.
CHAT_LABELS = {"chat", "vision", "reasoning", "tool-calling", "tools", "chat-transcription"}
SKIP_LABELS = {"embeddings", "embedding", "reranking", "transcription", "tts", "image"}
CHAT_RECIPES = {"llamacpp", "flm", "ryzenai-llm", "vllm", "ollama"}


def is_chat_model(model: Model) -> bool:
    if model.recipe not in CHAT_RECIPES:
        return False
    labels = set(model.labels)
    if CHAT_LABELS & labels:
        return True
    return not (SKIP_LABELS & labels)


JUNK_COMPOUNDS = [
    r"Claude-[\d.]+-Opus",
]
JUNK_TOKENS = {"Thinking", "NEO-CODE", "Di", "IMatrix", "MAX"}


def derive_display_name(model_id: str) -> str:
    name = re.sub(r"^user\.", "", model_id)
    name = re.sub(r":latest$", "", name)
    name = name.replace("-it-", "-")
    name = re.sub(r"-GGUF.*$", "", name)
    for pattern in JUNK_COMPOUNDS:
        name = re.sub(rf"-?{pattern}-?", "-", name)
    for token in sorted(JUNK_TOKENS, key=len, reverse=True):
        name = re.sub(rf"-?{re.escape(token)}-?", "-", name)
    name = re.sub(r"-{2,}", "-", name)
    name = name.strip("-")
    return name


def model_to_entry(model: Model) -> dict:
    entry: dict = {"name": derive_display_name(model.id)}
    limits: dict = {}
    if model.max_context_window and model.max_context_window > 0:
        limits["context"] = model.max_context_window
    labels = set(model.labels)
    if "vision" in labels:
        entry["modalities"] = {
            "input": ["text", "image", "pdf"],
            "output": ["text"],
        }
    if "reasoning" in labels:
        limits["output"] = 65536
    else:
        limits["output"] = 32768
    entry["limit"] = limits
    return entry


BASE_URL_PATHS = {"lemonade": "/api/v1", "ollama": "/v1"}


def build_provider_entry(server: Server, models: list[Model], show_all: bool = False):
    """Shared by sync and server add: one provider entry dict + warnings."""
    chat_models = [
        m for m in models
        if is_chat_model(m) and (show_all or m.downloaded)
    ]
    warnings = [
        f"{m.id}: context {m.max_context_window} < 65536 (opencode wants 64k+)"
        for m in chat_models
        if m.max_context_window and m.max_context_window < 65536
    ]
    entry = {
        "npm": "@ai-sdk/openai-compatible",
        "name": server.name or f"{server.type.capitalize()} ({server.host})",
        "options": {
            "baseURL": f"http://{server.host}:{server.port}{BASE_URL_PATHS[server.type]}"
        },
        "models": {m.id: model_to_entry(m) for m in chat_models},
    }
    return entry, warnings
