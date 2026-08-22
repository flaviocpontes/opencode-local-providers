import httpx

from opencode_config.domain.entities import Server, Model
from opencode_config.domain.ports import ServerError


def _short_cause(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection refused"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return "invalid response"


class HttpModelServerClient:
    def __init__(self, client: httpx.Client | None = None, timeout: float = 30):
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=5)
        )

    def fetch_models(self, server: Server) -> list[Model]:
        label = server.name or f"{server.host}:{server.port}"
        url = f"http://{server.host}:{server.port}/api/v1/models"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ServerError(label, _short_cause(exc)) from exc
        # ponytail: item missing "id" raises raw KeyError — upstream schema bug, traceback is honest
        return [
            Model(
                id=item["id"],
                recipe=item.get("recipe", ""),
                labels=item.get("labels", []),
                max_context_window=item.get("max_context_window"),
                checkpoint=item.get("checkpoint"),
                size=item.get("size"),
                downloaded=item.get("downloaded", True),
                suggested=item.get("suggested", False),
                created=item.get("created"),
                image_defaults=item.get("image_defaults"),
            )
            for item in data.get("data", [])
        ]
