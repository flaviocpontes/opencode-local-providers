from typing import Protocol, runtime_checkable

from opencode_config.domain.entities import Server, Model


class ConfigError(Exception):
    """A user config file is unreadable, unparseable, or invalid."""


class ServerError(Exception):
    """A Lemonade server could not be reached or returned an error."""

    def __init__(self, server_label: str, cause: str):
        self.server_label = server_label
        self.cause = cause
        super().__init__(f"{server_label}: {cause}")


@runtime_checkable
class ModelServerClient(Protocol):
    def fetch_models(self, server: Server) -> list[Model]: ...


@runtime_checkable
class ServerRegistryPort(Protocol):
    def load_servers(self) -> list[Server]: ...

    def add_server(self, server: Server) -> Server:
        """Persist a new server entry; returns it with the minted id."""
        ...

    def remove_server(self, server_id: str) -> bool:
        """Delete the entry; False if no server has that id."""
        ...

    def set_enabled(self, server_id: str, enabled: bool) -> bool:
        """Flip the entry's enabled flag; False if no server has that id."""
        ...


@runtime_checkable
class OpenCodeConfigPort(Protocol):
    def load_config(self) -> dict: ...

    def write_config(self, config: dict) -> None: ...
