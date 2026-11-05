import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from .mock_utils import NOT_MOCK, get_mock_backing


class StateStore(ABC):
    """Saved state for a sync: small values (watermarks, ids) and per-record hashes. Scoped by (project_id, sync_id, ...),
    so two syncs of the same project never share state."""

    @abstractmethod
    def get_state(self, project_id: str, sync_id: str, step_id: str, key: str) -> Any: ...

    @abstractmethod
    def set_state(self, project_id: str, sync_id: str, step_id: str, key: str, value: Any) -> None: ...

    @abstractmethod
    def delete_state(self, project_id: str, sync_id: str, step_id: str, key: str) -> None: ...

    @abstractmethod
    def get_sync_hash(self, project_id: str, sync_id: str, record_id: str) -> Optional[str]: ...

    @abstractmethod
    def set_sync_hash(self, project_id: str, sync_id: str, record_id: str, hash_value: str) -> None: ...

    @abstractmethod
    def delete_sync_hash(self, project_id: str, sync_id: str, record_id: str) -> None: ...

    @abstractmethod
    def create_sync_hash(self, project_id: str, sync_id: str, record_id: str, obj: dict) -> str: ...


class MockStateStore(StateStore):
    """In-memory state kept on `context`, so a new instance per call still sees what earlier steps wrote."""

    def __init__(self, backing: dict):
        self._state = backing["state"]
        self._sync_hashes = backing["sync_hashes"]

    @staticmethod
    def _state_key(project_id, sync_id, step_id, key) -> str:
        return f"{project_id}|{sync_id}|{step_id}|{key}"

    @staticmethod
    def _hash_key(project_id, sync_id, record_id) -> str:
        return f"{project_id}|{sync_id}|{record_id}"

    def get_state(self, project_id, sync_id, step_id, key):
        return self._state.get(self._state_key(project_id, sync_id, step_id, key))

    def set_state(self, project_id, sync_id, step_id, key, value):
        self._state[self._state_key(project_id, sync_id, step_id, key)] = value

    def delete_state(self, project_id, sync_id, step_id, key):
        self._state.pop(self._state_key(project_id, sync_id, step_id, key), None)

    def get_sync_hash(self, project_id, sync_id, record_id):
        return self._sync_hashes.get(self._hash_key(project_id, sync_id, record_id))

    def set_sync_hash(self, project_id, sync_id, record_id, hash_value):
        self._sync_hashes[self._hash_key(project_id, sync_id, record_id)] = hash_value

    def delete_sync_hash(self, project_id, sync_id, record_id):
        self._sync_hashes.pop(self._hash_key(project_id, sync_id, record_id), None)

    def create_sync_hash(self, project_id, sync_id, record_id, obj: dict) -> str:
        serialized = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_sync_state(context: Optional[dict] = None) -> StateStore:
    """The state store for this run. Locally this is the in-memory mock (context['mock_mode'] must be true)."""
    if context and context.get("mock_mode"):
        return MockStateStore(get_mock_backing(context, "state_store", lambda: {"state": {}, "sync_hashes": {}}))
    raise RuntimeError(NOT_MOCK)
