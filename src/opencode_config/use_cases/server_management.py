from dataclasses import dataclass

from opencode_config.domain.ports import (
    ServerError,
    ModelServerClient,
    ServerRegistryPort,
    OpenCodeConfigPort,
)
from opencode_config.domain.entities import Server, DEFAULT_PORTS
from opencode_config.use_cases.helpers import build_provider_entry


@dataclass
class CommandResult:
    ok: bool
    message: str


def add_server(
    server_registry: ServerRegistryPort,
    clients: dict[str, ModelServerClient],
    opencode_config: OpenCodeConfigPort,
    host: str,
    server_type: str = "lemonade",
    port: int | None = None,
    name: str | None = None,
    show_all: bool = False,
) -> CommandResult:
    server = Server(host=host, port=port or DEFAULT_PORTS[server_type],
                    name=name, type=server_type)
    try:
        models = clients[server_type].fetch_models(server)
    except ServerError as exc:
        return CommandResult(False, f"✗ {host}: {exc.cause} — nothing written")

    registered = server_registry.add_server(server)
    entry, _ = build_provider_entry(registered, models, show_all)
    config = opencode_config.load_config()
    config.setdefault("provider", {})[registered.id] = entry
    opencode_config.write_config(config)
    return CommandResult(
        True,
        f"✓ added {registered.id} ({host}:{registered.port}) — "
        f"{len(entry['models'])} chat models written",
    )


def remove_server(
    server_registry: ServerRegistryPort,
    opencode_config: OpenCodeConfigPort,
    server_id: str,
) -> CommandResult:
    if not server_registry.remove_server(server_id):
        return CommandResult(False, f"✗ no server with id '{server_id}'")
    config = opencode_config.load_config()
    if config.get("provider", {}).pop(server_id, None) is not None:
        opencode_config.write_config(config)
    return CommandResult(True, f"✓ removed {server_id}")


def set_server_enabled(
    server_registry: ServerRegistryPort,
    opencode_config: OpenCodeConfigPort,
    server_id: str,
    enabled: bool,
) -> CommandResult:
    if not server_registry.set_enabled(server_id, enabled):
        return CommandResult(False, f"✗ no server with id '{server_id}'")
    config = opencode_config.load_config()
    provider = config.get("provider", {})
    if server_id in provider:
        if enabled:
            provider[server_id].pop("disabled", None)
        else:
            provider[server_id]["disabled"] = True
        opencode_config.write_config(config)
    verb = "enabled" if enabled else "disabled"
    return CommandResult(True, f"✓ {verb} {server_id}")
