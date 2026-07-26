from opencode_config.domain.ports import LemonadeClient, ServerRegistryPort
from opencode_config.use_cases.helpers import is_chat_model


def list_servers(
    server_registry: ServerRegistryPort,
    lemonade: LemonadeClient,
) -> list[dict]:
    servers = [s for s in server_registry.load_servers() if s.enabled]
    result = []
    for server in servers:
        name = server.name or f"{server.host}:{server.port}"
        models = lemonade.fetch_models(server)
        chat_models = [m for m in models if is_chat_model(m)]
        result.append({
            "name": name,
            "host": server.host,
            "port": server.port,
            "models": chat_models,
        })
    return result
