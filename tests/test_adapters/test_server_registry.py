"""Adapter tests for JsonServerRegistry — file I/O with temp files."""

import json
from pathlib import Path

import pytest

from opencode_config.adapters.server_registry import JsonServerRegistry
from opencode_config.domain.entities import Server
from opencode_config.domain.ports import ConfigError


class TestServerRegistry:
    def test_load_servers(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [
                {"host": "192.168.0.20", "port": 13305, "name": "Desktop"},
                {"host": "192.168.0.7", "port": 13305},
            ]
        }) + "\n")
        registry = JsonServerRegistry(path)
        servers = registry.load_servers()
        assert len(servers) == 2
        assert servers[0].host == "192.168.0.20"
        assert servers[0].port == 13305
        assert servers[0].name == "Desktop"
        assert servers[1].host == "192.168.0.7"
        assert servers[1].port == 13305
        assert servers[1].name is None

    def test_port_defaults_to_13305(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20"}]
        }) + "\n")
        registry = JsonServerRegistry(path)
        servers = registry.load_servers()
        assert servers[0].port == 13305
        assert servers[0].type == "lemonade"

    def test_ollama_defaults_to_11434(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.30", "type": "ollama"}]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert servers[0].type == "ollama"
        assert servers[0].port == 11434

    def test_explicit_port_overrides_type_default(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.30", "type": "ollama", "port": 1234}]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert servers[0].port == 1234

    def test_explicit_lemonade_type(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20", "type": "lemonade"}]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert servers[0].type == "lemonade"
        assert servers[0].port == 13305

    def test_missing_file_returns_empty(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        registry = JsonServerRegistry(path)
        assert registry.load_servers() == []

    def test_empty_servers_list(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({"servers": []}) + "\n")
        registry = JsonServerRegistry(path)
        assert registry.load_servers() == []


class TestServerRegistryErrors:
    def test_invalid_json_raises_config_error(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text("{not json")
        with pytest.raises(ConfigError) as exc_info:
            JsonServerRegistry(path).load_servers()
        assert str(path) in str(exc_info.value)

    def test_missing_host_raises_config_error(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "ok.example"}, {"port": 13305}]
        }) + "\n")
        with pytest.raises(ConfigError) as exc_info:
            JsonServerRegistry(path).load_servers()
        assert "#2" in str(exc_info.value)
        assert "host" in str(exc_info.value)

    def test_zero_enabled_loads_fine(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20", "enabled": False}]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert len(servers) == 1
        assert servers[0].enabled is False

    def test_unknown_type_raises_config_error(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20", "type": "vllm"}]
        }) + "\n")
        with pytest.raises(ConfigError) as exc_info:
            JsonServerRegistry(path).load_servers()
        assert str(path) in str(exc_info.value)
        assert "#1" in str(exc_info.value)
        assert "vllm" in str(exc_info.value)

    def test_disabled_entries_included_in_result(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [
                {"host": "192.168.0.20"},
                {"host": "192.168.0.7", "enabled": False},
            ]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert [s.host for s in servers] == ["192.168.0.20", "192.168.0.7"]
        assert [s.enabled for s in servers] == [True, False]


class TestServerRegistryIds:
    def test_load_derives_ids_in_memory(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [
                {"host": "192.168.0.20", "name": "Lemonade Desktop"},
                {"host": "192.168.0.7"},
            ]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert servers[0].id == "lemonade-desktop"  # old provider-key derivation
        assert servers[1].id == "192.168.0.7"
        assert "id" not in json.loads(path.read_text())["servers"][0]  # not persisted yet

    def test_ids_persisted_on_next_write(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20", "name": "Lemonade Desktop"}]
        }) + "\n")
        registry = JsonServerRegistry(path)
        registry.set_enabled("lemonade-desktop", False)
        entries = json.loads(path.read_text())["servers"]
        assert entries[0]["id"] == "lemonade-desktop"

    def test_existing_ids_left_alone(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"id": "custom-key", "host": "192.168.0.20",
                         "name": "Lemonade Desktop"}]
        }) + "\n")
        registry = JsonServerRegistry(path)
        registry.set_enabled("custom-key", False)
        entries = json.loads(path.read_text())["servers"]
        assert entries[0]["id"] == "custom-key"

    def test_unknown_fields_survive_round_trip(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "version": 2,
            "servers": [{"host": "192.168.0.20", "note": "hand-added"}],
        }) + "\n")
        registry = JsonServerRegistry(path)
        registry.set_enabled("192.168.0.20", False)
        data = json.loads(path.read_text())
        assert data["version"] == 2
        assert data["servers"][0]["note"] == "hand-added"


class TestServerRegistryMutations:
    def test_add_server_mints_id_from_name(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        registry = JsonServerRegistry(path)
        server = registry.add_server(Server(host="192.168.0.20", port=13305,
                                            name="Lemonade Desktop"))
        assert server.id == "lemonade-desktop"
        assert server.enabled is True
        entries = json.loads(path.read_text())["servers"]
        assert entries[0]["id"] == "lemonade-desktop"
        assert entries[0]["enabled"] is True

    def test_add_server_without_name_uses_host(self, tmp_path: Path):
        registry = JsonServerRegistry(tmp_path / "servers.json")
        server = registry.add_server(Server(host="192.168.0.7"))
        assert server.id == "192.168.0.7"

    def test_add_server_collision_gets_suffix(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20", "name": "Lemonade Desktop"}]
        }) + "\n")
        registry = JsonServerRegistry(path)
        server = registry.add_server(Server(host="192.168.0.30",
                                            name="Lemonade Desktop"))
        assert server.id == "lemonade-desktop-2"

    def test_add_server_creates_missing_file(self, tmp_path: Path):
        path = tmp_path / "nested" / "servers.json"
        registry = JsonServerRegistry(path)
        registry.add_server(Server(host="192.168.0.20"))
        assert path.exists()

    def test_remove_server_deletes_entry(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [
                {"id": "a", "host": "192.168.0.20"},
                {"id": "b", "host": "192.168.0.7"},
            ]
        }) + "\n")
        registry = JsonServerRegistry(path)
        assert registry.remove_server("a") is True
        entries = json.loads(path.read_text())["servers"]
        assert [e["id"] for e in entries] == ["b"]

    def test_remove_unknown_id_returns_false(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({"servers": [{"id": "a", "host": "h"}]}) + "\n")
        registry = JsonServerRegistry(path)
        assert registry.remove_server("ghost") is False

    def test_set_enabled_flips_flag(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"id": "a", "host": "192.168.0.20", "enabled": True}]
        }) + "\n")
        registry = JsonServerRegistry(path)
        assert registry.set_enabled("a", False) is True
        entry = json.loads(path.read_text())["servers"][0]
        assert entry["enabled"] is False

    def test_set_enabled_unknown_id_returns_false(self, tmp_path: Path):
        registry = JsonServerRegistry(tmp_path / "servers.json")
        assert registry.set_enabled("ghost", True) is False
