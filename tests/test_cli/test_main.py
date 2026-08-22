"""CLI tests for main() — real temp files + pytest-httpserver, no mocks."""

import json

import pytest
from pytest_httpserver import HTTPServer

from opencode_config.cli.main import main


def _write_registry(path, entries):
    path.write_text(json.dumps({"servers": entries}, indent=2) + "\n")


def _models_payload():
    return {
        "data": [
            {"id": "have-m", "recipe": "llamacpp", "labels": [],
             "downloaded": True, "max_context_window": 8192},
            {"id": "want-m", "recipe": "llamacpp", "labels": [],
             "downloaded": False, "max_context_window": 8192},
        ],
        "object": "list",
    }


class TestBasics:
    def test_version_exits_0(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert capsys.readouterr().out.startswith("occfg ")

    def test_no_args_prints_usage_exits_0(self, capsys):
        main([])
        assert "usage:" in capsys.readouterr().out

    def test_bare_server_prints_usage_exits_0(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["server", "--help"])
        assert exc.value.code == 0

    def test_unknown_subcommand_exit_2(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["frobnicate"])
        assert exc.value.code == 2


class TestSync:
    def test_dry_run_untouched_file(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "localhost", "port": httpserver.port,
                               "name": "Test"}])
        target = tmp_path / "opencode.json"
        original = '{"provider": {"keep": {"name": "Keep"}}}'
        target.write_text(original)

        main(["--servers", str(reg), "--opencode", str(target), "sync", "-n"])

        assert target.read_text() == original
        out = capsys.readouterr().out
        assert "(dry-run)" in out
        assert "have-m" in out
        assert "want-m" not in out

    def test_dry_run_missing_file_not_created(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "localhost", "port": httpserver.port,
                               "name": "Test"}])
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target), "sync", "-n"])

        assert not target.exists()
        assert "have-m" in capsys.readouterr().out

    def test_zero_enabled_servers_is_noop_exit_0(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "192.168.0.20", "enabled": False}])
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target), "sync"])

        assert not target.exists()
        out = capsys.readouterr().out
        assert "nothing to do" in out
        assert "Updated providers" not in out

    def test_show_all_includes_undownloaded(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "localhost", "port": httpserver.port,
                               "name": "Test"}])
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target),
              "sync", "-n", "--show-all"])

        out = capsys.readouterr().out
        assert "have-m" in out
        assert "want-m" in out

    def test_dead_server_among_healthy_exits_1(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [
            {"host": "localhost", "port": 1, "name": "Dead"},
            {"host": "localhost", "port": httpserver.port, "name": "Alive"},
        ])
        target = tmp_path / "opencode.json"

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target), "sync"])
        assert exc.value.code == 1

        out = capsys.readouterr().out
        assert "✗ Dead: connection refused" in out
        assert "entry left unchanged, skipped" in out
        written = json.loads(target.read_text())
        assert "alive" in written["provider"]
        assert "dead" not in written["provider"]

    def test_bad_registry_json_exits_2(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        reg.write_text("{broken")
        target = tmp_path / "opencode.json"

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target), "sync"])
        assert exc.value.code == 2

        out = capsys.readouterr().out
        assert str(reg) in out
        assert "Traceback" not in out
        assert not target.exists()

    def test_registry_missing_host_exits_2(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"port": 13305}])

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "sync", "-n"])
        assert exc.value.code == 2
        assert "host" in capsys.readouterr().out

    def test_bad_opencode_json_exits_2_untouched(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "localhost", "port": httpserver.port,
                               "name": "Test"}])
        target = tmp_path / "opencode.json"
        original = "{broken"
        target.write_text(original)

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target), "sync"])
        assert exc.value.code == 2

        out = capsys.readouterr().out
        assert str(target) in out
        assert "nothing was written" in out
        assert target.read_text() == original


