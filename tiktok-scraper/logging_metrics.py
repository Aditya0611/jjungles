"""
Structured logging, event tracing, error taxonomy, and Prometheus-style metrics.

Features:
- JSON structured logging
- Request/event tracing with correlation IDs
- Error taxonomy and classification
- Prometheus-style counters and metrics
"""

import json
import logging
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import uuid
from collections import defaultdict


# ============================================================================
# ERROR TAXONOMY
# ============================================================================

class ErrorCategory(Enum):
    """Error categories for taxonomy."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    PARSING = "parsing"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RATE_LIMIT = "rate_limit"
    PROXY = "proxy"
    BLOCKED = "blocked"
    DATABASE = "database"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Structured error information."""
    category: ErrorCategory
    severity: ErrorSeverity
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON logging."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details or {},
            "stack_trace": self.stack_trace
        }


class ProxyBlockedError(Exception):
    """Exception raised when proxy access is blocked (403, 429, captcha)."""
    pass


class ErrorTaxonomy:
    """Error taxonomy and classification system."""
    
    @staticmethod
    def classify_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """Classify an error into taxonomy."""
        error_type = type(error).__name__
        error_message = str(error)
        context = context or {}
        
        # Network errors
        if "network" in error_message.lower() or "connection" in error_message.lower():
            if "timeout" in error_message.lower():
                return ErrorInfo(
                    category=ErrorCategory.TIMEOUT,
                    severity=ErrorSeverity.MEDIUM,
                    error_type=error_type,
                    message=error_message,
                    details=context
                )
            return ErrorInfo(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Proxy errors
        if "proxy" in error_message.lower():
            if "authentication" in error_message.lower() or "auth" in error_message.lower():
                return ErrorInfo(
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH,
                    error_type=error_type,
                    message=error_message,
                    details=context
                )

            return ErrorInfo(
                category=ErrorCategory.PROXY,
                severity=ErrorSeverity.MEDIUM,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Blocked/Captcha errors
        if "blocked" in error_message.lower() or "captcha" in error_message.lower() or "ProxyBlockedError" in error_type:
            return ErrorInfo(
                category=ErrorCategory.BLOCKED,
                severity=ErrorSeverity.HIGH,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Authentication errors
        if "auth" in error_message.lower() or "unauthorized" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Parsing errors
        if "parse" in error_message.lower() or "beautifulsoup" in error_type.lower():
            return ErrorInfo(
                category=ErrorCategory.PARSING,
                severity=ErrorSeverity.LOW,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Database errors
        if "database" in error_message.lower() or "supabase" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.HIGH,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Rate limiting
        if "rate limit" in error_message.lower() or "429" in error_message:
            return ErrorInfo(
                category=ErrorCategory.RATE_LIMIT,
                severity=ErrorSeverity.HIGH,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Timeout errors
        if "timeout" in error_message.lower() or "TimeoutError" in error_type:
            return ErrorInfo(
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                error_type=error_type,
                message=error_message,
                details=context
            )
        
        # Default/Unknown
        return ErrorInfo(
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            error_type=error_type,
            message=error_message,
            details=context
        )


# ============================================================================
# PROMETHEUS-STYLE METRICS
# ============================================================================

class MetricsCollector:
    """Prometheus-style metrics collector."""
    
    def __init__(self):
        self._counters = defaultdict(int)
        self._gauges = defaultdict(float)
        self._histograms = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment(self, metric_name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        key = self._make_key(metric_name, labels)
        with self._lock:
            self._counters[key] += value
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        key = self._make_key(metric_name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def observe_histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a histogram value."""
        key = self._make_key(metric_name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
    
    def get_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get counter value."""
        key = self._make_key(metric_name, labels)
        with self._lock:
            return self._counters.get(key, 0)
    
    def get_gauge(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        key = self._make_key(metric_name, labels)
        with self._lock:
            return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(metric_name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: self.get_histogram_stats(k.split(":")[0]) 
                              for k in self._histograms.keys()}
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    @staticmethod
    def _make_key(metric_name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create metric key with labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric_name}:{label_str}"
        return metric_name


# Global metrics instance
metrics = MetricsCollector()


# ============================================================================
# STRUCTURED JSON LOGGING
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            log_data["span_id"] = record.span_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "error_info"):
            log_data["error_info"] = record.error_info
        if hasattr(record, "metrics"):
            log_data["metrics"] = record.metrics
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName", 
                          "levelname", "levelno", "lineno", "module", "msecs", "message",
                          "pathname", "process", "processName", "relativeCreated", "thread",
                          "threadName", "exc_info", "exc_text", "stack_info", "trace_id",
                          "span_id", "request_id", "error_info", "metrics", "duration_ms"]:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


def setup_json_logging(level: int = logging.INFO, use_json: bool = True):
    """Setup JSON structured logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    if use_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s')
        )
    
    root_logger.addHandler(console_handler)
    return root_logger


# ============================================================================
# EVENT TRACING
# ============================================================================

class TraceContext:
    """Context manager for request tracing."""
    
    def __init__(self, trace_id: Optional[str] = None, request_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.request_id = request_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.start_time = None
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = time.time()
        # Set trace context in thread local storage
        threading.current_thread().trace_context = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0
        
        # Log trace completion
        extra = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "request_id": self.request_id,
            "duration_ms": duration_ms
        }
        
        if exc_type:
            error_info = ErrorTaxonomy.classify_error(exc_val, {"trace_id": self.trace_id})
            extra["error_info"] = error_info.to_dict()
            self.logger.error(
                f"Trace completed with error: {exc_val}",
                extra=extra,
                exc_info=exc_tb
            )
        else:
            self.logger.info(
                f"Trace completed successfully",
                extra=extra
            )
        
        # Clean up thread local storage
        if hasattr(threading.current_thread(), 'trace_context'):
            delattr(threading.current_thread(), 'trace_context')
        
        return False
    
    def create_span(self, operation_name: str):
        """Create a child span."""
        return Span(self.trace_id, self.request_id, operation_name, parent_span_id=self.span_id)


class Span:
    """Span for distributed tracing."""
    
    def __init__(self, trace_id: str, request_id: str, operation_name: str, 
                 parent_span_id: Optional[str] = None):
        self.trace_id = trace_id
        self.request_id = request_id
        self.span_id = str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.operation_name = operation_name
        self.start_time = None
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(
            f"Span started: {self.operation_name}",
            extra={
                "trace_id": self.trace_id,
                "span_id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "request_id": self.request_id,
                "operation": self.operation_name
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0
        
        extra = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "request_id": self.request_id,
            "operation": self.operation_name,
            "duration_ms": duration_ms
        }
        
        if exc_type:
            error_info = ErrorTaxonomy.classify_error(exc_val, {"span_id": self.span_id})
            extra["error_info"] = error_info.to_dict()
            self.logger.error(
                f"Span failed: {self.operation_name}",
                extra=extra,
                exc_info=exc_tb
            )
        else:
            self.logger.debug(
                f"Span completed: {self.operation_name}",
                extra=extra
            )
        
        return False


def get_trace_context() -> Optional[TraceContext]:
    """Get current trace context from thread local storage."""
    thread = threading.current_thread()
    return getattr(thread, 'trace_context', None)


def log_with_trace(level: int, message: str, **kwargs):
    """Log with automatic trace context."""
    logger = logging.getLogger(__name__)
    trace_context = get_trace_context()
    
    extra = kwargs.copy()
    if trace_context:
        extra["trace_id"] = trace_context.trace_id
        extra["span_id"] = trace_context.span_id
        extra["request_id"] = trace_context.request_id
    
    logger.log(level, message, extra=extra)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

@contextmanager
def trace_request(operation_name: str, request_id: Optional[str] = None):
    """Context manager for tracing a request."""
    with TraceContext(request_id=request_id) as trace:
        with trace.create_span(operation_name) as span:
            yield span


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None, 
              logger: Optional[logging.Logger] = None):
    """Log an error with taxonomy classification."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    error_info = ErrorTaxonomy.classify_error(error, context)
    trace_context = get_trace_context()
    
    extra = {
        "error_info": error_info.to_dict(),
    }
    if trace_context:
        extra["trace_id"] = trace_context.trace_id
        extra["span_id"] = trace_context.span_id
        extra["request_id"] = trace_context.request_id
    
    # Increment error counter
    metrics.increment("errors_total", labels={
        "category": error_info.category.value,
        "severity": error_info.severity.value,
        "error_type": error_info.error_type
    })
    
    logger.error(
        f"Error [{error_info.category.value}/{error_info.severity.value}]: {error_info.message}",
        extra=extra,
        exc_info=error
    )
    
    return error_info

