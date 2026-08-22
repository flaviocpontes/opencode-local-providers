"""Adapter tests for JsonOpenCodeConfig — file I/O with temp files."""

import json
from pathlib import Path

import pytest

from opencode_config.adapters.opencode_config import JsonOpenCodeConfig
from opencode_config.domain.ports import ConfigError


class TestOpenCodeConfig:
    def test_load_existing_config(self, tmp_path: Path):
        path = tmp_path / "opencode.json"
        content = {"provider": {"test": {"name": "Test"}}}
        path.write_text(json.dumps(content) + "\n")
        config = JsonOpenCodeConfig(path)
        assert config.load_config() == content

    def test_load_missing_file_returns_empty(self, tmp_path: Path):
        path = tmp_path / "nonexistent.json"
        config = JsonOpenCodeConfig(path)
        assert config.load_config() == {}

    def test_write_config(self, tmp_path: Path):
        path = tmp_path / "opencode.json"
        config = JsonOpenCodeConfig(path)
        config.write_config({"key": "value"})
        assert json.loads(path.read_text()) == {"key": "value"}

    def test_write_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "sub" / "dir" / "opencode.json"
        config = JsonOpenCodeConfig(path)
        config.write_config({"a": 1})
        assert path.exists()
        assert json.loads(path.read_text()) == {"a": 1}

    def test_invalid_json_raises_config_error(self, tmp_path: Path):
        path = tmp_path / "opencode.json"
        original = "{broken"
        path.write_text(original)
        with pytest.raises(ConfigError) as exc_info:
            JsonOpenCodeConfig(path).load_config()
        assert str(path) in str(exc_info.value)
        assert "nothing was written" in str(exc_info.value)
        assert path.read_text() == original
