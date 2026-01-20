# Monitoring and Observability

## Overview

Comprehensive monitoring system for the Multi-Layer Context Foundation with Prometheus metrics, Grafana dashboards, and intelligent alerting.

## Architecture

```
┌─────────────────────────────────────────────┐
│          Application Layer                   │
│  ┌────────────────────────────────────────┐ │
│  │  FastAPI + Metrics Middleware          │ │
│  │  - Request metrics                     │ │
│  │  - Performance tracking                │ │
│  │  - Health checks                       │ │
│  └────────────────────────────────────────┘ │
└─────────────┬───────────────────────────────┘
              │
              │ Prometheus exposition format
              ▼
┌─────────────────────────────────────────────┐
│          Prometheus Server                   │
│  - Metrics scraping (30s interval)          │
│  - Time-series storage                      │
│  - Alert evaluation                         │
│  - Recording rules                          │
└─────────────┬───────────────────────────────┘
              │
       ┌──────┴──────┐
       │             │
       ▼             ▼
┌─────────────┐ ┌──────────────┐
│  Grafana    │ │ Alertmanager │
│  Dashboards │ │  - Routing   │
│  - Overview │ │  - Grouping  │
│  - Performance│ │ - Notifications│
│  - Alerts   │ └──────────────┘
└─────────────┘
```

## Metrics

### HTTP Metrics

**Request Counters:**
```prometheus
http_requests_total{method, endpoint, status}
```
- Total number of HTTP requests
- Labels: method (GET/POST), endpoint, status code

**Request Duration:**
```prometheus
http_request_duration_seconds{method, endpoint}
```
- Histogram of request durations
- Buckets: 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 10s

**In-Progress Requests:**
```prometheus
http_requests_in_progress{method, endpoint}
```
- Current number of active requests

**Request/Response Size:**
```prometheus
http_request_size_bytes{method, endpoint}
http_response_size_bytes{method, endpoint}
```
- Summary of request and response sizes

### Context Management Metrics

**Operations:**
```prometheus
context_operations_total{operation, layer, status}
context_operation_duration_seconds{operation, layer}
```
- Operations: store, retrieve, delete, consolidate
- Layers: immediate, session, longterm

**Items Count:**
```prometheus
context_items_total{layer}
```
- Current number of items in each layer

**Cache Performance:**
```prometheus
context_cache_hits_total{layer}
context_cache_misses_total{layer}
```

### Search Metrics

**Query Performance:**
```prometheus
search_queries_total{strategy, status}
search_duration_seconds{strategy}
search_results_count{strategy}
```
- Strategies: hybrid, semantic, keyword, graph

### Database Metrics

**Vector Database:**
```prometheus
vector_db_operations_total{operation, status}
vector_db_operation_duration_seconds{operation}
vector_collection_size{collection}
```

**Graph Database:**
```prometheus
graph_db_operations_total{operation, status}
graph_db_operation_duration_seconds{operation}
graph_nodes_total{node_type}
graph_relationships_total{relationship_type}
```

### Entity Extraction

```prometheus
entity_extraction_total{status}
entities_extracted_count
relationships_extracted_count
```

### Authentication

```prometheus
auth_attempts_total{method, status}
active_sessions
token_operations_total{operation, status}
```

### System Metrics

```prometheus
memory_usage_bytes{type}
active_connections{type}
errors_total{error_type, endpoint}
users_total{status}
```

## Health Checks

### Endpoints

**Detailed Health Check:**
```bash
GET /health/detailed
```

Returns comprehensive health status:
```json
{
  \"status\": \"healthy\",
  \"timestamp\": \"2024-01-20T10:00:00Z\",
  \"uptime_seconds\": 86400,
  \"checks\": [
    {
      \"name\": \"orchestrator\",
      \"status\": \"healthy\",
      \"message\": \"Orchestrator operational\",
      \"duration_seconds\": 0.001
    },
    {
      \"name\": \"vector_store\",
      \"status\": \"healthy\",
      \"message\": \"Vector store operational\",
      \"details\": {\"vectors_count\": 10000}
    }
  ]
}
```

**Simple Health Check:**
```bash
GET /health/simple
```

Fast check for load balancers.

### Kubernetes Probes

**Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health/simple
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10
```

**Readiness Probe:**
```yaml
readinessProbe:
  httpGet:
    path: /health/detailed
    port: http
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Prometheus Setup

### Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'mlcf-api'
    static_configs:
      - targets: ['mlcf-api:8000']
    metrics_path: '/metrics'
  
  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'
  
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:2004']
    metrics_path: '/metrics'

rule_files:
  - '/etc/prometheus/alerts/mlcf-alerts.yaml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Docker Compose

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alerts:/etc/prometheus/alerts
      - prometheus-data:/prometheus
    ports:
      - \"9090:9090\"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
  
  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - \"3000:3000\"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
  
  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - \"9093:9093\"

volumes:
  prometheus-data:
  grafana-data:
```

## Grafana Dashboards

### 1. MLCF Overview Dashboard

**Panels:**
- Request rate (by status code)
- Response time percentiles (p50, p90, p95, p99)
- Error rate
- Active requests
- Context items by layer
- Search performance by strategy
- Cache hit rate
- Memory usage
- Database statistics

**Import:**
```bash
# Via UI
Grafana → Dashboards → Import → Upload JSON file

