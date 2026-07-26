from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest
from pytest_httpserver import HTTPServer

from opencode_config.adapters.server_registry import JsonServerRegistry
from opencode_config.adapters.opencode_config import JsonOpenCodeConfig
from opencode_config.domain.entities import Server, Model


# ── Shared model fixtures (mirrors real Lemonade API data) ──────────────

@pytest.fixture
def llm_model() -> Model:
    return Model(id="GLM-4.7-Flash-GGUF", max_context_window=202752,
                 labels=["tool-calling"], recipe="llamacpp",
                 checkpoint="ggml-org/GLM-4.7-Flash-GGUF:Q4_K_M",
                 size=3.61, downloaded=True, suggested=True, created=1744173590)


@pytest.fixture
def vision_model() -> Model:
    return Model(id="Gemma-4-31B-it-GGUF", max_context_window=262144,
                 labels=["tool-calling", "vision"], recipe="llamacpp",
                 checkpoint="ggml-org/gemma-3-4b-it-GGUF:Q4_K_M",
                 size=3.61, downloaded=True, suggested=True, created=1744173590)


@pytest.fixture
def reasoning_model() -> Model:
    return Model(id="gpt-oss-120b-mxfp-GGUF", max_context_window=131072,
                 labels=["reasoning", "tool-calling"], recipe="llamacpp",
                 size=6.8, downloaded=True, suggested=True, created=1744173590)


@pytest.fixture
def user_model() -> Model:
    return Model(id="user.Qwen3.6-27B-GGUF-UD-Q4_K_XL", max_context_window=262144,
                 labels=["tool-calling"], recipe="llamacpp",
                 downloaded=True, created=1744173590)


@pytest.fixture
def image_model() -> Model:
    return Model(id="Flux-2-Klein-4B", labels=["image", "edit"], recipe="sd-cpp",
                 size=5.2, downloaded=True, suggested=True, created=1744173590,
                 image_defaults={"steps": 4, "cfg_scale": 1.0, "width": 512, "height": 512})


@pytest.fixture
def tts_model() -> Model:
    return Model(id="kokoro-v1", labels=["tts"], recipe="kokoro",
                 downloaded=True, created=1744173590)


@pytest.fixture
def transcription_model() -> Model:
    return Model(id="Whisper-Large-v3-Turbo", labels=["transcription"], recipe="whispercpp",
                 downloaded=True, created=1744173590)


@pytest.fixture
def composite_model() -> Model:
    return Model(id="LMX-Omni-52B-Halo", labels=[], recipe="collection.omni",
                 downloaded=True, created=1744173590)


@pytest.fixture
def mixed_models(
    llm_model, vision_model, reasoning_model, user_model,
    image_model, tts_model, transcription_model, composite_model,
) -> list[Model]:
    """All model types in one list — 4 chat + 4 non-chat."""
    return [
        llm_model, vision_model, reasoning_model, user_model,
        image_model, tts_model, transcription_model, composite_model,
    ]


# ── Server fixtures ────────────────────────────────────────────────────

@pytest.fixture
def a_server() -> Server:
    return Server(host="192.168.0.20", port=13305, name="Lemonade Desktop")


@pytest.fixture
def another_server() -> Server:
    return Server(host="192.168.0.7", port=13305, name="Lemonade Laptop")


# ── Temp file fixtures ─────────────────────────────────────────────────

@pytest.fixture
def server_registry_path(tmp_path: Path) -> Path:
    return tmp_path / "lemonade-servers.json"


@pytest.fixture
def opencode_path(tmp_path: Path) -> Path:
    return tmp_path / "opencode.json"


@pytest.fixture
def make_server_registry(
    server_registry_path: Path,
    httpserver: HTTPServer,
) -> Callable[[list[dict]], JsonServerRegistry]:
    """Create a server registry file where each entry has host=localhost
    and port matching the test HTTPServer."""

    def _make(entries: list[dict]) -> JsonServerRegistry:
        data = []
        for e in entries:
            entry = {"host": "localhost", "port": httpserver.port}
            if "name" in e:
                entry["name"] = e["name"]
            data.append(entry)
        server_registry_path.write_text(
            json.dumps({"servers": data}, indent=2) + "\n"
        )
        return JsonServerRegistry(server_registry_path)

    return _make


@pytest.fixture
def make_server_registry_raw(server_registry_path: Path) -> Callable[[list[dict]], JsonServerRegistry]:
    """Create a server registry file using explicit host/port values."""

    def _make(entries: list[dict]) -> JsonServerRegistry:
        server_registry_path.write_text(
            json.dumps({"servers": entries}, indent=2) + "\n"
        )
        return JsonServerRegistry(server_registry_path)

    return _make


@pytest.fixture
def make_opencode_config(opencode_path: Path) -> Callable[[dict], JsonOpenCodeConfig]:
    """Create an opencode config file with initial content."""

    def _make(config: dict) -> JsonOpenCodeConfig:
        opencode_path.write_text(json.dumps(config, indent=2) + "\n")
        return JsonOpenCodeConfig(opencode_path)

    return _make


@pytest.fixture
def initial_config() -> dict:
    return {
        "$schema": "https://opencode.ai/config.json",
        "model": "some/existing-model",
        "provider": {
            "ollama": {
                "name": "Ollama",
                "npm": "@ai-sdk/openai-compatible",
                "options": {"baseURL": "http://localhost:11434/v1"},
                "models": {
                    "qwen3.5:9b": {
                        "name": "qwen3.5:9b",
                        "limit": {"context": 262144, "output": 32768},
                    }
                },
            }
        },
        "permission": {"bash": "ask", "read": "allow"},
    }


# ── HTTP handler fixtures ──────────────────────────────────────────────

@pytest.fixture
def empty_models_handler(httpserver: HTTPServer) -> None:
    """Register /api/v1/models to return an empty list."""
    httpserver.expect_request("/api/v1/models").respond_with_json(
        {"data": [], "object": "list"}
    )


def _api_payload(models: list[Model]) -> dict:
    """Build a real-looking /api/v1/models response body."""
    items = []
    for m in models:
        item: dict = {"id": m.id, "object": "model", "owned_by": "lemonade",
                      "recipe": m.recipe, "labels": list(m.labels),
                      "downloaded": m.downloaded}
        if m.max_context_window is not None:
            item["max_context_window"] = m.max_context_window
        if m.checkpoint is not None:
            item["checkpoint"] = m.checkpoint
        if m.size is not None:
            item["size"] = m.size
        if m.suggested:
            item["suggested"] = True
        if m.created is not None:
            item["created"] = m.created
        if m.image_defaults is not None:
            item["image_defaults"] = m.image_defaults
        items.append(item)
    return {"data": items, "object": "list"}


@pytest.fixture
def models_handler(httpserver: HTTPServer, mixed_models: list[Model]) -> None:
    """Register /api/v1/models to return the mixed_models payload."""
    httpserver.expect_request("/api/v1/models").respond_with_json(
        _api_payload(mixed_models)
    )
