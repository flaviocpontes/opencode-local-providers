import json
from pathlib import Path

from opencode_config.domain.entities import Server


class JsonServerRegistry:
    def __init__(self, path: Path):
        self._path = path

    def load_servers(self) -> list[Server]:
        if not self._path.exists():
            return []
        raw = self._path.read_text()
        data = json.loads(raw)
        return [
            Server(
                host=entry["host"],
                port=entry.get("port", 13305),
                name=entry.get("name"),
                enabled=entry.get("enabled", True),
            )
            for entry in data.get("servers", [])
        ]
