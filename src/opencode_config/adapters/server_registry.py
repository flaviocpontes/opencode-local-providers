import json
from pathlib import Path

from opencode_config.domain.entities import Server, DEFAULT_PORTS
from opencode_config.domain.ports import ConfigError


class JsonServerRegistry:
    def __init__(self, path: Path):
        self._path = path

    def load_servers(self) -> list[Server]:
        if not self._path.exists():
            return []
        raw = self._path.read_text()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"could not parse {self._path}: {exc.msg}") from exc
        servers = []
        for i, entry in enumerate(data.get("servers", [])):
            if "host" not in entry:
                raise ConfigError(
                    f"{self._path}: server entry #{i + 1} missing 'host'"
                ) from None
            server_type = entry.get("type", "lemonade")
            if server_type not in DEFAULT_PORTS:
                raise ConfigError(
                    f"{self._path}: server entry #{i + 1} has unknown type "
                    f"'{server_type}' (expected one of: {', '.join(sorted(DEFAULT_PORTS))})"
                ) from None
            servers.append(Server(
                host=entry["host"],
                port=entry.get("port", DEFAULT_PORTS[server_type]),
                name=entry.get("name"),
                enabled=entry.get("enabled", True),
                type=server_type,
            ))
        enabled = [s for s in servers if s.enabled]
        if servers and not enabled:
            raise ConfigError(f"no enabled servers in {self._path}") from None
        return enabled
