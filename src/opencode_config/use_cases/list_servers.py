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
    servers = [s for s in server_registry.load_servers() if s.enabled]
    result = []
    for server in servers:
        name = server.name or f"{server.host}:{server.port}"
        try:
            models = clients[server.type].fetch_models(server)
        except ServerError as exc:
            result.append({
                "name": name,
                "host": server.host,
                "port": server.port,
                "models": [],
                "error": exc.cause,
            })
            continue
        chat_models = [
            m for m in models
            if is_chat_model(m) and (show_all or m.downloaded)
        ]
        result.append({
            "name": name,
            "host": server.host,
            "port": server.port,
            "models": chat_models,
            "error": None,
        })
    return result
