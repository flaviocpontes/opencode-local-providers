"""Adapter tests for JsonServerRegistry — file I/O with temp files."""

import json
from pathlib import Path

import pytest

from opencode_config.adapters.server_registry import JsonServerRegistry
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

    def test_zero_enabled_raises_config_error(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [{"host": "192.168.0.20", "enabled": False}]
        }) + "\n")
        with pytest.raises(ConfigError):
            JsonServerRegistry(path).load_servers()

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

    def test_disabled_filtered_from_result(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({
            "servers": [
                {"host": "192.168.0.20"},
                {"host": "192.168.0.7", "enabled": False},
            ]
        }) + "\n")
        servers = JsonServerRegistry(path).load_servers()
        assert [s.host for s in servers] == ["192.168.0.20"]
