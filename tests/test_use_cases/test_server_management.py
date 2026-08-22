"""Use case tests for server management — real registry adapter on tmp files,
fake clients and opencode config."""

import json
from pathlib import Path

from opencode_config.adapters.server_registry import JsonServerRegistry
from opencode_config.domain.entities import Model
from opencode_config.domain.ports import ServerError
from opencode_config.use_cases.server_management import (
    add_server,
    remove_server,
    set_server_enabled,
)


class FakeModelServerClient:
    def __init__(self, models=None):
        self._models = models or []

    def fetch_models(self, server):
        return self._models


class DeadClient:
    def fetch_models(self, server):
        raise ServerError(server.name or server.host, "connection refused")


class FakeOpenCodeConfig:
    def __init__(self, initial=None):
        self._config = initial if initial is not None else {}
        self.written = None

    def load_config(self):
        return self._config

    def write_config(self, config):
        self.written = config


def _registry(tmp_path: Path, entries: list[dict]) -> JsonServerRegistry:
    path = tmp_path / "servers.json"
    path.write_text(json.dumps({"servers": entries}) + "\n")
    return JsonServerRegistry(path)


def _read(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "servers.json").read_text())


class TestAddServer:
    def test_add_probes_registers_and_seeds_provider(self, tmp_path):
        registry = _registry(tmp_path, [])
        client = FakeModelServerClient([Model(id="m1", recipe="llamacpp")])
        opencode = FakeOpenCodeConfig({})

        result = add_server(registry, {"lemonade": client}, opencode,
                            "192.168.0.20", name="Lemonade Desktop")

        assert result.ok
        assert _read(tmp_path)["servers"][0]["id"] == "lemonade-desktop"
        assert opencode.written["provider"]["lemonade-desktop"]["models"] == {
            "m1": {"name": "m1", "limit": {"output": 32768}}
        }
        assert opencode.written["provider"]["lemonade-desktop"]["options"][
            "baseURL"] == "http://192.168.0.20:13305/api/v1"

    def test_add_ollama_uses_11434_and_v1(self, tmp_path):
        registry = _registry(tmp_path, [])
        client = FakeModelServerClient([Model(id="m", recipe="ollama")])
        opencode = FakeOpenCodeConfig({})

        result = add_server(registry, {"ollama": client}, opencode,
                            "192.168.0.30", server_type="ollama")

        assert result.ok
        entry = _read(tmp_path)["servers"][0]
        assert entry["type"] == "ollama"
        assert entry["port"] == 11434
        assert opencode.written["provider"]["192.168.0.30"]["options"][
            "baseURL"] == "http://192.168.0.30:11434/v1"

    def test_add_unreachable_writes_nothing(self, tmp_path):
        registry = _registry(tmp_path, [])
        opencode = FakeOpenCodeConfig({})

        result = add_server(registry, {"lemonade": DeadClient()}, opencode,
                            "10.0.0.99")

        assert not result.ok
        assert "10.0.0.99" in result.message
        assert "nothing written" in result.message
        assert _read(tmp_path)["servers"] == []
        assert opencode.written is None

    def test_add_collision_suffixes_id(self, tmp_path):
        registry = _registry(tmp_path, [{"name": "Box", "host": "192.168.0.20"}])
        client = FakeModelServerClient([])
        opencode = FakeOpenCodeConfig({})

        add_server(registry, {"lemonade": client}, opencode,
                   "192.168.0.30", name="Box")

        ids = [e["id"] for e in _read(tmp_path)["servers"]]
        assert ids == ["box", "box-2"]


class TestRemoveServer:
    def test_remove_deletes_registry_entry_and_provider(self, tmp_path):
        registry = _registry(tmp_path, [{"id": "box", "host": "192.168.0.20"}])
        opencode = FakeOpenCodeConfig({"provider": {
            "box": {"name": "Box", "models": {"m": {"name": "m"}}}}})

        result = remove_server(registry, opencode, "box")

        assert result.ok
        assert _read(tmp_path)["servers"] == []
        assert "box" not in opencode.written["provider"]

    def test_remove_tolerates_missing_provider_entry(self, tmp_path):
        registry = _registry(tmp_path, [{"id": "box", "host": "192.168.0.20"}])
        opencode = FakeOpenCodeConfig({})

        result = remove_server(registry, opencode, "box")

        assert result.ok
        assert _read(tmp_path)["servers"] == []

    def test_remove_unknown_id_writes_nothing(self, tmp_path):
        registry = _registry(tmp_path, [{"id": "box", "host": "192.168.0.20"}])
        opencode = FakeOpenCodeConfig({})

        result = remove_server(registry, opencode, "ghost")

        assert not result.ok
        assert "ghost" in result.message
        assert len(_read(tmp_path)["servers"]) == 1
        assert opencode.written is None


class TestSetServerEnabled:
    def test_disable_sets_both_flags(self, tmp_path):
        registry = _registry(tmp_path, [{"id": "box", "host": "192.168.0.20"}])
        models = {"m": {"name": "m"}}
        opencode = FakeOpenCodeConfig({"provider": {
            "box": {"name": "Box", "models": models}}})

        result = set_server_enabled(registry, opencode, "box", False)

        assert result.ok
        assert _read(tmp_path)["servers"][0]["enabled"] is False
        entry = opencode.written["provider"]["box"]
        assert entry["disabled"] is True
        assert entry["models"] == models  # kept intact

    def test_enable_flips_both_flags(self, tmp_path):
        registry = _registry(
            tmp_path, [{"id": "box", "host": "192.168.0.20", "enabled": False}])
        opencode = FakeOpenCodeConfig({"provider": {
            "box": {"name": "Box", "disabled": True, "models": {}}}})

        result = set_server_enabled(registry, opencode, "box", True)

        assert result.ok
        assert _read(tmp_path)["servers"][0]["enabled"] is True
        assert "disabled" not in opencode.written["provider"]["box"]

    def test_disable_last_enabled_server_succeeds(self, tmp_path):
        registry = _registry(tmp_path, [{"id": "box", "host": "192.168.0.20"}])
        opencode = FakeOpenCodeConfig({})

        result = set_server_enabled(registry, opencode, "box", False)

        assert result.ok

    def test_unknown_id_fails(self, tmp_path):
        registry = _registry(tmp_path, [])
        opencode = FakeOpenCodeConfig({})

        result = set_server_enabled(registry, opencode, "ghost", False)

        assert not result.ok
        assert "ghost" in result.message
        assert opencode.written is None
