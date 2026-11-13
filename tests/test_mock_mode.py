import pytest

from knit_core import (ApiExecutionFacade, FlowError, TerminalFlowError, TransientFlowError, execute_dw_query,
                       execute_dw_write, get_logger, get_mock_logs, get_object_store, get_state_store, knit_mail)
from knit_core.testing import make_context, rearm, run_step


def test_state_survives_new_instances_and_is_scoped_by_flow():
    ctx = make_context()
    get_state_store(ctx).set_state("p", "s1", "step", "watermark", "2026-01-01")
    assert get_state_store(ctx).get_state("p", "s1", "step", "watermark") == "2026-01-01"
    assert get_state_store(ctx).get_state("p", "s2", "step", "watermark") is None       # another flow, no shared state
    get_state_store(ctx).delete_state("p", "s1", "step", "watermark")
    assert get_state_store(ctx).get_state("p", "s1", "step", "watermark") is None


def test_hashes_are_stable_and_scoped():
    ctx = make_context()
    st = get_state_store(ctx)
    h = st.create_flow_hash("p", "s1", "r1", {"b": 2, "a": 1})
    assert h == st.create_flow_hash("p", "s1", "r1", {"a": 1, "b": 2})
    assert st.get_flow_hash("p", "s1", "r1") is None
    st.set_flow_hash("p", "s1", "r1", h)
    assert get_state_store(ctx).get_flow_hash("p", "s1", "r1") == h and get_state_store(ctx).get_flow_hash("p", "s2", "r1") is None
    st.delete_flow_hash("p", "s1", "r1")
    assert st.get_flow_hash("p", "s1", "r1") is None


def test_object_store_round_trip_and_ownership_check():
    ctx = make_context()
    store = get_object_store(ctx)
    uri = store.upload_json("p", "s1", "run/a.json", [{"id": 1}])
    assert get_object_store(ctx).download_json("p", "s1", uri) == [{"id": 1}]
    with pytest.raises(ValueError, match="Security mismatch"):
        store.download_json("p", "other-flow", uri)
    with pytest.raises(PermissionError):
        store.delete_json("p", "other-flow", uri)
    assert store.delete_json("p", "s1", uri) is True and store.delete_json("p", "s1", uri) is False
    report = store.upload_report("p", "s1", ctx, b"abc", "csv")
    assert store.download_report("p", "s1", ctx, report) == b"abc"
    assert store.get_report_presigned_url("p", "s1", ctx, report).startswith("mock-presigned://")


def test_api_fixtures_single_list_and_missing():
    ctx = make_context({"app": {"GET /things": [{"status_code": 200, "body": {"n": 1}}, {"status_code": 429}],
                                "POST /things": {"status_code": 201, "body": {"id": "x"}}}})
    call = lambda m, p: ApiExecutionFacade.execute(ctx, "app", m, p)
    assert call("GET", "/things?limit=10").body == {"n": 1}
    assert call("GET", "/things").status_code == 429
    assert call("POST", "/things").body == {"id": "x"} and call("POST", "/things").body == {"id": "x"}
    with pytest.raises(RuntimeError, match="used up"):
        call("GET", "/things")                                                          # list used up
    with pytest.raises(RuntimeError, match="No mock fixture"):
        call("GET", "/other")
    rearm(ctx, "app", "GET /things", [{"status_code": 200, "body": {"n": 2}}])
    assert call("GET", "/things").body == {"n": 2}


def test_logger_records_and_does_not_grow_exponentially():
    ctx = make_context()
    logger = get_logger(project_id="p", account_id="a", context=ctx)
    for i in range(12):
        logger.log_flow_event(flow_id="s1", log_type="RECORD_STATUS", duration_ms=0, record_id=str(i), status="SUCCESS", context=ctx)
    logger.info("hello", context=ctx)
    records = get_mock_logs(ctx)
    assert len(records) == 13 and records[0]["record_id"] == "0" and records[-1]["message"] == "hello"
    assert max(len(str(r)) for r in records) < 2000


def test_mail_and_warehouse_mocks():
    ctx = make_context()
    assert knit_mail.email(ctx, "a@b.c", "Hi", "<p>x</p>")["status"] == "mocked"
    ctx["mock_io"]["dw"] = {"wh": {"/query": {"rows": [{"a": 1}], "row_count": 1, "columns": ["a"]},
                                   "/write": {"rows_written": 2, "rows_failed": 0}}}
    assert execute_dw_query(ctx, "wh", "select 1").rows == [{"a": 1}]
    assert execute_dw_write(ctx, "wh", "t", [{"a": 1}, {"a": 2}]).rows_written == 2
    assert execute_dw_write(ctx, "wh", "t", []).rows_written == 0


def test_outside_mock_mode_fails_with_a_clear_message():
    for call in (lambda: get_state_store({}), lambda: get_object_store(None),
                 lambda: ApiExecutionFacade.execute({}, "app", "GET", "/x"), lambda: knit_mail.email({}, "a", "b", "c")):
        with pytest.raises(RuntimeError, match="mock_mode"):
            call()


def test_errors_carry_the_retry_decision():
    assert TerminalFlowError("x").non_retryable is True and TransientFlowError("x").non_retryable is False
    assert issubclass(TerminalFlowError, FlowError) and str(TerminalFlowError("bad creds")) == "bad creds"


def test_a_step_runs_through_the_test_helper():
    async def step(user_input, integration_ids, flow_id, project_id, account_id, context, step_context):
        r = ApiExecutionFacade.execute(context, integration_ids["app"], "GET", "/ping")
        step_context["ping"] = r.body
        return {"ok": r.status_code == 200}

    ctx = make_context({"int_1": {"GET /ping": {"status_code": 200, "body": "pong"}}})
    result, sc = run_step(step, ctx, {"app": "int_1"})
    assert result == {"ok": True} and sc == {"ping": "pong"}