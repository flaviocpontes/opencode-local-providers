from opencode_config.domain.ports import (
    ServerError,
    ModelServerClient,
    ServerRegistryPort,
)
from opencode_config.use_cases.helpers import is_chat_model


def list_servers(
    server_registry: ServerRegistryPort,
    clients: dict[str, ModelServerClient],
    show_all: bool = False,
) -> list[dict]:
    result = []
    for server in server_registry.load_servers():
        base = {
            "id": server.id,
            "name": server.name or f"{server.host}:{server.port}",
            "host": server.host,
            "port": server.port,
            "type": server.type,
            "enabled": server.enabled,
            "models": [],
            "error": None,
        }
        if not server.enabled:
            result.append(base)
            continue
        try:
            models = clients[server.type].fetch_models(server)
        except ServerError as exc:
            base["error"] = exc.cause
            result.append(base)
            continue
        base["models"] = [
            m for m in models
            if is_chat_model(m) and (show_all or m.downloaded)
        ]
        result.append(base)
    return result
