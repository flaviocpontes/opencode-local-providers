from typing import Protocol, runtime_checkable

from opencode_config.domain.entities import Server, Model


@runtime_checkable
class LemonadeClient(Protocol):
    def fetch_models(self, server: Server) -> list[Model]: ...


@runtime_checkable
class ServerRegistryPort(Protocol):
    def load_servers(self) -> list[Server]: ...


@runtime_checkable
class OpenCodeConfigPort(Protocol):
    def load_config(self) -> dict: ...

    def write_config(self, config: dict) -> None: ...
