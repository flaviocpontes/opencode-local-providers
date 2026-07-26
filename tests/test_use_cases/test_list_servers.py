"""Use case tests for list_servers — inject fake adapters."""

from opencode_config.domain.entities import Server, Model
from opencode_config.use_cases.list_servers import list_servers


class FakeServerRegistry:
    def __init__(self, servers=None):
        self._servers = servers or []

    def load_servers(self):
        return self._servers


class FakeLemonadeClient:
    def __init__(self, models=None):
        self._models = models or []

    def fetch_models(self, server):
        return self._models


class TestListServers:
    def test_empty_registry(self):
        result = list_servers(FakeServerRegistry([]), FakeLemonadeClient())
        assert result == []

    def test_single_server_no_models(self):
        registry = FakeServerRegistry([Server(host="localhost", port=13305)])
        client = FakeLemonadeClient([])
        result = list_servers(registry, client)
        assert len(result) == 1
        assert result[0]["name"] == "localhost:13305"
        assert result[0]["models"] == []

    def test_single_server_with_models(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
        ])
        models = [
            Model(id="m1", recipe="llamacpp"),
            Model(id="m2", recipe="llamacpp"),
        ]
        client = FakeLemonadeClient(models)
        result = list_servers(registry, client)
        assert len(result[0]["models"]) == 2

    def test_filters_non_chat_models(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeLemonadeClient([
            Model(id="chat", recipe="llamacpp"),
            Model(id="img", recipe="sd-cpp", labels=["image"]),
        ])
        result = list_servers(registry, client)
        assert len(result[0]["models"]) == 1
        assert result[0]["models"][0].id == "chat"

    def test_multiple_servers(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
            Server(host="192.168.0.7", port=13305, name="Laptop"),
        ])
        client = FakeLemonadeClient([Model(id="m", recipe="llamacpp")])
        result = list_servers(registry, client)
        assert len(result) == 2
        assert result[0]["name"] == "Desktop"
        assert result[1]["name"] == "Laptop"
