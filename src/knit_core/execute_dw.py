"""Data warehouse access for step code (mock mode locally; real calls run on Knit's runner)."""
from dataclasses import dataclass, field
from typing import Optional

from .mock_utils import NOT_MOCK

# ── Result types ───────────────────────────────────────────────────────────────

@dataclass
class DWQueryResult:
    rows:          list[dict]
    row_count:     int
    columns:       list[str]
    bytes_scanned: int = 0
    job_id:        str = ""
    provider:      str = ""
    duration_ms:   int = 0


@dataclass
class DWWriteResult:
    rows_written: int
    rows_failed:  int
    job_id:       str = ""
    provider:     str = ""
    duration_ms:  int = 0


@dataclass
class DatasetInfo:
    name:     str
    location: str = ""


@dataclass
class TableInfo:
    name:      str
    dataset:   str
    full_name: str
    row_count: int = 0


@dataclass
class ColumnInfo:
    name:        str
    type:        str
    mode:        str
    description: str = ""


@dataclass
class TableSchema:
    table:    str
    provider: str
    columns:  list[ColumnInfo] = field(default_factory=list)


@dataclass
class ColumnDefinition:
    name:        str
    type:        str              # generic: string, integer, bigint, float,
    #          boolean, date, timestamp, json
    nullable:    bool = True
    description: str  = ""
    primary_key: bool = False


@dataclass
class CreateTableResult:
    table:       str
    provider:    str
    created:     bool   # False if already existed and if_not_exists=True
    ddl:         str
    duration_ms: int = 0


# ── Query ──────────────────────────────────────────────────────────────────────

def execute_dw_query(
        context:        dict,
        integration_id: str,
        query:          str,
        params:         Optional[dict] = None,
        max_results:    int = 50_000,
        timeout:        int = 120
) -> DWQueryResult:
    """
    Execute a SELECT query against a data warehouse.

    Args:
        context:        Pass as-is from activity params.
        integration_id: integration_ids.get("bigquery") etc.
        query:          SQL with provider-appropriate params.
                          BigQuery:           @param_name
                          Redshift/Snowflake: %(param_name)s
        params:         Query parameters dict.
        max_results:    Max rows to return (default 50k).
        timeout:        Query timeout in seconds (default 120).

    Returns:
        DWQueryResult with rows, row_count, columns, bytes_scanned.
    """
    response = _call("/query", context, integration_id)

    return DWQueryResult(
        rows          = response["rows"],
        row_count     = response["row_count"],
        columns       = response["columns"],
        bytes_scanned = response.get("bytes_scanned", 0),
        job_id        = response.get("job_id", ""),
        provider      = response.get("provider", ""),
        duration_ms   = response.get("duration_ms", 0)
    )


# ── Write ──────────────────────────────────────────────────────────────────────

def execute_dw_write(
        context:           dict,
        integration_id:    str,
        table:             str,
        rows:              list[dict],
        write_mode:        str = "append",
        upsert_keys:       Optional[list[str]] = None,
        s3_integration_id: Optional[str] = None,
        batch_size:        int = 500,
        timeout:           int = 120
) -> DWWriteResult:
    """
    Write rows to a data warehouse table.

    Args:
        context:           Pass as-is from activity params.
        integration_id:    integration_ids.get("bigquery") etc.
        table:             Fully qualified table name.
                             BigQuery:  "project.dataset.table"  or "dataset.table"
                             Redshift:  "schema.table"
                             Snowflake: "database.schema.table"
        rows:              List of dicts — keys are column names.
        write_mode:        "append" | "upsert" | "replace"
        upsert_keys:       Required for write_mode="upsert".
        s3_integration_id: Required for Redshift bulk writes (>=500 rows).
        batch_size:        Rows per batch for inline writes (default 500).
        timeout:           Operation timeout in seconds (default 120).

    Returns:
        DWWriteResult with rows_written, rows_failed, job_id.
    """
    if not rows:
        return DWWriteResult(rows_written=0, rows_failed=0)

    response = _call("/write", context, integration_id)

    return DWWriteResult(
        rows_written = response["rows_written"],
        rows_failed  = response["rows_failed"],
        job_id       = response.get("job_id", ""),
        provider     = response.get("provider", ""),
        duration_ms  = response.get("duration_ms", 0)
    )




def _call(endpoint: str, context: dict, integration_id: str) -> dict:
    """Mock mode: the fixture at context["mock_io"]["dw"][integration_id][endpoint] (a dict, or a list consumed in order)."""
    if (context or {}).get("mock_mode"):
        fixture = (context.get("mock_io") or {}).get("dw", {}).get(integration_id, {}).get(endpoint)
        if fixture is None:
            raise RuntimeError(f"No mock fixture for integration_id={integration_id} DW endpoint {endpoint} — unexpected call in mock mode")
        return fixture.pop(0) if isinstance(fixture, list) else fixture
    raise RuntimeError(NOT_MOCK)
