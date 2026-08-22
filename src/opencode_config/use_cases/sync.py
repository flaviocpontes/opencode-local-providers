from dataclasses import dataclass, field

from opencode_config.domain.ports import (
    ServerError,
    ModelServerClient,
    ServerRegistryPort,
    OpenCodeConfigPort,
)
from opencode_config.use_cases.helpers import is_chat_model, model_to_entry

BASE_URL_PATHS = {"lemonade": "/api/v1", "ollama": "/v1"}


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


@dataclass
class SyncResult:
    summary: list[str]
    config: dict
    failures: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def sync_models(
    server_registry: ServerRegistryPort,
    clients: dict[str, ModelServerClient],
    opencode_config: OpenCodeConfigPort,
    dry_run: bool = False,
    show_all: bool = False,
) -> SyncResult:
    servers = [s for s in server_registry.load_servers() if s.enabled]
    providers: dict = {}
    summary: list[str] = []
    failures: list[tuple[str, str]] = []
    warnings: list[str] = []

    for server in servers:
        key = slugify(server.name) if server.name else slugify(server.host)
        name = server.name or f"{server.type.capitalize()} ({server.host})"
        base_url = f"http://{server.host}:{server.port}{BASE_URL_PATHS[server.type]}"

        try:
            models = clients[server.type].fetch_models(server)
        except ServerError as exc:
            failures.append((exc.server_label, exc.cause))
            continue
        chat_models = [
            m for m in models
            if is_chat_model(m) and (show_all or m.downloaded)
        ]
        summary.append(f"{key}: {len(chat_models)} models")

        models_dict = {}
        for m in chat_models:
            models_dict[m.id] = model_to_entry(m)
            if m.max_context_window and m.max_context_window < 65536:
                warnings.append(
                    f"{m.id}: context {m.max_context_window} < 65536 "
                    f"(opencode wants 64k+)"
                )

        providers[key] = {
            "npm": "@ai-sdk/openai-compatible",
            "name": name,
            "options": {"baseURL": base_url},
            "models": models_dict,
        }

    config = opencode_config.load_config()
    config.setdefault("provider", {}).update(providers)
    if not dry_run:
        opencode_config.write_config(config)

    return SyncResult(
        summary=summary, config=config, failures=failures, warnings=warnings
    )