# Via API
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H \"Content-Type: application/json\" \
  -d @monitoring/grafana/dashboards/mlcf-overview.json
```

### 2. Performance Dashboard

**Panels:**
- Latency distribution heatmap
- Latency percentiles over time
- Search performance by strategy
- Context operation performance
- Database operation performance
- Throughput by endpoint
- Request/response sizes
- Memory usage trends

## Alerting

### Alert Rules

**Critical Alerts:**
1. **HighErrorRate** - Error rate > 5% for 5 minutes
2. **APIDown** - API unreachable for 1 minute
3. **VectorDBDown** - Vector DB unreachable
4. **GraphDBDown** - Graph DB unreachable
5. **SuspiciousAuthActivity** - Possible brute force attack

**Warning Alerts:**
1. **HighLatency** - p95 latency > 2s for 10 minutes
2. **SlowSearchQueries** - Search p95 > 5s
3. **HighMemoryUsage** - Memory > 90% for 5 minutes
4. **HighAuthFailureRate** - Auth failures > 30%
5. **SlowDatabaseOperations** - DB operations > 3s

**Info Alerts:**
1. **LowCacheHitRate** - Cache hits < 50%
2. **ContextBufferFull** - Immediate buffer at capacity

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: true
    
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'default'
    slack_configs:
      - channel: '#alerts'
        title: 'MLCF Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#critical-alerts'
        title: ':fire: CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
  
  - name: 'warning-alerts'
    slack_configs:
      - channel: '#alerts'
        title: ':warning: WARNING: {{ .GroupLabels.alertname }}'
```

## Usage

### Accessing Metrics

**From Application:**
```bash
curl http://localhost:8000/metrics
```

**From Prometheus:**
```bash
# Query API
curl 'http://localhost:9090/api/v1/query?query=http_requests_total'

# Web UI
open http://localhost:9090
```

**From Grafana:**
```bash
open http://localhost:3000
# Default credentials: admin/admin
```

### Example Queries

**Request Rate:**
```promql
sum(rate(http_requests_total[5m])) by (status)
```

**Error Rate:**
```promql
sum(rate(http_requests_total{status=~\"5..\"}[5m])) 
/ 
sum(rate(http_requests_total[5m]))
```

**95th Percentile Latency:**
```promql
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)
```

**Cache Hit Rate:**
```promql
sum(rate(context_cache_hits_total[5m])) 
/ 
(sum(rate(context_cache_hits_total[5m])) + sum(rate(context_cache_misses_total[5m])))
```

**Top Slowest Endpoints:**
```promql
topk(10, 
  histogram_quantile(0.95, 
    sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
  )
)
```

## Custom Metrics

### Adding New Metrics

```python
from prometheus_client import Counter, Histogram

# Define metric
my_custom_metric = Counter(
    'my_custom_operations_total',
    'Description of my metric',
    ['label1', 'label2'],
    registry=registry
)

# Use metric
my_custom_metric.labels(label1=\"value1\", label2=\"value2\").inc()
```

### Tracking Function Performance

```python
from mlcf.monitoring.metrics import track_time, search_duration_seconds

@track_time(search_duration_seconds, {\"strategy\": \"custom\"})
async def my_search_function():
    # Your code here
    pass
```

## Best Practices

1. **Use Labels Wisely** - Keep cardinality low (< 10 values per label)
2. **Histogram Buckets** - Align buckets with your SLOs
3. **Alert Fatigue** - Only alert on actionable conditions
4. **Dashboard Organization** - Group related metrics
5. **Retention** - Balance storage vs. historical data needs
6. **Documentation** - Document all custom metrics

## Troubleshooting

### High Cardinality

**Problem:** Too many unique label combinations
**Solution:** 
- Remove high-cardinality labels (user IDs, request IDs)
- Use aggregation
- Implement metric relabeling

### Missing Metrics

```bash
# Check if endpoint is scraped
curl http://localhost:8000/metrics | grep metric_name

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Prometheus logs
docker logs prometheus
```

### Slow Queries

**Problem:** Dashboard queries timeout
**Solution:**
- Reduce time range
- Use recording rules
- Optimize PromQL queries
- Increase Prometheus resources

## Recording Rules

For expensive queries, use recording rules:

```yaml
# recording-rules.yaml
groups:
  - name: mlcf_recordings
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)
      
      - record: job:http_request_duration:p95
        expr: histogram_quantile(0.95, 
                sum(rate(http_request_duration_seconds_bucket[5m])) by (le, job))
```

## Integration

### With Application

The monitoring system is automatically integrated via middleware:

```python
# In mlcf/api/main.py
from mlcf.monitoring.middleware import MetricsMiddleware

app.add_middleware(MetricsMiddleware)
```

### With External Systems

**Datadog:**
```yaml
# datadog-agent.yaml
prometheus:
  enabled: true
  url: http://prometheus:9090
```

**New Relic:**
```yaml
# newrelic.yml
integrations:
  - name: prometheus
    env:
      URLS: [\"http://mlcf-api:8000/metrics\"]
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Alert Best Practices](https://prometheus.io/docs/practices/alerting/)
