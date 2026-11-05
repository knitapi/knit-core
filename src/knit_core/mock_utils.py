"""Shared helper for the mock implementations (state, object store, logging).

The mock INSTANCE is rebuilt on every factory call, but the DATA it wraps must survive across every step of one run. The one
object threaded through every step is `context`, so the data lives under context["mock_io"]["_backing"], next to (not inside)
the "api"/"dw"/"knit_mail" fixture sections a test supplies. Everything stored there stays JSON-safe.
"""
from typing import Any, Dict


def get_mock_backing(context: dict, key: str, default_factory) -> Dict[str, Any]:
    """The backing object for `key`, created on first use for this context and reused afterwards.
    `context` must be the SAME object across calls for data to persist between steps."""
    mock_io = context.setdefault("mock_io", {})
    backing_root = mock_io.setdefault("_backing", {})
    if key not in backing_root:
        backing_root[key] = default_factory()
    return backing_root[key]


def get_mock_logs(context: dict) -> list:
    """Every log record written against this context so far, in call order ([] if none)."""
    return ((context.get("mock_io") or {}).get("_backing") or {}).get("logger_records", [])


def context_snapshot_for_logging(context: dict) -> dict:
    """A shallow copy of `context` without "mock_io", for embedding in a log record. Embedding the mock bookkeeping would make
    every record contain all earlier records, and the size would grow exponentially."""
    return {k: v for k, v in (context or {}).items() if k != "mock_io"}


NOT_MOCK = ("knit_core only runs real calls on Knit's runner. For local tests set context['mock_mode'] = True "
            "(and supply fixtures under context['mock_io']).")
