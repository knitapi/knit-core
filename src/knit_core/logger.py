import json
import sys
from typing import Any, Dict, Optional

from .mock_utils import context_snapshot_for_logging, get_mock_backing


class SyncLogger:
    """Logger for step code. Locally, records are kept in memory (mock mode, read them with get_mock_logs) or printed to
    stdout. On Knit's runner the same calls go to Knit's run monitoring."""

    def __init__(self, project_id: Optional[str], account_id: Optional[str], records: Optional[list]):
        self.project_id = project_id
        self.account_id = account_id
        self._records = records

    def _emit(self, record: Dict[str, Any]):
        record.setdefault("project_id", self.project_id)
        record.setdefault("account_id", self.account_id)
        if self._records is not None:
            self._records.append(record)
        else:
            print(json.dumps(record, default=str), file=sys.stdout)

    def log_api_traffic(self, log_type: str, method: str, url: str, status_code: int, duration_ms: int,
                        req_payload: Dict[str, Any], resp_payload: Dict[str, Any], vendor_name: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None):
        self._emit({"log_table": "API", "log_type": log_type, "method": method, "url": url,
                    "status_code": int(status_code), "duration_ms": int(duration_ms),
                    "request_payload": json.dumps(req_payload or {}), "response_payload": json.dumps(resp_payload or {}),
                    "vendor_name": vendor_name, "api_data": json.dumps(metadata or {}),
                    "context": json.dumps(context_snapshot_for_logging(context), default=str)})

    def log_sync_event(self, sync_id: str, log_type: str, duration_ms: int, record_id: Optional[str] = None,
                       external_id: Optional[str] = None, entity_type: Optional[str] = None, action: Optional[str] = None,
                       status: Optional[str] = None, error_message: Optional[str] = None, vendor_url: Optional[str] = None,
                       vendor_method: Optional[str] = None, vendor_req_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None):
        self._emit({"log_table": "SYNC", "sync_id": sync_id, "log_type": log_type, "duration_ms": int(duration_ms),
                    "record_id": record_id, "external_id": external_id, "entity_type": entity_type, "action": action,
                    "status": status, "error_message": error_message, "vendor_url": vendor_url,
                    "vendor_method": vendor_method, "vendor_request_id": vendor_req_id,
                    "sync_data": json.dumps(metadata or {}),
                    "context": json.dumps(context_snapshot_for_logging(context), default=str)})

    def log_billable_event(self, source: str, resource_id: str, quantity: int, duration_ms: int,
                           metadata: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None,
                           status: str = "SUCCESS", blocking: Optional[bool] = True):
        self._emit({"log_table": "BILLING", "source": source, "resource_id": resource_id, "quantity": int(quantity),
                    "duration_ms": int(duration_ms), "status": status, "metadata": json.dumps(metadata or {}),
                    "context": json.dumps(context_snapshot_for_logging(context), default=str)})

    def _message(self, severity: str, message: str, details: Dict[str, Any]):
        details = dict(details or {})
        if "context" in details:
            details["context"] = json.dumps(context_snapshot_for_logging(details["context"]), default=str)
        self._emit({"severity": severity, "message": message, **details})

    def info(self, message: str, **kwargs):
        self._message("INFO", message, kwargs)

    def warning(self, message: str, **kwargs):
        self._message("WARNING", message, kwargs)

    def error(self, message: str, **kwargs):
        self._message("ERROR", message, kwargs)

    def debug(self, message: str, **kwargs):
        self._message("DEBUG", message, kwargs)

    def shutdown(self):
        pass


def get_logger(project_id=None, env=None, account_id=None, context: Optional[dict] = None) -> SyncLogger:
    """A logger for step code. In mock mode records go to context and are read back with get_mock_logs(context)."""
    records = get_mock_backing(context, "logger_records", list) if context and context.get("mock_mode") else None
    return SyncLogger(project_id, account_id, records)
