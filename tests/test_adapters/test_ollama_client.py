"""Adapter tests for HttpOllamaClient — real HTTP via pytest-httpserver."""

import pytest
from pytest_httpserver import HTTPServer

from opencode_config.adapters.ollama_client import HttpOllamaClient
from opencode_config.domain.entities import Server
from opencode_config.domain.ports import ServerError


def _tags(models: list[dict]) -> dict:
    return {"models": models}


def _show(capabilities: list | None = None, num_ctx: int | None = None,
          context_length: int | None = None) -> dict:
    body: dict = {}
    if capabilities is not None:
        body["capabilities"] = capabilities
    if num_ctx is not None:
        body["parameters"] = f"temperature 0.7\nnum_ctx {num_ctx}"
    if context_length is not None:
        body["model_info"] = {"gemma4.context_length": context_length}
    return body


class TestOllamaClient:
    def _show_for(self, httpserver, model: str, body: dict) -> None:
        httpserver.expect_request(
            "/api/show", method="POST", json={"model": model}
        ).respond_with_json(body)

    def test_tags_and_show_happy_path(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_json(_tags([
            {"name": "gemma4:latest", "model": "gemma4:latest", "size": 9608350245},
            {"name": "qwen3:8b", "model": "qwen3:8b"},
        ]))
        self._show_for(httpserver, "gemma4:latest",
                       _show(capabilities=["completion", "vision"], context_length=131072))
        self._show_for(httpserver, "qwen3:8b",
                       _show(capabilities=["completion", "thinking"], num_ctx=262144))

        models = HttpOllamaClient().fetch_models(
            Server(host="localhost", port=httpserver.port, type="ollama"))

        assert len(models) == 2
        assert models[0].id == "gemma4:latest"
        assert models[0].recipe == "ollama"
        assert models[0].labels == ["vision"]
        assert models[0].max_context_window == 131072
        assert models[0].size == pytest.approx(9.6, abs=0.1)
        assert models[1].labels == ["reasoning"]
        assert models[1].max_context_window == 262144  # num_ctx overrides model_info

    def test_num_ctx_preferred_over_model_info(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_json(
            _tags([{"name": "m"}]))
        self._show_for(httpserver, "m",
                       _show(capabilities=["completion"], num_ctx=65536, context_length=8192))
        models = HttpOllamaClient().fetch_models(
            Server(host="localhost", port=httpserver.port, type="ollama"))
        assert models[0].max_context_window == 65536

    def test_embedding_model_excluded(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_json(
            _tags([{"name": "nomic-embed-text"}]))
        self._show_for(httpserver, "nomic-embed-text",
                       _show(capabilities=["embedding"]))
        models = HttpOllamaClient().fetch_models(
            Server(host="localhost", port=httpserver.port, type="ollama"))
        assert models[0].recipe == ""  # fails the chat gate downstream

    def test_failed_show_degrades_to_unenriched(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_json(_tags([
            {"name": "a"}, {"name": "b"},
        ]))
        httpserver.expect_request(
            "/api/show", method="POST", json={"model": "a"}
        ).respond_with_data(status=500)
        self._show_for(httpserver, "b",
                       _show(capabilities=["completion"], context_length=4096))

        models = HttpOllamaClient().fetch_models(
            Server(host="localhost", port=httpserver.port, type="ollama"))

        assert models[0].id == "a"
        assert models[0].recipe == "ollama"  # conservative include
        assert models[0].max_context_window is None
        assert models[0].labels == []
        assert models[1].max_context_window == 4096  # sibling unaffected

    def test_tags_http_error_raises_server_error(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_data(status=500)
        with pytest.raises(ServerError) as exc_info:
            HttpOllamaClient().fetch_models(
                Server(host="localhost", port=httpserver.port, type="ollama"))
        assert exc_info.value.cause == "HTTP 500"

    def test_connection_refused(self):
        with pytest.raises(ServerError) as exc_info:
            HttpOllamaClient().fetch_models(
                Server(host="localhost", port=1, type="ollama"))
        assert exc_info.value.cause == "connection refused"

    def test_empty_tags(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_json({"models": []})
        models = HttpOllamaClient().fetch_models(
            Server(host="localhost", port=httpserver.port, type="ollama"))
        assert models == []

    def test_error_label_uses_server_name(self, httpserver: HTTPServer):
        httpserver.expect_request("/api/tags").respond_with_data(status=500)
        with pytest.raises(ServerError) as exc_info:
            HttpOllamaClient().fetch_models(
                Server(host="localhost", port=httpserver.port,
                       name="Ollama Box", type="ollama"))
        assert exc_info.value.server_label == "Ollama Box"
