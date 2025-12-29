# Observability Implementation

This document describes the structured logging, event tracing, error taxonomy, and Prometheus-style metrics implementation.

## Features

### 1. Structured JSON Logging

All logs are now output in JSON format with consistent fields:

```json
{
  "timestamp": "2025-11-26T10:00:00.123456Z",
  "level": "INFO",
  "logger": "instagram_scraper",
  "message": "Starting scraper job",
  "module": "main",
  "function": "run_scraper_job",
  "line": 3716,
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "660e8400-e29b-41d4-a716-446655440001",
  "operation": "scraper_job"
}
```

**Configuration:**
- Set `USE_JSON_LOGGING=false` to use readable format (default: `true`)
- Set `LOG_LEVEL=DEBUG` to change log level (default: `INFO`)

### 2. Event Tracing Per Request

Each operation gets a unique `trace_id` that follows the request through all log entries:

```python
trace_id = logger.start_trace('get_post_engagement')
# ... operation code ...
logger.end_trace('get_post_engagement', trace_id, success=True)
```

**Benefits:**
- Track a single request end-to-end
- Measure operation duration
- Correlate logs across services

### 3. Error Taxonomy

All errors are categorized with error codes:

#### Error Categories

- **AUTH (1xxx)**: Authentication errors
  - `AUTH_1001`: Credentials missing
  - `AUTH_1002`: Login failed
  - `AUTH_1003`: Verification required
  - `AUTH_1004`: Session expired

- **NETWORK/PROXY (2xxx)**: Network and proxy errors
  - `NET_2001`: Connection error
  - `NET_2002`: Timeout
  - `PROXY_2003`: Proxy connection failed
  - `PROXY_2004`: Proxy authentication failed
  - `PROXY_2005`: Proxy timeout

- **SCRAPE (3xxx)**: Scraping errors
  - `SCRAPE_3001`: Navigation failed
  - `SCRAPE_3002`: Element not found
  - `SCRAPE_3003`: Rate limited
  - `SCRAPE_3004`: Blocked
  - `SCRAPE_3005`: Parsing error

- **DATA (4xxx)**: Data processing errors
  - `DATA_4001`: Validation error
  - `DATA_4002`: Serialization error
  - `DATA_4003`: Transformation error

- **DATABASE (5xxx)**: Database errors
  - `DB_5001`: Connection error
  - `DB_5002`: Query error
  - `DB_5003`: Insert error
  - `DB_5004`: Update error

- **CONFIG (6xxx)**: Configuration errors
  - `CONFIG_6001`: Missing config
  - `CONFIG_6002`: Invalid config

- **UNKNOWN (9xxx)**: Unknown errors
  - `UNKNOWN_9001`: Unclassified error

**Usage:**
```python
logger.error("Failed to connect to proxy",
            error_code=ErrorCode.PROXY_CONNECTION_FAILED,
            extra_fields={'proxy_url': 'http://proxy.example.com:8080'})
```

### 4. Prometheus-Style Metrics

Basic counters and histograms are collected:

#### Counters

- `scraper_requests_total{adapter="engagement",outcome="success"}` - Total requests by adapter and outcome
- `scraper_errors_total{adapter="engagement",error_type="navigation"}` - Errors by type
- `scraper_jobs_started_total` - Total scraper jobs started
- `scraper_jobs_completed_total{outcome="success"}` - Jobs completed by outcome
- `errors_total{error_code="PROXY_2003"}` - Errors by error code
- `log_messages_total{level="error"}` - Log messages by level
- `operations_started_total{operation="get_post_engagement"}` - Operations started
- `operations_completed_total{operation="get_post_engagement",outcome="success"}` - Operations completed

#### Histograms

- `scraper_request_duration_seconds{adapter="engagement"}` - Request duration
- `operation_duration_seconds{operation="get_post_engagement"}` - Operation duration

**Metrics Format:**
```
scraper_requests_total{adapter="engagement",outcome="success"} 150
scraper_requests_total{adapter="engagement",outcome="failure"} 5
scraper_request_duration_seconds{adapter="engagement"}_count 155
scraper_request_duration_seconds{adapter="engagement"}_sum 1234.56
scraper_request_duration_seconds{adapter="engagement"}_avg 7.96
scraper_request_duration_seconds{adapter="engagement"}_min 0.5
scraper_request_duration_seconds{adapter="engagement"}_max 45.2
```

## Usage Examples

### Structured Logging

```python
from observability import logger, ErrorCode

# Info log
logger.info("Starting operation", extra_fields={'operation': 'scrape'})

# Error with error code
logger.error("Proxy connection failed",
            error_code=ErrorCode.PROXY_CONNECTION_FAILED,
            extra_fields={'proxy_url': 'http://proxy:8080'})

# Exception with error code
try:
    # ... code ...
except Exception as e:
    logger.exception("Operation failed",
                    error_code=ErrorCode.SCRAPE_NAVIGATION_FAILED)
```

### Event Tracing

```python
# Start trace
trace_id = logger.start_trace('get_post_engagement')

try:
    # ... operation code ...
    logger.end_trace('get_post_engagement', trace_id, success=True)
except Exception as e:
    logger.end_trace('get_post_engagement', trace_id, success=False,
                    error_code=ErrorCode.SCRAPE_PARSING_ERROR)
```

### Metrics

```python
from observability import metrics, ErrorCode

# Increment counter
metrics.increment('scraper_requests_total',
                 labels={'adapter': 'engagement', 'outcome': 'success'})

# Record duration
metrics.observe('scraper_request_duration_seconds', 2.5,
               labels={'adapter': 'engagement'})

# Get metrics
all_metrics = metrics.get_all_metrics()
summary = get_metrics_summary()
print(summary['prometheus_format'])
```

## Accessing Metrics

### Programmatically

```python
from observability import get_metrics_summary

summary = get_metrics_summary()
print(summary['prometheus_format'])
```

### In Logs

Metrics summary is automatically logged at the end of each scraper job run in the JSON logs.

## Integration

The observability system is automatically integrated into:

1. **Configuration validation** - Logs config errors with error codes
2. **Engagement scraper** - Traces each post engagement extraction
3. **Hashtag discovery** - Traces hashtag discovery operations
4. **Engagement analysis** - Traces hashtag engagement analysis
5. **Main scraper job** - Tracks overall job execution

## Benefits

1. **Debugging**: Trace requests end-to-end with trace_id
2. **Monitoring**: Prometheus-style metrics for dashboards
3. **Error Analysis**: Categorized errors for better insights
4. **Performance**: Track operation durations
5. **Compliance**: Structured logs for log aggregation systems (ELK, Splunk, etc.)

## Future Enhancements

- Export metrics to Prometheus endpoint
- Add more detailed histograms (percentiles)
- Add gauge metrics for current state
- Integration with APM tools (Datadog, New Relic)
- Distributed tracing (OpenTelemetry)

