import httpx

from opencode_config.domain.entities import Server, Model


class HttpLemonadeClient:
    def __init__(self, client: httpx.Client | None = None, timeout: int = 30):
        self._client = client or httpx.Client()
        self._timeout = timeout

    def fetch_models(self, server: Server) -> list[Model]:
        url = f"http://{server.host}:{server.port}/api/v1/models"
        resp = self._client.get(url, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
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
