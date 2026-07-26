"""Domain entity creation and equality."""

from opencode_config.domain.entities import Server, Model, ProviderConfig


class TestServer:
    def test_minimal(self):
        s = Server(host="192.168.0.20")
        assert s.host == "192.168.0.20"
        assert s.port == 13305
        assert s.name is None

    def test_full(self):
        s = Server(host="192.168.0.7", port=13305, name="Lemonade Laptop")
        assert s.host == "192.168.0.7"
        assert s.port == 13305
        assert s.name == "Lemonade Laptop"

    def test_custom_port(self):
        s = Server(host="localhost", port=9999)
        assert s.port == 9999


class TestModel:
    def test_minimal(self):
        m = Model(id="test-model")
        assert m.id == "test-model"
        assert m.recipe == ""
        assert m.labels == []
        assert m.max_context_window is None
        assert m.checkpoint is None
        assert m.size is None
        assert m.downloaded is True
        assert m.suggested is False
        assert m.created is None
        assert m.image_defaults is None

    def test_full(self):
        m = Model(id="test-model", max_context_window=131072,
                  labels=["vision"], recipe="llamacpp",
                  checkpoint="org/repo:variant", size=3.5,
                  downloaded=False, suggested=True, created=1744173590,
                  image_defaults={"steps": 4})
        assert m.max_context_window == 131072
        assert m.labels == ["vision"]
        assert m.recipe == "llamacpp"
        assert m.checkpoint == "org/repo:variant"
        assert m.size == 3.5
        assert m.downloaded is False
        assert m.suggested is True
        assert m.created == 1744173590
        assert m.image_defaults == {"steps": 4}


class TestProviderConfig:
    def test_minimal(self):
        p = ProviderConfig(key="test-server")
        assert p.key == "test-server"
        assert p.npm == "@ai-sdk/openai-compatible"
        assert p.name == ""
        assert p.options is None
        assert p.models == []
        assert p.api_key is None
        assert p.disabled is False

    def test_full(self):
        models = [Model(id="m1"), Model(id="m2")]
        p = ProviderConfig(
            key="full-server",
            npm="@ai-sdk/openai-compatible",
            name="Full Server",
            options={"baseURL": "http://localhost:13305/api/v1"},
            models=models,
            api_key="sk-test",
            disabled=True,
        )
        assert p.key == "full-server"
        assert p.name == "Full Server"
        assert p.options == {"baseURL": "http://localhost:13305/api/v1"}
        assert len(p.models) == 2
        assert p.models[0].id == "m1"
        assert p.models[1].id == "m2"
        assert p.api_key == "sk-test"
        assert p.disabled is True
