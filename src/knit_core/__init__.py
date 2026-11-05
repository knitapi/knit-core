"""Knit core SDK: what step code imports to keep saved state, store large data, log, call apps and raise errors.

Locally everything runs in mock mode: set context["mock_mode"] = True and supply fixtures under context["mock_io"]. On Knit's
runner the same imports are backed by the real services.
"""
from .state import get_sync_state
from .storage import get_object_store
from .logger import get_logger
from .mock_utils import get_mock_logs
from .api_execution_facade import ApiExecutionFacade
from .execute_dw import execute_dw_query, execute_dw_write
from . import knit_mail
from .durable import SyncError, TerminalSyncError, TransientSyncError

__version__ = "0.1.0"

__all__ = [
    "get_sync_state", "get_object_store", "get_logger", "get_mock_logs", "ApiExecutionFacade",
    "execute_dw_query", "execute_dw_write", "knit_mail", "SyncError", "TerminalSyncError", "TransientSyncError",
]
