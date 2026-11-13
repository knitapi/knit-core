"""The public names and call shapes agents write against. Run it against any implementation of the SDK:

    SURFACE_MODULE=knit_core pytest tests/test_public_surface.py      (the public package, the default)
    SURFACE_MODULE=weavex_core pytest tests/test_public_surface.py    (the runner's package, to catch drift)
"""
import importlib
import inspect
import os

import pytest

mod = importlib.import_module(os.environ.get("SURFACE_MODULE", "knit_core"))

# Only the local mock-testing helper. Agents use it in tests on their own machine (through knit_core); the runner does not
# need to export it, so it is not required of any other module.
LOCAL_TEST_ONLY = {"get_mock_logs"}
IS_PUBLIC_PACKAGE = mod.__name__ == "knit_core"

NAMES = ["get_state_store", "get_object_store", "get_logger", "get_mock_logs", "ApiExecutionFacade", "execute_dw_query",
         "execute_dw_write", "knit_mail", "FlowError", "TerminalFlowError", "TransientFlowError"]


def params(fn):
    return list(inspect.signature(fn).parameters)


@pytest.mark.parametrize("name", NAMES)
def test_name_is_exported(name):
    if name in LOCAL_TEST_ONLY and not IS_PUBLIC_PACKAGE:
        pytest.skip(f"{name} is local-testing only")
    assert hasattr(mod, name), f"{mod.__name__} does not export {name}"


def test_error_hierarchy():
    assert issubclass(mod.TerminalFlowError, mod.FlowError) and issubclass(mod.TransientFlowError, mod.FlowError)


def test_call_shapes():
    assert params(mod.get_state_store) == ["context"]
    assert params(mod.get_object_store) == ["context"]
    assert params(mod.get_logger) == ["project_id", "env", "account_id", "context"]
    if IS_PUBLIC_PACKAGE:
        assert params(mod.get_mock_logs) == ["context"]
    assert params(mod.ApiExecutionFacade.execute)[:6] == ["context", "integration_id", "method", "path", "body", "headers"]
    assert "content_type" in params(mod.ApiExecutionFacade.execute) and "timeout" in params(mod.ApiExecutionFacade.execute)
    assert params(mod.knit_mail.email) == ["context", "to", "subject", "html_content", "attachment"]
    assert params(mod.execute_dw_query)[:3] == ["context", "integration_id", "query"]
    assert params(mod.execute_dw_write)[:4] == ["context", "integration_id", "table", "rows"]


def test_state_and_store_methods():
    state = [n for n in dir(mod.get_state_store({"mock_mode": True})) if not n.startswith("_")]
    for method in ("get_state", "set_state", "delete_state", "get_flow_hash", "set_flow_hash", "delete_flow_hash", "create_flow_hash"):
        assert method in state
    assert params(mod.get_state_store({"mock_mode": True}).get_state) == ["project_id", "flow_id", "step_id", "key"]
    store = [n for n in dir(mod.get_object_store({"mock_mode": True})) if not n.startswith("_")]
    for method in ("upload_json", "download_json", "delete_json", "upload_report", "download_report", "get_report_presigned_url"):
        assert method in store
    logger = mod.get_logger(context={"mock_mode": True})
    for method in ("log_flow_event", "log_api_traffic", "log_billable_event", "info", "warning", "error", "debug"):
        assert hasattr(logger, method)
    assert "flow_id" in params(logger.log_flow_event) and "log_type" in params(logger.log_flow_event)