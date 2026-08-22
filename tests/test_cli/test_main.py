"""CLI tests for main() — real temp files + pytest-httpserver, no mocks."""

import json

import pytest
from pytest_httpserver import HTTPServer

from opencode_config.cli.main import main


def _write_registry(path, host, port):
    path.write_text(json.dumps({
        "servers": [{"host": host, "port": port, "name": "Test"}]
    }, indent=2) + "\n")


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


class TestModeValidation:
    def test_conflicting_modes_exit_2(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--init-servers", "-l"])
        assert exc.value.code == 2
        assert "not allowed with" in capsys.readouterr().err

    def test_version_exits_0(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert capsys.readouterr().out.startswith("opencode_config ")


class TestDryRun:
    def test_existing_file_untouched(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, "localhost", httpserver.port)
        target = tmp_path / "opencode.json"
        original = '{"provider": {"keep": {"name": "Keep"}}}'
        target.write_text(original)

        main(["--servers", str(reg), "--opencode", str(target), "-n"])

        assert target.read_text() == original
        out = capsys.readouterr().out
        assert "(dry-run)" in out
        assert "have-m" in out
        assert "want-m" not in out  # undownloaded filtered by default

    def test_missing_file_not_created(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, "localhost", httpserver.port)
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target), "-n"])

        assert not target.exists()
        assert "have-m" in capsys.readouterr().out


class TestShowAll:
    def test_passes_through_to_sync(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, "localhost", httpserver.port)
        target = tmp_path / "opencode.json"

        main(["--servers", str(reg), "--opencode", str(target), "-n", "--show-all"])

        out = capsys.readouterr().out
        assert "have-m" in out
        assert "want-m" in out

    def test_passes_through_to_list(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, "localhost", httpserver.port)

        main(["--servers", str(reg), "-l", "--show-all"])

        out = capsys.readouterr().out
        assert "have-m" in out
        assert "want-m" in out

    def test_list_default_filters_undownloaded(self, tmp_path, httpserver: HTTPServer, capsys):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, "localhost", httpserver.port)

        main(["--servers", str(reg), "-l"])

        out = capsys.readouterr().out
        assert "have-m" in out
        assert "want-m" not in out


class TestFriendlyErrors:
    def test_dead_server_among_healthy_exits_1(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        reg.write_text(json.dumps({"servers": [
            {"host": "localhost", "port": 1, "name": "Dead"},
            {"host": "localhost", "port": httpserver.port, "name": "Alive"},
        ]}) + "\n")
        target = tmp_path / "opencode.json"

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target)])
        assert exc.value.code == 1

        out = capsys.readouterr().out
        assert "✗ Dead: connection refused" in out
        assert "entry left unchanged, skipped" in out
        written = json.loads(target.read_text())
        assert "alive" in written["provider"]
        assert "dead" not in written["provider"]

    def test_dead_server_preserves_stale_entry(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        reg.write_text(json.dumps({"servers": [
            {"host": "localhost", "port": 1, "name": "Dead"},
        ]}) + "\n")
        target = tmp_path / "opencode.json"
        stale = {"name": "Dead", "models": {}}
        target.write_text(json.dumps({"provider": {"dead": stale}}))

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target)])
        assert exc.value.code == 1
        assert json.loads(target.read_text())["provider"]["dead"] == stale

    def test_bad_registry_json_exits_2(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        reg.write_text("{broken")
        target = tmp_path / "opencode.json"

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target)])
        assert exc.value.code == 2

        out = capsys.readouterr().out
        assert str(reg) in out
        assert "Traceback" not in out
        assert not target.exists()

    def test_registry_missing_host_exits_2(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        reg.write_text(json.dumps({"servers": [{"port": 13305}]}) + "\n")

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "-n"])
        assert exc.value.code == 2
        assert "host" in capsys.readouterr().out

    def test_zero_enabled_servers_exits_2(self, tmp_path, capsys):
        reg = tmp_path / "servers.json"
        reg.write_text(json.dumps({"servers": [
            {"host": "192.168.0.20", "enabled": False}
        ]}) + "\n")
        target = tmp_path / "opencode.json"

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target)])
        assert exc.value.code == 2
        assert not target.exists()

    def test_bad_opencode_json_exits_2_untouched(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        _write_registry(reg, "localhost", httpserver.port)
        target = tmp_path / "opencode.json"
        original = "{broken"
        target.write_text(original)

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "--opencode", str(target)])
        assert exc.value.code == 2

        out = capsys.readouterr().out
        assert str(target) in out
        assert "nothing was written" in out
        assert "Traceback" not in out
        assert target.read_text() == original

    def test_list_dead_server_row_exits_1(
        self, tmp_path, httpserver: HTTPServer, capsys
    ):
        httpserver.expect_request("/api/v1/models").respond_with_json(_models_payload())
        reg = tmp_path / "servers.json"
        reg.write_text(json.dumps({"servers": [
            {"host": "localhost", "port": 1, "name": "Dead"},
            {"host": "localhost", "port": httpserver.port, "name": "Alive"},
        ]}) + "\n")

        with pytest.raises(SystemExit) as exc:
            main(["--servers", str(reg), "-l"])
        assert exc.value.code == 1

        out = capsys.readouterr().out
        assert "✗ Dead (localhost:1) — connection refused" in out
        assert "Alive" in out
        assert "have-m" in out

    def test_no_args_prints_usage_exits_0(self, capsys):
        main([])
        assert "usage:" in capsys.readouterr().out
