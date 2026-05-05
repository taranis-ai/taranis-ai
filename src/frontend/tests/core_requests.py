from dataclasses import dataclass, field, replace
from typing import Any, Mapping

import requests


DEFAULT_CORE_REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_JSON_HEADERS = {"Content-type": "application/json"}


@dataclass(frozen=True)
class CoreRequestClient:
    base_url: str
    access_token: str | None = None
    default_headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int | float = DEFAULT_CORE_REQUEST_TIMEOUT_SECONDS

    def with_access_token(self, access_token: str | None) -> "CoreRequestClient":
        return replace(self, access_token=access_token)

    def build_headers(
        self,
        *,
        authenticated: bool | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        merged_headers = {**DEFAULT_JSON_HEADERS, **self.default_headers}
        should_authenticate = self.access_token is not None if authenticated is None else authenticated
        if should_authenticate:
            if self.access_token is None:
                raise RuntimeError("Authenticated core request requested without an access token")
            merged_headers["Authorization"] = f"Bearer {self.access_token}"
        if headers:
            merged_headers.update(headers)
        return merged_headers

    def request(
        self,
        method: str,
        path: str,
        *,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        authenticated: bool | None = None,
        raise_for_status: bool = True,
        timeout_seconds: int | float | None = None,
    ) -> requests.Response:
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=self.build_headers(authenticated=authenticated, headers=headers),
            json=json_data,
            params=params,
            timeout=timeout_seconds or self.timeout_seconds,
        )
        if raise_for_status:
            response.raise_for_status()
        return response

    def json_request(self, method: str, path: str, **kwargs: Any) -> Any:
        return self.request(method, path, **kwargs).json()

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, **kwargs)
