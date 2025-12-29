"""
Observability module for Instagram scraper.

Provides:
- Structured JSON logging
- Request/trace ID tracking
- Error taxonomy
- Prometheus-style metrics
"""
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from collections import defaultdict
from threading import Lock
from enum import Enum


# Context variable for request/trace ID
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)


class ErrorCode(Enum):
    """Error taxonomy - categorized error codes."""
    # Authentication errors (1xxx)
    AUTH_CREDENTIALS_MISSING = "AUTH_1001"
    AUTH_LOGIN_FAILED = "AUTH_1002"
    AUTH_VERIFICATION_REQUIRED = "AUTH_1003"
    AUTH_SESSION_EXPIRED = "AUTH_1004"
    
    # Network/Proxy errors (2xxx)
    NETWORK_CONNECTION_ERROR = "NET_2001"
    NETWORK_TIMEOUT = "NET_2002"
    PROXY_CONNECTION_FAILED = "PROXY_2003"
    PROXY_AUTH_FAILED = "PROXY_2004"
    PROXY_TIMEOUT = "PROXY_2005"
    
    # Scraping errors (3xxx)
    SCRAPE_NAVIGATION_FAILED = "SCRAPE_3001"
    SCRAPE_ELEMENT_NOT_FOUND = "SCRAPE_3002"
    SCRAPE_RATE_LIMITED = "SCRAPE_3003"
    SCRAPE_BLOCKED = "SCRAPE_3004"
    SCRAPE_PARSING_ERROR = "SCRAPE_3005"
    
    # Data processing errors (4xxx)
    DATA_VALIDATION_ERROR = "DATA_4001"
    DATA_SERIALIZATION_ERROR = "DATA_4002"
    DATA_TRANSFORMATION_ERROR = "DATA_4003"
    
    # Database errors (5xxx)
    DB_CONNECTION_ERROR = "DB_5001"
    DB_QUERY_ERROR = "DB_5002"
    DB_INSERT_ERROR = "DB_5003"
    DB_UPDATE_ERROR = "DB_5004"
    
    # Configuration errors (6xxx)
    CONFIG_MISSING = "CONFIG_6001"
    CONFIG_INVALID = "CONFIG_6002"
    
    # Unknown errors (9xxx)
    UNKNOWN_ERROR = "UNKNOWN_9001"


