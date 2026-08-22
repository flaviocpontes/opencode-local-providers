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


@runtime_checkable
class OpenCodeConfigPort(Protocol):
    def load_config(self) -> dict: ...

    def write_config(self, config: dict) -> None: ...
