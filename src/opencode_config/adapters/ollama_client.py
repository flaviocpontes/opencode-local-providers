import re

import httpx

from opencode_config.domain.entities import Server, Model
from opencode_config.domain.ports import ServerError
from opencode_config.adapters.lemonade_client import _short_cause

# Ollama capability -> our Model.labels
CAPABILITY_LABELS = {"vision": "vision", "thinking": "reasoning"}


def _context_from_parameters(parameters: str | None) -> int | None:
    if not parameters:
        return None
    match = re.search(r"^\s*num_ctx\s+(\d+)\s*$", parameters, re.MULTILINE)
    return int(match.group(1)) if match else None


def _context_from_model_info(model_info: dict | None) -> int | None:
    if not model_info:
        return None
    for key, value in model_info.items():
        if key.endswith(".context_length") and isinstance(value, int):
            return value
    return None


class HttpOllamaClient:
    def __init__(self, client: httpx.Client | None = None, timeout: float = 30):
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=5)
        )

    def fetch_models(self, server: Server) -> list[Model]:
        label = server.name or f"{server.host}:{server.port}"
        base = f"http://{server.host}:{server.port}"
        try:
            resp = self._client.get(f"{base}/api/tags")
            resp.raise_for_status()
            tags = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ServerError(label, _short_cause(exc)) from exc
        return [
            self._to_model(item, base)
            for item in tags.get("models", [])
        ]

    # ponytail: sequential /api/show per model — fine for LAN servers with
    # dozens of models; use a small worker pool if anyone lists hundreds.
    def _to_model(self, item: dict, base: str) -> Model:
        model_id = item.get("name") or item.get("model", "")
        capabilities: list = []
        parameters: str | None = None
        model_info: dict | None = None
        try:
            resp = self._client.post(f"{base}/api/show", json={"model": model_id})
            resp.raise_for_status()
            show = resp.json()
            capabilities = show.get("capabilities") or []
            parameters = show.get("parameters")
            model_info = show.get("model_info")
        except (httpx.HTTPError, ValueError):
            pass  # degrade to unenriched — include, never drop

        labels = [CAPABILITY_LABELS[c] for c in capabilities if c in CAPABILITY_LABELS]
        is_chat = not capabilities or "completion" in capabilities
        context = _context_from_parameters(parameters)
        if context is None:
            context = _context_from_model_info(model_info)
        size = item.get("size")
        return Model(
            id=model_id,
            recipe="ollama" if is_chat else "",
            labels=labels,
            max_context_window=context,
            size=size / 1e9 if size is not None else None,
            downloaded=True,
        )
