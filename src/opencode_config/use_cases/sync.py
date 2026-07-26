from opencode_config.domain.ports import LemonadeClient, ServerRegistryPort, OpenCodeConfigPort
from opencode_config.use_cases.helpers import is_chat_model, model_to_entry


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def sync_models(
    server_registry: ServerRegistryPort,
    lemonade: LemonadeClient,
    opencode_config: OpenCodeConfigPort,
) -> list[str]:
    servers = [s for s in server_registry.load_servers() if s.enabled]
    providers: dict = {}
    summary: list[str] = []

    for server in servers:
        key = slugify(server.name) if server.name else slugify(server.host)
        name = server.name or f"Lemonade ({server.host})"
        base_url = f"http://{server.host}:{server.port}/api/v1"

        models = lemonade.fetch_models(server)
        chat_models = [m for m in models if is_chat_model(m)]
        summary.append(f"{key}: {len(chat_models)} models")

        models_dict = {}
        for m in chat_models:
            models_dict[m.id] = model_to_entry(m)

        providers[key] = {
            "npm": "@ai-sdk/openai-compatible",
            "name": name,
            "options": {"baseURL": base_url},
            "models": models_dict,
        }

    config = opencode_config.load_config()
    config.setdefault("provider", {}).update(providers)
    opencode_config.write_config(config)

    return summary
