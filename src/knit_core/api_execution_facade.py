from dataclasses import dataclass, field
from typing import Any, Optional

from .mock_utils import NOT_MOCK


@dataclass
class ApiResponse:
    status_code: int
    body: Any = None
    headers: dict = field(default_factory=dict)


@dataclass
class RetryConfig:
    max_attempts: int = 3


DEFAULT_RETRY = RetryConfig()


class ApiExecutionFacade:

    @staticmethod
    def execute(
            context: Any,
            integration_id: str,
            method: str,
            path: str,
            body: Optional[Any] = None,            # dict/list (JSON) or str (sent as is: a SOAP/XML envelope)
            headers: Optional[dict] = None,
            content_type: str = "application/json",
            app_base_url: Optional[str] = None,
            timeout: int = 30,
            retry: RetryConfig = DEFAULT_RETRY,
            healing: Optional[Any] = None,
            path_template: Optional[str] = None,
    ) -> ApiResponse:
        """Call an app's API through its integration. `path` is the part after the vendor base URL, query string included.

        Mock mode (context["mock_mode"] truthy): returns the fixture found at
        context["mock_io"]["api"][integration_id]["{METHOD} {path without query}"]. A fixture is one dict
        ({"status_code", "body", "headers"?}) returned on every call, or a list consumed one entry per call (for paging).
        A call with no fixture raises: a step calling something outside its expected set is a bug worth catching."""
        if context and context.get("mock_mode"):
            key = f"{method} {path.split('?')[0]}"
            fixture = (context.get("mock_io") or {}).get("api", {}).get(integration_id, {}).get(key)
            if fixture is None:
                raise RuntimeError(f"No mock fixture for integration_id={integration_id} {method} {path} — unexpected call in mock mode")
            if isinstance(fixture, list) and not fixture:
                raise RuntimeError(f"Mock fixture for integration_id={integration_id} {key} is used up — more calls than fixtures supplied")
            entry = fixture.pop(0) if isinstance(fixture, list) else fixture
            return ApiResponse(status_code=entry["status_code"], body=entry.get("body"), headers=entry.get("headers", {}))
        raise RuntimeError(NOT_MOCK)
