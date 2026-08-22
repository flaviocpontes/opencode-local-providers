from dataclasses import dataclass, field


@dataclass
class Server:
    host: str
    port: int = 13305
    name: str | None = None
    enabled: bool = True
    type: str = "lemonade"


DEFAULT_PORTS = {"lemonade": 13305, "ollama": 11434}


@dataclass
class Model:
    id: str
    recipe: str = ""
    labels: list[str] = field(default_factory=list)
    max_context_window: int | None = None
    checkpoint: str | None = None
    size: float | None = None
    downloaded: bool = True
    suggested: bool = False
    created: int | None = None
    image_defaults: dict | None = None


@dataclass
class ProviderConfig:
    key: str
    npm: str = "@ai-sdk/openai-compatible"
    name: str = ""
    options: dict | None = None
    models: list[Model] = field(default_factory=list)
    api_key: str | None = None
    disabled: bool = False
