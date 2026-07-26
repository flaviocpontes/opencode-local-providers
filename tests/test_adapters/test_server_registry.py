"""Adapter tests for JsonServerRegistry — file I/O with temp files."""

import json
from pathlib import Path

from opencode_config.adapters.server_registry import JsonServerRegistry


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

    def test_missing_file_returns_empty(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        registry = JsonServerRegistry(path)
        assert registry.load_servers() == []

    def test_empty_servers_list(self, tmp_path: Path):
        path = tmp_path / "servers.json"
        path.write_text(json.dumps({"servers": []}) + "\n")
        registry = JsonServerRegistry(path)
        assert registry.load_servers() == []
