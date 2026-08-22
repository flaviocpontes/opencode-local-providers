import json
from pathlib import Path

from opencode_config.domain.ports import ConfigError


class JsonOpenCodeConfig:
    def __init__(self, path: Path):
        self._path = path

    def load_config(self) -> dict:
        if not self._path.exists():
            return {}
        raw = self._path.read_text()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"could not parse {self._path}: {exc.msg} — nothing was written"
            ) from exc

    def write_config(self, config: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(config, indent=2) + "\n")
