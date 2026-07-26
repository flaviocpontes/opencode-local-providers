"""Use case tests for sync — inject fake adapters (Protocols)."""

from opencode_config.domain.entities import Server, Model
from opencode_config.use_cases.sync import sync_models


# ── Fake adapters ──────────────────────────────────────────────────────

class FakeServerRegistry:
    def __init__(self, servers: list[Server] | None = None):
        self._servers = servers or []

    def load_servers(self) -> list[Server]:
        return self._servers


class FakeLemonadeClient:
    def __init__(self, models: list[Model] | None = None):
        self._models = models or []

    def fetch_models(self, server: Server) -> list[Model]:
        return self._models


class FakeOpenCodeConfig:
    def __init__(self, initial: dict | None = None):
        self._config = initial or {}
        self.written: dict | None = None

    def load_config(self) -> dict:
        return self._config

    def write_config(self, config: dict) -> None:
        self.written = config


# ── Tests ──────────────────────────────────────────────────────────────

class TestSyncModels:
    def test_no_servers(self):
        registry = FakeServerRegistry([])
        client = FakeLemonadeClient()
        opencode = FakeOpenCodeConfig({})
        results = sync_models(registry, client, opencode)
        assert results == []
        assert opencode.written == {"provider": {}}

    def test_single_server_no_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        client = FakeLemonadeClient([])
        opencode = FakeOpenCodeConfig({})
        results = sync_models(registry, client, opencode)
        assert results == ["desktop: 0 models"]
        assert opencode.written["provider"]["desktop"]["models"] == {}

    def test_single_server_with_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        client = FakeLemonadeClient([
            Model(id="m1", max_context_window=131072, recipe="llamacpp"),
            Model(id="m2", max_context_window=262144, recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        results = sync_models(registry, client, opencode)
        assert results == ["desktop: 2 models"]
        prov = opencode.written["provider"]["desktop"]
        assert prov["name"] == "Desktop"
        assert len(prov["models"]) == 2

    def test_filters_non_chat_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305),
        ])
        client = FakeLemonadeClient([
            Model(id="llm", recipe="llamacpp"),
            Model(id="img", recipe="sd-cpp", labels=["image"]),
            Model(id="tts", recipe="kokoro", labels=["tts"]),
        ])
        opencode = FakeOpenCodeConfig({})
        results = sync_models(registry, client, opencode)
        assert results == ["192.168.0.20: 1 models"]
        assert "llm" in opencode.written["provider"]["192.168.0.20"]["models"]
        assert "img" not in opencode.written["provider"]["192.168.0.20"]["models"]

    def test_preserves_existing_providers(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        client = FakeLemonadeClient([
            Model(id="llm-1", recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({
            "provider": {
                "ollama": {
                    "name": "Ollama",
                    "models": {"m": {"name": "m"}},
                }
            }
        })
        sync_models(registry, client, opencode)
        assert "ollama" in opencode.written["provider"]
        assert opencode.written["provider"]["ollama"]["name"] == "Ollama"
        assert "desktop" in opencode.written["provider"]

    def test_multiple_servers(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
            Server(host="192.168.0.7", port=13305, name="Laptop"),
        ])
        client = FakeLemonadeClient([
            Model(id="shared-model", recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        results = sync_models(registry, client, opencode)
        assert set(results) == {"desktop: 1 models", "laptop: 1 models"}
        assert "desktop" in opencode.written["provider"]
        assert "laptop" in opencode.written["provider"]

    def test_vision_model_gets_modalities(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeLemonadeClient([
            Model(id="vision-m", max_context_window=131072,
                  labels=["vision"], recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, client, opencode)
        entry = opencode.written["provider"]["test"]["models"]["vision-m"]
        assert "modalities" in entry
        assert "input" in entry["modalities"]

    def test_reasoning_model_gets_output_limit(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeLemonadeClient([
            Model(id="reason-m", max_context_window=131072,
                  labels=["reasoning"], recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, client, opencode)
        entry = opencode.written["provider"]["test"]["models"]["reason-m"]
        assert entry["limit"]["output"] == 65536
