"""End-to-end tests: full stack with real HTTP and file I/O.

Each test starts a real pytest-httpserver, creates temp files for the
server registry and opencode config, then exercises the use cases or CLI.
"""

from __future__ import annotations

import json

from pytest_httpserver import HTTPServer

from opencode_config.adapters.lemonade_client import HttpModelServerClient
from opencode_config.adapters.opencode_config import JsonOpenCodeConfig
from opencode_config.adapters.server_registry import JsonServerRegistry
from opencode_config.use_cases.sync import sync_models
from opencode_config.use_cases.list_servers import list_servers


# ── Helpers ────────────────────────────────────────────────────────────

def _api_payload(models: list[dict]) -> dict:
    """Wrap raw model dicts into a /api/v1/models response body."""
    items = []
    for m in models:
        item = {
            "id": m["id"],
            "object": "model",
            "owned_by": "lemonade",
            "recipe": m.get("recipe", "llamacpp"),
            "labels": m.get("labels", []),
            "downloaded": m.get("downloaded", True),
        }
        if "max_context_window" in m:
            item["max_context_window"] = m["max_context_window"]
        if "checkpoint" in m:
            item["checkpoint"] = m["checkpoint"]
        if "size" in m:
            item["size"] = m["size"]
        if "suggested" in m:
            item["suggested"] = m["suggested"]
        if "created" in m:
            item["created"] = m["created"]
        if "image_defaults" in m:
            item["image_defaults"] = m["image_defaults"]
        items.append(item)
    return {"data": items, "object": "list"}


# ── Scenario: empty server registry ────────────────────────────────────

class TestEmptyRegistry:
    def test_no_servers_is_noop(self, server_registry_path, opencode_path):
        """A blank server registry file with no entries."""
        server_registry_path.write_text(json.dumps({"servers": []}) + "\n")
        registry = JsonServerRegistry(server_registry_path)
        client = HttpModelServerClient()
        opencode = JsonOpenCodeConfig(opencode_path)

        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["no enabled servers — nothing to do"]
        assert result.wrote is False
        assert not opencode_path.exists()


# ── Scenario: server has no models ─────────────────────────────────────

