import re

from opencode_config.domain.entities import Model


SKIP_LABELS = {"embeddings", "transcription", "tts", "image"}
CHAT_RECIPES = {"llamacpp"}


def is_chat_model(model: Model) -> bool:
    if model.recipe not in CHAT_RECIPES:
        return False
    if SKIP_LABELS & set(model.labels):
        return False
    return True


JUNK_COMPOUNDS = [
    r"Claude-[\d.]+-Opus",
]
JUNK_TOKENS = {"Thinking", "NEO-CODE", "Di", "IMatrix", "MAX"}


def derive_display_name(model_id: str) -> str:
    name = model_id
    name = re.sub(r"^user\.", "", name)
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
