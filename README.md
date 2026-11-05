# knit-core

The Knit core SDK for sync step code. A step imports it to keep saved state, store large data, log, call apps through an
integration and raise errors the runner understands:

```python
from knit_core import get_sync_state, get_object_store, get_logger, ApiExecutionFacade, TerminalSyncError, TransientSyncError
```

## Install

```
pip install knit-core
```

For development of this package: `pip install -e ".[dev]"` and `pytest`.

## Test your steps locally (mock mode)

Everything here runs in memory. Set `context["mock_mode"] = True` and supply fixtures:

```python
from knit_core.testing import make_context, run_step

ctx = make_context({"int_1": {"GET /v1/things": {"status_code": 200, "body": {"data": []}}}})
result, step_context = run_step(my_step, ctx, {"source": "int_1"})
```

- `context["mock_io"]["api"][integration_id]["GET /path"]` is one fixture dict, or a list consumed one entry per call.
- State, the object store and logs live on `context`, so they survive from one step to the next. Reuse the same `context`.
- A call with no fixture raises, so unexpected calls are caught.
- Outside mock mode the SDK raises: real calls only run on Knit's runner, where the same names are backed by the real services.
- `get_mock_logs(context)` returns every log record written so far.

## What is in the package

`get_sync_state`, `get_object_store`, `get_logger`, `get_mock_logs`, `ApiExecutionFacade`, `execute_dw_query`,
`execute_dw_write`, `knit_mail`, `SyncError`, `TerminalSyncError`, `TransientSyncError`, and `knit_core.testing`
(`make_context`, `rearm`, `run_step`).

## For the runner (not part of the published package)

`module_alias.py` makes the runner's package importable as `knit_core` and `weavex_core` with the same module objects
(`install_alias("knit_core", "weavex_core")` today, the reverse after a rename). `tests/test_public_surface.py` checks that
the runner and this package expose the same names and call shapes: run it with `SURFACE_MODULE=weavex_core`.
