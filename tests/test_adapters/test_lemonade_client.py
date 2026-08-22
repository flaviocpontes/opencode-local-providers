"""Adapter tests for HttpModelServerClient — real HTTP via pytest-httpserver."""

import pytest
import httpx
from pytest_httpserver import HTTPServer

from opencode_config.adapters.lemonade_client import HttpModelServerClient
from opencode_config.domain.entities import Server
from opencode_config.domain.ports import ServerError


class TestModelServerClient:
    def test_fetch_models_returns_parsed_models(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/v1/models").respond_with_json({
            "data": [
                {"id": "m1", "object": "model", "owned_by": "lemonade",
                 "recipe": "llamacpp", "labels": ["vision"],
                 "max_context_window": 262144, "downloaded": True},
                {"id": "m2", "object": "model", "owned_by": "lemonade",
                 "recipe": "llamacpp", "labels": [],
                 "max_context_window": 131072, "downloaded": True},
            ],
            "object": "list",
        })

        server = Server(host="localhost", port=httpserver.port)
        client = HttpModelServerClient()
        models = client.fetch_models(server)

        assert len(models) == 2
        assert models[0].id == "m1"
        assert models[0].max_context_window == 262144
        assert models[0].labels == ["vision"]
        assert models[0].recipe == "llamacpp"

        assert models[1].id == "m2"
        assert models[1].max_context_window == 131072
        assert models[1].labels == []

    def test_empty_data_list(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/v1/models").respond_with_json(
            {"data": [], "object": "list"}
        )
        server = Server(host="localhost", port=httpserver.port)
        client = HttpModelServerClient()
        assert client.fetch_models(server) == []

    def test_handles_missing_optional_fields(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/v1/models").respond_with_json({
            "data": [{"id": "minimal", "object": "model", "owned_by": "lemonade"}],
            "object": "list",
        })
        server = Server(host="localhost", port=httpserver.port)
        client = HttpModelServerClient()
        models = client.fetch_models(server)
        assert len(models) == 1
        assert models[0].max_context_window is None
        assert models[0].labels == []
        assert models[0].recipe == ""

    def test_http_error_raises(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/v1/models").respond_with_data(
            status=500
        )
        server = Server(host="localhost", port=httpserver.port)
        client = HttpModelServerClient()
        with pytest.raises(ServerError) as exc_info:
            client.fetch_models(server)
        assert exc_info.value.cause == "HTTP 500"

    def test_connection_refused(self):
        server = Server(host="localhost", port=1)
        client = HttpModelServerClient()
        with pytest.raises(ServerError) as exc_info:
            client.fetch_models(server)
        assert exc_info.value.cause == "connection refused"

    def test_garbage_body_raises(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/v1/models").respond_with_data(
            "not json at all"
        )
        server = Server(host="localhost", port=httpserver.port)
        client = HttpModelServerClient()
        with pytest.raises(ServerError) as exc_info:
            client.fetch_models(server)
        assert exc_info.value.cause == "invalid response"

    def test_error_label_uses_server_name(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/v1/models").respond_with_data(
            status=500
        )
        server = Server(host="localhost", port=httpserver.port, name="Desktop")
        client = HttpModelServerClient()
        with pytest.raises(ServerError) as exc_info:
            client.fetch_models(server)
        assert exc_info.value.server_label == "Desktop"

    def test_timeout_maps_to_short_cause(self):
        from opencode_config.adapters.lemonade_client import _short_cause
        assert _short_cause(httpx.ReadTimeout("read timed out")) == "timeout"
