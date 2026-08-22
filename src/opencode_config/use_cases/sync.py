from dataclasses import dataclass, field

from opencode_config.domain.ports import (
    ServerError,
    ModelServerClient,
    ServerRegistryPort,
    OpenCodeConfigPort,
)
from opencode_config.domain.entities import Server
from opencode_config.use_cases.helpers import build_provider_entry


def slugify(name: str) -> str:
    return name.lower().replace(" ", "-")


def provider_key(server: Server) -> str:
    return server.id or slugify(server.name or server.host)


@dataclass
class SyncResult:
    summary: list[str]
    config: dict
    failures: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    wrote: bool = True


def sync_models(
    server_registry: ServerRegistryPort,
    clients: dict[str, ModelServerClient],
    opencode_config: OpenCodeConfigPort,
    dry_run: bool = False,
    show_all: bool = False,
) -> SyncResult:
    servers = [s for s in server_registry.load_servers() if s.enabled]
    if not servers:
        return SyncResult(
            summary=["no enabled servers — nothing to do"],
            config=opencode_config.load_config(),
            wrote=False,
        )

    providers: dict = {}
    summary: list[str] = []
    failures: list[tuple[str, str]] = []
    warnings: list[str] = []

    for server in servers:
        key = provider_key(server)
        try:
            models = clients[server.type].fetch_models(server)
        except ServerError as exc:
            failures.append((exc.server_label, exc.cause))
            continue
        entry, entry_warnings = build_provider_entry(server, models, show_all)
        warnings.extend(entry_warnings)
        summary.append(f"{key}: {len(entry['models'])} models")
        providers[key] = entry

    config = opencode_config.load_config()
    config.setdefault("provider", {}).update(providers)
    if not dry_run:
        opencode_config.write_config(config)

    return SyncResult(
        summary=summary, config=config, failures=failures, warnings=warnings
    )
