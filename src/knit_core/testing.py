"""Small helpers for tests of step code in mock mode."""
import asyncio
import copy
from typing import Any, Optional


def make_context(api: Optional[dict] = None, execution_id: str = "exec-1", **extra) -> dict:
    """A mock-mode context. `api` is {integration_id: {"GET /path": fixture_or_list}}."""
    ctx = {"mock_mode": True, "execution_id": execution_id, "mock_io": {"api": copy.deepcopy(api or {})}}
    ctx.update(extra)
    return ctx


def rearm(context: dict, integration_id: str, key: str, fixture: Any) -> None:
    """Put a fresh fixture back for one endpoint (fixture lists are consumed as they are used)."""
    context["mock_io"]["api"].setdefault(integration_id, {})[key] = copy.deepcopy(fixture)


def run_step(step, context: dict, integration_ids: dict, step_context: Optional[dict] = None,
             user_input: Optional[dict] = None, sync_id: str = "sync1", project_id: str = "proj1",
             account_id: str = "acct1"):
    """Run one async step the way the runner calls it. Returns (result, step_context)."""
    sc = {} if step_context is None else step_context
    result = asyncio.run(step(user_input or {}, integration_ids, sync_id, project_id, account_id, context, sc))
    return result, sc