class Metrics:
    """Prometheus-style metrics collector."""
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
    
    def increment(self, metric_name: str, labels: Optional[Dict[str, str]] = None, value: int = 1):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric (e.g., 'requests_total')
            labels: Optional labels dict (e.g., {'adapter': 'instagram', 'outcome': 'success'})
            value: Amount to increment (default: 1)
        """
        key = self._format_key(metric_name, labels)
        with self._lock:
            self._counters[key] += value
    
    def observe(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a histogram observation.
        
        Args:
            metric_name: Name of the metric (e.g., 'request_duration_seconds')
            value: Observed value
            labels: Optional labels dict
        """
        key = self._format_key(metric_name, labels)
        with self._lock:
            self._histograms[key].append(value)
    
    def get_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value."""
        key = self._format_key(metric_name, labels)
        with self._lock:
            return self._counters.get(key, 0)
    
    def get_histogram_summary(self, metric_name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram summary (count, sum, avg, min, max)."""
        key = self._format_key(metric_name, labels)
        with self._lock:
            values = self._histograms.get(key, [])
            if not values:
                return {'count': 0, 'sum': 0.0, 'avg': 0.0, 'min': 0.0, 'max': 0.0}
            
            return {
                'count': len(values),
                'sum': sum(values),
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values)
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics in Prometheus format."""
        with self._lock:
            return {
                'counters': dict(self._counters),
                'histograms': {
                    key: self.get_histogram_summary(key.split('{')[0], self._parse_labels(key))
                    for key in self._histograms.keys()
                }
            }
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
    
    def _format_key(self, metric_name: str, labels: Optional[Dict[str, str]]) -> str:
        """Format metric key with labels."""
        if labels:
            label_str = ','.join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f'{metric_name}{{{label_str}}}'
        return metric_name
    
    def _parse_labels(self, key: str) -> Optional[Dict[str, str]]:
        """Parse labels from formatted key."""
        if '{' not in key:
            return None
        labels_str = key.split('{')[1].rstrip('}')
        labels = {}
        for pair in labels_str.split(','):
            if '=' in pair:
                k, v = pair.split('=', 1)
                labels[k.strip()] = v.strip('"')
        return labels if labels else None


# Global metrics instance
metrics = Metrics()


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a structured JSON string.
        
        Includes standard fields, request context (request_id, trace_id),
        and any extra fields attached to the record.
        
        Args:
            record: The logging record to format
            
        Returns:
            str: JSON-formatted log message
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request/trace IDs if available
        request_id = request_id_var.get()
        trace_id = trace_id_var.get()
        if request_id:
            log_data['request_id'] = request_id
        if trace_id:
            log_data['trace_id'] = trace_id
        
        # Add error code if present
        if hasattr(record, 'error_code'):
            log_data['error_code'] = record.error_code.value if isinstance(record.error_code, ErrorCode) else record.error_code
            log_data['error_category'] = record.error_code.value.split('_')[0] if isinstance(record.error_code, ErrorCode) else None
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add any extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """Structured logger wrapper with request tracing."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._start_times: Dict[str, float] = {}
    
    def _log_with_context(self, level: int, msg: str, error_code: Optional[ErrorCode] = None, 
                          extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Internal helper that normalizes logging kwargs so we never pass
        unexpected parameters (like ``extra_fields``) into the stdlib logger.
        """
        # Start from any user‑provided extra dict
        extra = kwargs.pop('extra', {}) or {}

        # Allow callers to (incorrectly) pass extra_fields via kwargs;
        # normalize it so it becomes part of the structured payload.
        if 'extra_fields' in kwargs and kwargs['extra_fields'] is not None:
            # If the explicit argument was also provided, merge them
            if extra_fields:
                extra_fields = {**kwargs['extra_fields'], **extra_fields}
            else:
                extra_fields = kwargs['extra_fields']
            kwargs.pop('extra_fields', None)

        # Attach error code on the record so JSONFormatter can see it
        if error_code:
            extra['error_code'] = error_code

        # Attach any structured fields in a single namespaced key
        if extra_fields:
            extra['extra_fields'] = extra_fields

        # Only forward kwargs that the logging API actually understands
        allowed_kwargs = {}
        for key in ('exc_info', 'stack_info', 'stacklevel'):
            if key in kwargs:
                allowed_kwargs[key] = kwargs[key]

        self.logger.log(level, msg, extra=extra, **allowed_kwargs)
    
    def info(self, msg: str, error_code: Optional[ErrorCode] = None,
             extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message with optional error code and extra fields."""
        self._log_with_context(logging.INFO, msg, error_code=error_code,
                               extra_fields=extra_fields, **kwargs)
        metrics.increment('log_messages_total', {'level': 'info'})
    
    def debug(self, msg: str, error_code: Optional[ErrorCode] = None,
              extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message with optional error code and extra fields."""
        self._log_with_context(logging.DEBUG, msg, error_code=error_code,
                               extra_fields=extra_fields, **kwargs)
        metrics.increment('log_messages_total', {'level': 'debug'})
    
    def warning(self, msg: str, error_code: Optional[ErrorCode] = None, **kwargs):
        """
        Log a warning message with an optional error code.
        
        Args:
            msg: The warning message
            error_code: Optional ErrorCode enum member
            **kwargs: Additional parameters passed to stdlib logger
        """
        self._log_with_context(logging.WARNING, msg, error_code=error_code, **kwargs)
        metrics.increment('log_messages_total', {'level': 'warning'})
        if error_code:
            metrics.increment('errors_total', {'error_code': error_code.value})
    
    def error(self, msg: str, error_code: Optional[ErrorCode] = None, 
              extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log error with error code and extra context."""
        self._log_with_context(logging.ERROR, msg, error_code=error_code, 
                               extra_fields=extra_fields, **kwargs)
        metrics.increment('log_messages_total', {'level': 'error'})
        if error_code:
            metrics.increment('errors_total', {'error_code': error_code.value})
    
    def exception(self, msg: str, error_code: Optional[ErrorCode] = None, 
                  extra_fields: Optional[Dict[str, Any]] = None, **kwargs):
        """Log exception with error code."""
        kwargs['exc_info'] = True
        self.error(msg, error_code=error_code, extra_fields=extra_fields, **kwargs)
    
    def start_trace(self, operation: str) -> str:
        """Start a trace for an operation, returns trace_id."""
        trace_id = str(uuid.uuid4())
        trace_id_var.set(trace_id)
        self._start_times[trace_id] = time.time()
        self.info(f"Starting operation: {operation}", extra={'operation': operation, 'trace_id': trace_id})
        metrics.increment('operations_started_total', {'operation': operation})
        return trace_id
    
    def end_trace(self, operation: str, trace_id: Optional[str] = None, 
                  success: bool = True, error_code: Optional[ErrorCode] = None,
                  extra_fields: Optional[Dict[str, Any]] = None):
        """
        End a trace and record duration.
        
        extra_fields allows callers to attach additional structured context
        about the completed operation (e.g. items processed).
        """
        if trace_id is None:
            trace_id = trace_id_var.get()
        
        if trace_id and trace_id in self._start_times:
            duration = time.time() - self._start_times[trace_id]
            metrics.observe('operation_duration_seconds', duration, {'operation': operation})
            
            outcome = 'success' if success else 'failure'
            metrics.increment('operations_completed_total', {'operation': operation, 'outcome': outcome})
            
            # Base context about this operation
            base_fields = {
                'operation': operation,
                'duration_seconds': duration,
                'trace_id': trace_id,
            }
            # Merge in any caller‑provided fields
            if extra_fields:
                base_fields.update(extra_fields)

            if success:
                self.info(f"Completed operation: {operation}", 
                         extra_fields=base_fields)
            else:
                self.error(f"Failed operation: {operation}", 
                          error_code=error_code,
                          extra_fields=base_fields)
            
            del self._start_times[trace_id]
    
    def set_request_id(self, request_id: str):
        """Set request ID for current context."""
        request_id_var.set(request_id)
    
    def get_request_id(self) -> Optional[str]:
        """Get current request ID."""
        return request_id_var.get()
    
    def get_trace_id(self) -> Optional[str]:
        """Get current trace ID."""
        return trace_id_var.get()


def setup_structured_logging(log_file_path: str, log_level: int = logging.INFO, 
                            json_format: bool = True) -> StructuredLogger:
    """
    Setup structured logging with JSON format.
    
    Args:
        log_file_path: Path to log file
        log_level: Logging level
        json_format: Whether to use JSON format (default: True)
    
    Returns:
        StructuredLogger instance
    """
    logger = logging.getLogger('instagram_scraper')
    logger.setLevel(log_level)
    logger.handlers.clear()  # Clear existing handlers
    
    # File handler with JSON format
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    if json_format:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
    logger.addHandler(file_handler)
    
    # Console handler with readable format (for development)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(console_handler)
    
    return StructuredLogger(logger)


def get_metrics_summary() -> Dict[str, Any]:
    """Get summary of all metrics in Prometheus format."""
    all_metrics = metrics.get_all_metrics()
    
    # Format for Prometheus text format
    prometheus_lines = []
    
    # Counters
    for key, value in all_metrics['counters'].items():
        prometheus_lines.append(f"{key} {value}")
    
    # Histograms (as summaries)
    for key, summary in all_metrics['histograms'].items():
        if summary['count'] > 0:
            prometheus_lines.append(f"{key}_count {summary['count']}")
            prometheus_lines.append(f"{key}_sum {summary['sum']}")
            prometheus_lines.append(f"{key}_avg {summary['avg']}")
            prometheus_lines.append(f"{key}_min {summary['min']}")
            prometheus_lines.append(f"{key}_max {summary['max']}")
    
    return {
        'raw': all_metrics,
        'prometheus_format': '\n'.join(prometheus_lines)
    }

