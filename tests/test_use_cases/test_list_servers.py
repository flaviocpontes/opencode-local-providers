"""Use case tests for list_servers — inject fake adapters."""

from opencode_config.domain.entities import Server, Model
from opencode_config.domain.ports import ServerError
from opencode_config.use_cases.list_servers import list_servers


class FakeServerRegistry:
    def __init__(self, servers=None):
        self._servers = servers or []

    def load_servers(self):
        return self._servers

    def add_server(self, server):
        from dataclasses import replace
        return replace(server, id=server.id or server.host)

    def remove_server(self, server_id):
        return False

    def set_enabled(self, server_id, enabled):
        return False


class FakeModelServerClient:
    def __init__(self, models=None):
        self._models = models or []

    def fetch_models(self, server):
        return self._models


class FlakyModelServerClient:
    def __init__(self, bad_host, models):
        self._bad_host = bad_host
        self._models = models

    def fetch_models(self, server):
        if server.host == self._bad_host:
            raise ServerError(server.name or server.host, "connection refused")
        return self._models


class TestListServers:
    def test_empty_registry(self):
        result = list_servers(FakeServerRegistry([]), {"lemonade": FakeModelServerClient()})
        assert result == []

    def test_single_server_no_models(self):
        registry = FakeServerRegistry([Server(host="localhost", port=13305)])
        client = FakeModelServerClient([])
        result = list_servers(registry, {"lemonade": client})
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
        client = FakeModelServerClient(models)
        result = list_servers(registry, {"lemonade": client})
        assert len(result[0]["models"]) == 2

    def test_filters_non_chat_models(self):
        registry = FakeServerRegistry([
            Server(host="localhost", port=13305, name="Test"),
        ])
        client = FakeModelServerClient([
            Model(id="chat", recipe="llamacpp"),
            Model(id="img", recipe="sd-cpp", labels=["image"]),
        ])
        result = list_servers(registry, {"lemonade": client})
        assert len(result[0]["models"]) == 1
        assert result[0]["models"][0].id == "chat"

    def test_multiple_servers(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Desktop"),
            Server(host="192.168.0.7", port=13305, name="Laptop"),
        ])
        client = FakeModelServerClient([Model(id="m", recipe="llamacpp")])
        result = list_servers(registry, {"lemonade": client})
        assert len(result) == 2
        assert result[0]["name"] == "Desktop"
        assert result[1]["name"] == "Laptop"

    def test_default_filters_undownloaded(self):
        registry = FakeServerRegistry([Server(host="localhost", port=13305)])
        client = FakeModelServerClient([
            Model(id="have", recipe="llamacpp", downloaded=True),
            Model(id="want", recipe="llamacpp", downloaded=False),
        ])
        result = list_servers(registry, {"lemonade": client})
        assert [m.id for m in result[0]["models"]] == ["have"]

    def test_show_all_includes_undownloaded(self):
        registry = FakeServerRegistry([Server(host="localhost", port=13305)])
        client = FakeModelServerClient([
            Model(id="have", recipe="llamacpp", downloaded=True),
            Model(id="want", recipe="llamacpp", downloaded=False),
        ])
        result = list_servers(registry, {"lemonade": client}, show_all=True)
        assert [m.id for m in result[0]["models"]] == ["have", "want"]

    def test_show_all_still_excludes_non_chat(self):
        registry = FakeServerRegistry([Server(host="localhost", port=13305)])
        client = FakeModelServerClient([
            Model(id="llm", recipe="llamacpp", downloaded=False),
            Model(id="img", recipe="sd-cpp", labels=["image"], downloaded=False),
        ])
        result = list_servers(registry, {"lemonade": client}, show_all=True)
        assert [m.id for m in result[0]["models"]] == ["llm"]

    def test_dead_server_becomes_error_row(self):
        registry = FakeServerRegistry([
            Server(host="192.168.0.20", port=13305, name="Dead"),
            Server(host="192.168.0.7", port=13305, name="Alive"),
        ])
        client = FlakyModelServerClient(
            "192.168.0.20", [Model(id="m1", recipe="llamacpp")]
        )
        result = list_servers(registry, {"lemonade": client})

        assert result[0]["error"] == "connection refused"
        assert result[0]["models"] == []
        assert result[1]["error"] is None
        assert len(result[1]["models"]) == 1