class TestServerHasNoModels:
    def test_empty_data_from_single_server(
        self,
        httpserver: HTTPServer,
        server_registry_path,
        opencode_path,
        initial_config,
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(
            {"data": [], "object": "list"}
        )
        server_registry_path.write_text(json.dumps(
            {"servers": [{"host": "localhost", "port": httpserver.port}]}
        ) + "\n")
        opencode_path.write_text(json.dumps(initial_config, indent=2) + "\n")

        registry = JsonServerRegistry(server_registry_path)
        client = HttpModelServerClient()
        opencode = JsonOpenCodeConfig(opencode_path)

        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["localhost: 0 models"]

        config = json.loads(opencode_path.read_text())
        assert config["provider"]["ollama"] == initial_config["provider"]["ollama"]
        assert config["provider"]["localhost"]["models"] == {}


# ── Scenario: single server with mixed models ──────────────────────────

class TestSingleServerMixedModels:
    def test_chat_models_included_non_chat_skipped(
        self, httpserver: HTTPServer, server_registry_path, opencode_path
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(
            _api_payload([
                {"id": "llm-1", "max_context_window": 131072},
                {"id": "vision-m", "max_context_window": 262144,
                 "labels": ["vision"]},
                {"id": "reason-m", "max_context_window": 131072,
                 "labels": ["reasoning"]},
                {"id": "img-gen", "recipe": "sd-cpp", "labels": ["image"]},
                {"id": "whisper", "recipe": "whispercpp",
                 "labels": ["transcription"]},
                {"id": "tts", "recipe": "kokoro", "labels": ["tts"]},
            ])
        )
        server_registry_path.write_text(json.dumps(
            {"servers": [{"host": "localhost", "port": httpserver.port,
                          "name": "My Server"}]}
        ) + "\n")

        registry = JsonServerRegistry(server_registry_path)
        client = HttpModelServerClient()
        opencode = JsonOpenCodeConfig(opencode_path)

        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["my-server: 3 models"]

        config = json.loads(opencode_path.read_text())
        models = config["provider"]["my-server"]["models"]
        assert list(models.keys()) == ["llm-1", "vision-m", "reason-m"]

        # Verify vision model has modalities
        assert "modalities" in models["vision-m"]
        assert models["vision-m"]["modalities"]["input"] == ["text", "image", "pdf"]

        # Verify reasoning model has output limit
        assert models["reason-m"]["limit"]["output"] == 65536

        # Non-chat models excluded
        assert "img-gen" not in models
        assert "whisper" not in models
        assert "tts" not in models


# ── Scenario: multiple servers ─────────────────────────────────────────

class TestMultipleServers:
    def test_two_servers_each_with_models(
        self, httpserver: HTTPServer, server_registry_path, opencode_path
    ):
        # First server: has models
        httpserver.expect_request("/api/v1/models").respond_with_json(
            _api_payload([
                {"id": "server1-model", "max_context_window": 131072},
            ])
        )
        # We need a second port; since pytest-httpserver is single-port,
        # we use the same server for both (simulating same host:port)
        # In a real multi-server scenario they'd be on different ports.
        server_registry_path.write_text(json.dumps({
            "servers": [
                {"host": "localhost", "port": httpserver.port,
                 "name": "Server Alpha"},
                {"host": "localhost", "port": httpserver.port,
                 "name": "Server Beta"},
            ]
        }) + "\n")

        registry = JsonServerRegistry(server_registry_path)
        client = HttpModelServerClient()
        opencode = JsonOpenCodeConfig(opencode_path)

        result = sync_models(registry, {"lemonade": client}, opencode)
        assert set(result.summary) == {"server-alpha: 1 models", "server-beta: 1 models"}

        config = json.loads(opencode_path.read_text())
        assert "server-alpha" in config["provider"]
        assert "server-beta" in config["provider"]


# ── Scenario: list_servers end-to-end ──────────────────────────────────

class TestListServersE2E:
    def test_list_servers_with_models(
        self, httpserver: HTTPServer, server_registry_path
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(
            _api_payload([
                {"id": "chat-model", "max_context_window": 131072},
                {"id": "image-gen", "recipe": "sd-cpp", "labels": ["image"]},
            ])
        )
        server_registry_path.write_text(json.dumps({
            "servers": [{"host": "localhost", "port": httpserver.port,
                          "name": "My Server"}]
        }) + "\n")

        registry = JsonServerRegistry(server_registry_path)
        client = HttpModelServerClient()
        result = list_servers(registry, {"lemonade": client})

        assert len(result) == 1
        assert result[0]["name"] == "My Server"
        assert len(result[0]["models"]) == 1
        assert result[0]["models"][0].id == "chat-model"


# ── Scenario: preserve existing opencode config ────────────────────────

class TestPreserveExistingConfig:
    def test_existing_providers_untouched(
        self,
        httpserver: HTTPServer,
        server_registry_path,
        opencode_path,
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(
            _api_payload([{"id": "new-model", "max_context_window": 65536}])
        )
        server_registry_path.write_text(json.dumps({
            "servers": [{"host": "localhost", "port": httpserver.port,
                          "name": "NewServer"}]
        }) + "\n")
        opencode_path.write_text(json.dumps({
            "$schema": "https://opencode.ai/config.json",
            "model": "existing/model",
            "provider": {
                "existing": {
                    "name": "Existing",
                    "npm": "@ai-sdk/openai-compatible",
                    "options": {"baseURL": "http://existing:11434/v1"},
                    "models": {"old-m": {"name": "old-m"}},
                }
            },
            "permission": {"bash": "ask"},
        }) + "\n")

        registry = JsonServerRegistry(server_registry_path)
        client = HttpModelServerClient()
        opencode = JsonOpenCodeConfig(opencode_path)
        sync_models(registry, {"lemonade": client}, opencode)

        config = json.loads(opencode_path.read_text())
        assert config["$schema"] == "https://opencode.ai/config.json"
        assert config["model"] == "existing/model"
        assert config["permission"]["bash"] == "ask"
        assert config["provider"]["existing"]["name"] == "Existing"
        assert "newserver" in config["provider"]
