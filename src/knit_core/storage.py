import base64
from abc import ABC, abstractmethod
from typing import Any, Optional

from .mock_utils import NOT_MOCK, get_mock_backing


class ObjectStore(ABC):
    """Object storage for data too big for state or step_context. Objects belong to (project_id, sync_id)."""

    @abstractmethod
    def upload_json(self, project_id: str, sync_id: str, key: str, data: Any) -> str:
        """Stores data and returns a URI string."""

    @abstractmethod
    def download_json(self, project_id: str, sync_id: str, uri: str) -> Any:
        """Returns the data at a URI string."""

    @abstractmethod
    def delete_json(self, project_id: str, sync_id: str, uri: str) -> bool:
        """Deletes an object. Returns True if something was deleted."""

    @abstractmethod
    def upload_report(self, project_id: str, sync_id: str, context: dict, file_content: bytes, extension: str) -> str:
        """Stores a report file and returns its URI."""

    @abstractmethod
    def download_report(self, project_id: str, sync_id: str, context: dict, uri: str) -> bytes:
        """Returns the raw bytes of a report file."""

    @abstractmethod
    def get_report_presigned_url(self, project_id: str, sync_id: str, context: dict, uri: str,
                                 expiration_seconds: int = 3600) -> str:
        """Returns a temporary public URL for a report file."""


class MockObjectStore(ObjectStore):
    """In-memory store kept on `context`. Reports are stored base64-encoded so context stays JSON-safe. The same
    project/sync ownership check as the real store applies, so leaking the wrong ids fails in mock mode too."""

    def __init__(self, backing: dict):
        self._json_store: dict = backing["json_store"]
        self._report_store: dict = backing["report_store"]

    @staticmethod
    def _check_prefix(project_id, sync_id, blob_path, uri, exc=ValueError):
        if not blob_path.startswith(f"{project_id}/{sync_id}/"):
            raise exc(f"Security mismatch: URI {uri} does not belong to Project: {project_id}, Sync: {sync_id}")

    def upload_json(self, project_id, sync_id, key, data):
        full_path = f"{project_id}/{sync_id}/{key}"
        self._json_store[full_path] = data
        return f"mock://{full_path}"

    def download_json(self, project_id, sync_id, uri):
        if not uri.startswith("mock://"):
            raise ValueError(f"Invalid mock URI: {uri}. Must start with mock://")
        full_path = uri.replace("mock://", "")
        self._check_prefix(project_id, sync_id, full_path, uri)
        if full_path not in self._json_store:
            raise ValueError(f"MockObjectStore: no object at {uri}")
        return self._json_store[full_path]

    def delete_json(self, project_id, sync_id, uri):
        if not uri.startswith("mock://"):
            raise ValueError(f"Invalid mock URI: {uri}. Must start with mock://")
        full_path = uri.replace("mock://", "")
        self._check_prefix(project_id, sync_id, full_path, uri, exc=PermissionError)
        return self._json_store.pop(full_path, None) is not None

    def upload_report(self, project_id, sync_id, context, file_content, extension):
        full_path = f"{project_id}/{sync_id}/reports/mock_mocktime_report.{extension}"
        self._report_store[full_path] = base64.b64encode(file_content).decode("ascii")
        return f"mock://{full_path}"

    def download_report(self, project_id, sync_id, context, uri):
        full_path = uri.replace("mock://", "")
        if full_path not in self._report_store:
            raise ValueError(f"MockObjectStore: no report at {uri}")
        return base64.b64decode(self._report_store[full_path])

    def get_report_presigned_url(self, project_id, sync_id, context, uri, expiration_seconds=3600):
        return f"mock-presigned://{uri}"


def get_object_store(context: Optional[dict] = None) -> ObjectStore:
    """The object store for this run. Locally this is the in-memory mock (context['mock_mode'] must be true)."""
    if context and context.get("mock_mode"):
        return MockObjectStore(get_mock_backing(context, "object_store", lambda: {"json_store": {}, "report_store": {}}))
    raise RuntimeError(NOT_MOCK)
