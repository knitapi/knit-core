"""The public names and call shapes agents write against. Run it against any implementation of the SDK:

    SURFACE_MODULE=knit_core pytest tests/test_public_surface.py      (the public package, the default)
    SURFACE_MODULE=weavex_core pytest tests/test_public_surface.py    (the runner's package, to catch drift)
"""
import importlib
import inspect
import os

import pytest

mod = importlib.import_module(os.environ.get("SURFACE_MODULE", "knit_core"))

NAMES = ["get_sync_state", "get_object_store", "get_logger", "get_mock_logs", "ApiExecutionFacade", "execute_dw_query",
         "execute_dw_write", "knit_mail", "SyncError", "TerminalSyncError", "TransientSyncError"]


def params(fn):
    return list(inspect.signature(fn).parameters)


@pytest.mark.parametrize("name", NAMES)
def test_name_is_exported(name):
    assert hasattr(mod, name), f"{mod.__name__} does not export {name}"


def test_error_hierarchy():
    assert issubclass(mod.TerminalSyncError, mod.SyncError) and issubclass(mod.TransientSyncError, mod.SyncError)


def test_call_shapes():
    assert params(mod.get_sync_state) == ["context"]
    assert params(mod.get_object_store) == ["context"]
    assert params(mod.get_logger) == ["project_id", "env", "account_id", "context"]
    assert params(mod.get_mock_logs) == ["context"]
    assert params(mod.ApiExecutionFacade.execute)[:6] == ["context", "integration_id", "method", "path", "body", "headers"]
    assert "content_type" in params(mod.ApiExecutionFacade.execute) and "timeout" in params(mod.ApiExecutionFacade.execute)
    assert params(mod.knit_mail.email) == ["context", "to", "subject", "html_content", "attachment"]
    assert params(mod.execute_dw_query)[:3] == ["context", "integration_id", "query"]
    assert params(mod.execute_dw_write)[:4] == ["context", "integration_id", "table", "rows"]


def test_state_and_store_methods():
    state = [n for n in dir(mod.get_sync_state({"mock_mode": True})) if not n.startswith("_")]
    for method in ("get_state", "set_state", "delete_state", "get_sync_hash", "set_sync_hash", "delete_sync_hash", "create_sync_hash"):
        assert method in state
    assert params(mod.get_sync_state({"mock_mode": True}).get_state) == ["project_id", "sync_id", "step_id", "key"]
    store = [n for n in dir(mod.get_object_store({"mock_mode": True})) if not n.startswith("_")]
    for method in ("upload_json", "download_json", "delete_json", "upload_report", "download_report", "get_report_presigned_url"):
        assert method in store
    logger = mod.get_logger(context={"mock_mode": True})
    for method in ("log_sync_event", "log_api_traffic", "log_billable_event", "info", "warning", "error", "debug"):
        assert hasattr(logger, method)
    assert "sync_id" in params(logger.log_sync_event) and "log_type" in params(logger.log_sync_event)
