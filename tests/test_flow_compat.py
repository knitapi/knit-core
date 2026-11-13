"""flow_compat in front of a stand-in for the runner's live, sync-named SDK. The stand-in below is deliberately written with the
OLD names (sync_id, get_sync_hash, log_sync_event) because that is what the runner has today."""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from flow_compat import LOGGER_METHODS, STATE_METHODS, flow_view  # noqa: E402


class LiveState:
    def __init__(self):
        self.hashes = {}

    def get_state(self, project_id, sync_id, step_id, key):
        return ("state", project_id, sync_id, step_id, key)

    def get_sync_hash(self, project_id, sync_id, record_id):
        return self.hashes.get((project_id, sync_id, record_id))

    def set_sync_hash(self, project_id, sync_id, record_id, hash_value):
        self.hashes[(project_id, sync_id, record_id)] = hash_value


class LiveLogger:
    def __init__(self):
        self.events = []

    def log_sync_event(self, sync_id, log_type, duration_ms, record_id=None, status=None):
        self.events.append((sync_id, log_type, duration_ms, record_id, status))

    def info(self, message, **kwargs):
        self.events.append(("info", message))


class LiveStore:
    def upload_json(self, project_id, sync_id, key, data):
        return f"{project_id}/{sync_id}/{key}"


_state = LiveState()
_logger = LiveLogger()
get_sync_state = lambda context=None: _state                       # noqa: E731
get_logger = lambda project_id=None, env=None, account_id=None, context=None: _logger   # noqa: E731
get_object_store = lambda context=None: LiveStore()                 # noqa: E731

get_state_store = flow_view(get_sync_state, STATE_METHODS)
flow_logger = flow_view(get_logger, LOGGER_METHODS)
flow_store = flow_view(get_object_store)


def test_flow_names_run_the_live_methods():
    st = get_state_store({})
    st.set_flow_hash("p", "f1", "r1", "h")
    assert _state.hashes[("p", "f1", "r1")] == "h"                    # it reached the live store
    assert st.get_flow_hash("p", "f1", "r1") == "h"


def test_keyword_flow_id_becomes_the_live_keyword():
    st = get_state_store({})
    assert st.get_state("p", flow_id="f1", step_id="s", key="k") == ("state", "p", "f1", "s", "k")
    flow_logger().log_flow_event(flow_id="f2", log_type="RECORD_STATUS", duration_ms=1, record_id="r")
    assert _logger.events[-1] == ("f2", "RECORD_STATUS", 1, "r", None)
    assert flow_store().upload_json("p", flow_id="f3", key="k", data={}) == "p/f3/k"


def test_old_names_and_positional_calls_still_work():
    st = get_state_store({})
    assert st.get_sync_hash("p", "f1", "r1") == "h"                   # a flow deployed before the rename
    assert st.get_state("p", sync_id="f1", step_id="s", key="k") == ("state", "p", "f1", "s", "k")
    flow_logger().log_flow_event("f4", "X", 0)
    assert _logger.events[-1][0] == "f4"
    flow_logger().info("hello")                                       # methods with no id pass through
    assert _logger.events[-1] == ("info", "hello")


def test_signatures_show_the_flow_names():
    st = get_state_store({})
    assert list(inspect.signature(st.get_state).parameters) == ["project_id", "flow_id", "step_id", "key"]
    assert list(inspect.signature(flow_logger().log_flow_event).parameters)[0] == "flow_id"
    assert "get_flow_hash" in dir(st) and "get_sync_hash" in dir(st)


def test_both_names_at_once_is_left_to_the_live_code():
    st = get_state_store({})
    with pytest.raises(TypeError):
        st.get_state("p", flow_id="a", sync_id="b", step_id="s", key="k")