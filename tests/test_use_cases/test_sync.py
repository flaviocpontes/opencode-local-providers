"""Use case tests for sync — inject fake adapters (Protocols)."""

from opencode_config.domain.entities import Server, Model
from opencode_config.domain.ports import ServerError
from opencode_config.use_cases.sync import sync_models


# ── Fake adapters ──────────────────────────────────────────────────────

class FakeServerRegistry:
    def __init__(self, servers: list[Server] | None = None):
        self._servers = servers or []

    def load_servers(self) -> list[Server]:
        return self._servers

    def add_server(self, server: Server) -> Server:
        from dataclasses import replace
        return replace(server, id=server.id or server.host)

    def remove_server(self, server_id: str) -> bool:
        return False

    def set_enabled(self, server_id: str, enabled: bool) -> bool:
        return False


class FakeModelServerClient:
    def __init__(self, models: list[Model] | None = None):
        self._models = models or []

    def fetch_models(self, server: Server) -> list[Model]:
        return self._models


class FlakyModelServerClient:
    """Raises ServerError for one host, returns models for the rest."""

    def __init__(self, bad_host: str, models: list[Model]):
        self._bad_host = bad_host
        self._models = models

    def fetch_models(self, server: Server) -> list[Model]:
        if server.host == self._bad_host:
            raise ServerError(server.name or server.host, "connection refused")
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
    def test_no_servers_is_noop_success(self):
        registry = FakeServerRegistry([])
        client = FakeModelServerClient()
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["no enabled servers — nothing to do"]
        assert result.wrote is False
        assert opencode.written is None

    def test_all_disabled_is_noop_success(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", name="Off", enabled=False),
        ])
        client = FakeModelServerClient([Model(id="m1", recipe="llamacpp")])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["no enabled servers — nothing to do"]
        assert opencode.written is None
        assert result.failures == []

    def test_disabled_server_skipped_enabled_synced(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", name="Off", enabled=False),
            Server(host="192.168.0.7", name="On"),
        ])
        client = FakeModelServerClient([Model(id="m1", recipe="llamacpp")])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["on: 1 models"]
        assert "off" not in opencode.written["provider"]

    def test_server_id_is_provider_key(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", name="Renamed", id="stable-id"),
        ])
        client = FakeModelServerClient([Model(id="m1", recipe="llamacpp")])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"lemonade": client}, opencode)
        assert "stable-id" in opencode.written["provider"]
        assert opencode.written["provider"]["stable-id"]["name"] == "Renamed"

    def test_single_server_no_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        client = FakeModelServerClient([])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["desktop: 0 models"]
        assert opencode.written["provider"]["desktop"]["models"] == {}

    def test_single_server_with_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        client = FakeModelServerClient([
            Model(id="m1", max_context_window=131072, recipe="llamacpp"),
            Model(id="m2", max_context_window=262144, recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["desktop: 2 models"]
        prov = opencode.written["provider"]["desktop"]
        assert prov["name"] == "Desktop"
        assert len(prov["models"]) == 2

    def test_filters_non_chat_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305),
        ])
        client = FakeModelServerClient([
            Model(id="llm", recipe="llamacpp"),
            Model(id="img", recipe="sd-cpp", labels=["image"]),
            Model(id="tts", recipe="kokoro", labels=["tts"]),
        ])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert result.summary == ["192.168.0.20: 1 models"]
        assert "llm" in opencode.written["provider"]["192.168.0.20"]["models"]
        assert "img" not in opencode.written["provider"]["192.168.0.20"]["models"]

    def test_preserves_existing_providers(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        client = FakeModelServerClient([
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
        sync_models(registry, {"lemonade": client}, opencode)
        assert "ollama" in opencode.written["provider"]
        assert opencode.written["provider"]["ollama"]["name"] == "Ollama"
        assert "desktop" in opencode.written["provider"]

    def test_multiple_servers(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
            Server(host="192.168.0.7", port=13305, name="Laptop"),
        ])
        client = FakeModelServerClient([
            Model(id="shared-model", recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert set(result.summary) == {"desktop: 1 models", "laptop: 1 models"}
        assert "desktop" in opencode.written["provider"]
        assert "laptop" in opencode.written["provider"]

    def test_vision_model_gets_modalities(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([
            Model(id="vision-m", max_context_window=131072,
                  labels=["vision"], recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"lemonade": client}, opencode)
        entry = opencode.written["provider"]["test"]["models"]["vision-m"]
        assert "modalities" in entry
        assert "input" in entry["modalities"]

    def test_reasoning_model_gets_output_limit(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([
            Model(id="reason-m", max_context_window=131072,
                  labels=["reasoning"], recipe="llamacpp"),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"lemonade": client}, opencode)
        entry = opencode.written["provider"]["test"]["models"]["reason-m"]
        assert entry["limit"]["output"] == 65536

    def test_dry_run_writes_nothing(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([Model(id="m1", recipe="llamacpp")])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode, dry_run=True)
        assert opencode.written is None
        assert result.summary == ["test: 1 models"]
        assert result.config["provider"]["test"]["models"]["m1"]["name"] == "m1"

    def test_default_filters_undownloaded(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([
            Model(id="have", recipe="llamacpp", downloaded=True),
            Model(id="want", recipe="llamacpp", downloaded=False),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"lemonade": client}, opencode)
        models = opencode.written["provider"]["test"]["models"]
        assert "have" in models
        assert "want" not in models

    def test_show_all_includes_undownloaded(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([
            Model(id="have", recipe="llamacpp", downloaded=True),
            Model(id="want", recipe="llamacpp", downloaded=False),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"lemonade": client}, opencode, show_all=True)
        models = opencode.written["provider"]["test"]["models"]
        assert "have" in models
        assert "want" in models

    def test_show_all_still_excludes_non_chat(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([
            Model(id="llm", recipe="llamacpp", downloaded=False),
            Model(id="img", recipe="sd-cpp", labels=["image"], downloaded=False),
        ])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"lemonade": client}, opencode, show_all=True)
        models = opencode.written["provider"]["test"]["models"]
        assert "llm" in models
        assert "img" not in models

    def test_dead_server_skipped_others_synced(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Dead"),
            Server(host="192.168.0.7", port=13305, name="Alive"),
        ])
        client = FlakyModelServerClient(
            "192.168.0.20", [Model(id="m1", recipe="llamacpp")]
        )
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)

        assert result.failures == [("Dead", "connection refused")]
        assert result.summary == ["alive: 1 models"]
        assert "alive" in opencode.written["provider"]
        assert "dead" not in opencode.written["provider"]

    def test_dead_server_stale_entry_preserved(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Dead"),
        ])
        client = FlakyModelServerClient("192.168.0.20", [])
        stale = {"name": "Dead", "models": {"old-m": {"name": "old-m"}}}
        opencode = FakeOpenCodeConfig({"provider": {"dead": stale}})
        result = sync_models(registry, {"lemonade": client}, opencode)

        assert len(result.failures) == 1
        assert opencode.written["provider"]["dead"] is stale

    def test_all_servers_dead_still_writes_config(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Dead"),
        ])
        client = FlakyModelServerClient("192.168.0.20", [])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)

        assert len(result.failures) == 1
        assert opencode.written == {"provider": {}}


class TestSyncModelsOllama:
    def test_mixed_registry_writes_both_entries(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop",
                   type="lemonade"),
            Server(host="192.168.0.30", port=11434, name="Ollama Box",
                   type="ollama"),
        ])
        lemonade = FakeModelServerClient([Model(id="m1", recipe="llamacpp")])
        ollama = FakeModelServerClient(
            [Model(id="gemma4:latest", recipe="ollama",
                   max_context_window=131072)])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(
            registry, {"lemonade": lemonade, "ollama": ollama}, opencode)

        assert set(result.summary) == {"desktop: 1 models", "ollama-box: 1 models"}
        providers = opencode.written["provider"]
        assert providers["desktop"]["options"]["baseURL"] == \
            "http://192.168.0.20:13305/api/v1"
        assert providers["ollama-box"]["options"]["baseURL"] == \
            "http://192.168.0.30:11434/v1"
        assert providers["ollama-box"]["models"]["gemma4:latest"]["name"] == "gemma4"

    def test_ollama_fallback_provider_name(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.30", type="ollama"),
        ])
        client = FakeModelServerClient([Model(id="m1", recipe="ollama")])
        opencode = FakeOpenCodeConfig({})
        sync_models(registry, {"ollama": client}, opencode)
        assert opencode.written["provider"]["192.168.0.30"]["name"] == \
            "Ollama (192.168.0.30)"

    def test_sub_64k_model_warns_and_is_included(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.30", name="Box", type="ollama"),
        ])
        client = FakeModelServerClient([
            Model(id="small", recipe="ollama", max_context_window=8192),
        ])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"ollama": client}, opencode)

        assert len(result.warnings) == 1
        assert "small" in result.warnings[0]
        assert "8192" in result.warnings[0]
        assert "small" in opencode.written["provider"]["box"]["models"]

    def test_unknown_context_model_not_warned(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.30", name="Box", type="ollama"),
        ])
        client = FakeModelServerClient([
            Model(id="mystery", recipe="ollama", max_context_window=None),
        ])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"ollama": client}, opencode)
        assert result.warnings == []

    def test_lemonade_sub_64k_also_warns(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", name="Desktop", type="lemonade"),
        ])
        client = FakeModelServerClient([
            Model(id="tiny", recipe="llamacpp", max_context_window=4096),
        ])
        opencode = FakeOpenCodeConfig({})
        result = sync_models(registry, {"lemonade": client}, opencode)
        assert len(result.warnings) == 1
