import json
from pathlib import Path

class JsonOpenCodeConfig:
    def __init__(self, path: Path):
        self._path = path

    def load_config(self) -> dict:
        if not self._path.exists():
            return {}
        raw = self._path.read_text()
        return json.loads(raw)

    def write_config(self, config: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(config, indent=2) + "\n")
