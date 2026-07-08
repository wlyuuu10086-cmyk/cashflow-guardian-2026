import datetime
import threading
from typing import Dict, Any, List, Optional
from .schemas import TraceStep, TraceRecord

class TraceStore:
    """Thread-safe trace store for tracking agent execution steps."""
    def __init__(self) -> None:
        self._traces: Dict[str, TraceRecord] = {}
        self._lock = threading.Lock()

    def create_trace(self, trace_id: str, request_id: str) -> TraceRecord:
        """Initializes a new trace record in the store."""
        with self._lock:
            record = TraceRecord(trace_id=trace_id, request_id=request_id, steps=[])
            self._traces[trace_id] = record
            return record

    def add_step(self, trace_id: str, step_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Appends a new TraceStep to an active trace record."""
        now_str = datetime.datetime.utcnow().isoformat() + "Z"
        step = TraceStep(step_name=step_name, timestamp=now_str, metadata=metadata or {})
        
        with self._lock:
            if trace_id in self._traces:
                self._traces[trace_id].steps.append(step)

    def get_trace(self, trace_id: str) -> Optional[TraceRecord]:
        """Retrieves a trace record by ID."""
        with self._lock:
            return self._traces.get(trace_id)

    def clear(self) -> None:
        """Clears all trace records."""
        with self._lock:
            self._traces.clear()

# Global thread-safe trace store instance
global_trace_store = TraceStore()
