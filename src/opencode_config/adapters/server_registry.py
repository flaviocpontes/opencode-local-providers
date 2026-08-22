import json
from dataclasses import replace
from pathlib import Path

from opencode_config.domain.entities import Server, DEFAULT_PORTS
from opencode_config.domain.ports import ConfigError


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def _mint_id(entry: dict, taken: set[str]) -> str:
    base = slugify(entry.get("name") or entry["host"])
    candidate = base
    n = 2
    while candidate in taken:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


class JsonServerRegistry:
    def __init__(self, path: Path):
        self._path = path

    def _load_raw(self) -> dict:
        if not self._path.exists():
            return {"servers": []}
        try:
            data = json.loads(self._path.read_text())
        except json.JSONDecodeError as exc:
            raise ConfigError(f"could not parse {self._path}: {exc.msg}") from exc
        entries = data.get("servers", [])
        for i, entry in enumerate(entries):
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
        # Legacy files without ids adopt the same ids as the old provider-key
        # derivation, so existing opencode.json entries carry over unchanged.
        taken: set[str] = set()
        for entry in entries:
            if not entry.get("id"):
                entry["id"] = _mint_id(entry, taken)
            taken.add(entry["id"])
        return data

    def _save(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2) + "\n")

    def _to_server(self, entry: dict) -> Server:
        server_type = entry.get("type", "lemonade")
        return Server(
            host=entry["host"],
            port=entry.get("port", DEFAULT_PORTS[server_type]),
            name=entry.get("name"),
            enabled=entry.get("enabled", True),
            type=server_type,
            id=entry["id"],
        )

    def load_servers(self) -> list[Server]:
        data = self._load_raw()
        return [self._to_server(e) for e in data.get("servers", [])]

    def add_server(self, server: Server) -> Server:
        data = self._load_raw()
        entries = data.setdefault("servers", [])
        entry: dict = {"id": None, "host": server.host, "port": server.port,
                       "enabled": True, "type": server.type}
        if server.name:
            entry["name"] = server.name
        entry["id"] = _mint_id(entry, {e["id"] for e in entries})
        entries.append(entry)
        self._save(data)
        return replace(server, id=entry["id"], enabled=True)

    def remove_server(self, server_id: str) -> bool:
        data = self._load_raw()
        entries = data.get("servers", [])
        remaining = [e for e in entries if e["id"] != server_id]
        if len(remaining) == len(entries):
            return False
        data["servers"] = remaining
        self._save(data)
        return True

    def set_enabled(self, server_id: str, enabled: bool) -> bool:
        data = self._load_raw()
        for entry in data.get("servers", []):
            if entry["id"] == server_id:
                entry["enabled"] = enabled
                self._save(data)
                return True
        return False
