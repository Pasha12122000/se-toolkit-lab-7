from dataclasses import dataclass

import httpx

from config import Settings


TIMEOUT_SECONDS = 10.0


@dataclass
class BackendError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


class LmsApiClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.lms_api_base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {settings.lms_api_key}"}

    async def get_items(self) -> list[dict]:
        return await self._get_json("/items/")

    async def get_pass_rates(self, lab: str) -> list[dict]:
        return await self._get_json("/analytics/pass-rates", params={"lab": lab})

    async def _get_json(
        self, path: str, params: dict[str, str] | None = None
    ) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self._base_url}{path}",
                    headers=self._headers,
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            reason = exc.response.reason_phrase
            raise BackendError(
                f"Backend error: HTTP {status_code} {reason}."
            ) from exc
        except httpx.ConnectError as exc:
            raise BackendError(
                f"Backend error: connection refused ({self._base_url}). "
                "Check that the services are running."
            ) from exc
        except httpx.TimeoutException as exc:
            raise BackendError(
                f"Backend error: request to {self._base_url} timed out."
            ) from exc
        except httpx.RequestError as exc:
            raise BackendError(
                f"Backend error: {exc.__class__.__name__}: {exc}."
            ) from exc