class TestServerAdd:
    def test_add_writes_registry_and_provider(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [])
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target),
              "server", "add", "localhost", "--port", str(httpserver.port),
              "--name", "Test Box"])

        registry = json.loads(reg.read_text())["servers"]
        assert registry[0]["id"] == "test-box"
        assert registry[0]["enabled"] is True
        provider = json.loads(target.read_text())["provider"]
        assert "have-m" in provider["test-box"]["models"]
        assert "want-m" not in provider["test-box"]["models"]

    def test_add_unreachable_writes_nothing_exit_1(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        _write_registry(reg, [])
        target = tmp_path / "opencode.json"

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target),
                  "server", "add", "localhost", "--port", "1"])
        assert exc.value.code == 1

        assert json.loads(reg.read_text())["servers"] == []
        assert not target.exists()
        out = capsys.readouterr().out
        assert "✗" in out
        assert "nothing written" in out

    def test_add_ollama_probes_v1(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/tags").respond_with_json(
            {"models": [{"name": "llama4:latest", "size": 4_600_000_000}]}
        )
        httpserver.expect_request("/api/show").respond_with_json(
            {"capabilities": ["completion"]}
        )
        reg = tmp_path / "servers.json"
        _write_registry(reg, [])
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target),
              "server", "add", "localhost", "--type", "ollama",
              "--port", str(httpserver.port)])

        registry = json.loads(reg.read_text())["servers"]
        assert registry[0]["type"] == "ollama"
        provider = json.loads(target.read_text())["provider"]
        assert "llama4:latest" in provider["localhost"]["models"]
        assert provider["localhost"]["options"]["baseURL"] == \
            f"http://localhost:{httpserver.port}/v1"


class TestServerLifecycle:
    def _setup(self, tmp_path):
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"id": "box", "host": "192.168.0.20",
                               "name": "Box"}])
        target = tmp_path / "opencode.json"
        target.write_text(json.dumps({"provider": {
            "box": {"name": "Box", "models": {"m": {"name": "m"}}}}}))
        return reg, target

    def test_disable_sets_both_flags(self, tmp_path, capsys):
        reg, target = self._setup(tmp_path)

        main(["--servers", str(reg), "--opencode", str(target),
              "server", "disable", "box"])

        assert json.loads(reg.read_text())["servers"][0]["enabled"] is False
        provider = json.loads(target.read_text())["provider"]
        assert provider["box"]["disabled"] is True
        assert provider["box"]["models"] == {"m": {"name": "m"}}

    def test_enable_flips_back(self, tmp_path, capsys):
        reg, target = self._setup(tmp_path)
        main(["--servers", str(reg), "--opencode", str(target),
              "server", "disable", "box"])
        main(["--servers", str(reg), "--opencode", str(target),
              "server", "enable", "box"])

        assert json.loads(reg.read_text())["servers"][0]["enabled"] is True
        assert "disabled" not in json.loads(target.read_text())["provider"]["box"]

    def test_remove_cleans_both_files(self, tmp_path, capsys):
        reg, target = self._setup(tmp_path)

        main(["--servers", str(reg), "--opencode", str(target),
              "server", "remove", "box"])

        assert json.loads(reg.read_text())["servers"] == []
        assert json.loads(target.read_text())["provider"] == {}

    def test_unknown_id_exits_1(self, tmp_path, capsys):
        reg, target = self._setup(tmp_path)

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target),
                  "server", "disable", "ghost"])
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "ghost" in out
        assert "✗" in out
        assert json.loads(reg.read_text())["servers"][0]["id"] == "box"  # untouched


class TestServerList:
    def test_mixed_listing(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [
            {"host": "localhost", "port": httpserver.port, "name": "Alive"},
            {"host": "192.168.0.99", "port": 13305, "name": "Off",
             "enabled": False},
        ])

        main(["--servers", str(reg), "server", "list"])

        out = capsys.readouterr().out
        assert "✓ alive — Alive" in out
        assert "1 chat models" in out
        assert "[disabled]" in out
        assert "Off" in out

    def test_dead_enabled_server_exits_1(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "localhost", "port": 1, "name": "Dead"}])

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "server", "list"])
        assert exc.value.code == 1
        assert "✗ dead" in capsys.readouterr().out

    def test_show_all_counts_undownloaded(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, [{"host": "localhost", "port": httpserver.port,
                               "name": "Test"}])

        main(["--servers", str(reg), "server", "list", "--show-all"])
        main(["--servers", str(reg), "server", "list"])

        outs = capsys.readouterr()
        assert "2 chat models" in outs.out
        assert "1 chat models" in outs.out
