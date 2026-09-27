# FastAPI + OpenTelemetry + Prometheus + Grafana + Tempo Lab

A complete local Docker observability lab for learning:

- FastAPI
- OpenTelemetry Python SDK
- OpenTelemetry automatic FastAPI instrumentation
- OpenTelemetry Collector
- Prometheus metrics
- Grafana dashboards
- Tempo distributed traces
- Structured application logging

## Architecture

```text
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │     :8000           │
                         │                     │
                         │ OTEL SDK            │
                         │ traces + metrics     │
                         └──────────┬──────────┘
                                    │ OTLP gRPC
                                    ▼
                         ┌─────────────────────┐
                         │ OpenTelemetry       │
                         │ Collector :4317     │
                         │                     │
                         │ batch/process       │
                         └───────┬───────┬─────┘
                                 │       │
                       metrics   │       │ traces
                                 ▼       ▼
                       ┌────────────┐  ┌────────────┐
                       │ Prometheus │  │   Tempo    │
                       │   :9090    │  │   :3200    │
                       └─────┬──────┘  └──────┬─────┘
                             │                │
                             └───────┬────────┘
                                     ▼
                              ┌─────────────┐
                              │   Grafana   │
                              │    :3000    │
                              └─────────────┘
```

## Start

```bash
docker compose up -d --build
```

Check containers:

```bash
docker compose ps
```

## URLs

- FastAPI: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Tempo: http://localhost:3200

Grafana login:

```text
username: admin
password: admin
```

The dashboard is provisioned automatically under:

```text
Grafana → Dashboards → OpenTelemetry → FastAPI OpenTelemetry Lab
```

## Generate telemetry

Open these repeatedly:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/slow
curl http://localhost:8000/work
curl -X POST http://localhost:8000/orders
curl http://localhost:8000/error
```

Generate load:

```bash
for i in $(seq 1 100); do
  curl -s http://localhost:8000/slow >/dev/null &
  curl -s http://localhost:8000/work >/dev/null &
done
wait
```

## What to learn first

### 1. Metrics

Start in Prometheus.

Try:

```promql
sum(rate(http_server_request_duration_seconds_count[1m]))
```

Request rate by method:

```promql
sum by (http_request_method) (
  rate(http_server_request_duration_seconds_count[1m])
)
```

5xx rate:

```promql
sum(
  rate(
    http_server_request_duration_seconds_count{
      http_response_status_code=~"5.."
    }[1m]
  )
)
```

p95 latency:

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(http_server_request_duration_seconds_bucket[5m])
  )
)
```

### 2. Traces

Open Grafana → Explore → Tempo.

Find traces for:

```text
service.name = fastapi-demo
```

Call:

```bash
curl http://localhost:8000/work
```

You should see a parent HTTP span and child spans such as:

```text
GET /work
└── background-work
    ├── work-step
    ├── work-step
    └── work-step
```

The `/slow` endpoint demonstrates a slow child operation.

The `/error` endpoint demonstrates an error span.

### 3. Correlation

The important observability concept is:

```text
Metrics
   │
   ├── How often?
   ├── How many?
   └── How slow?
        │
        ▼
      Trace
        │
        ├── Which request?
        ├── Which operation?
        └── Where did time go?
```

OpenTelemetry provides the common telemetry model and context propagation.

## Project structure

```text
otel-fastapi-lab/
├── docker-compose.yml
├── README.md
│
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
│
├── otel-collector/
│   └── config.yaml
│
├── prometheus/
│   └── prometheus.yml
│
├── tempo/
│   └── tempo.yaml
│
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── datasources.yaml
    │   └── dashboards/
    │       └── dashboards.yaml
    │
    └── dashboards/
        └── fastapi-observability.json
```

## Important concepts

### OpenTelemetry

Application instrumentation and telemetry standard.

It can produce:

- traces
- metrics
- logs

### OpenTelemetry Collector

Receives telemetry from applications, processes it, and exports it to backends.

This is useful because your application does not need to know every backend.

```text
Application
    ↓
OpenTelemetry Collector
    ↓
Prometheus / Tempo / Loki / other backends
```

### Prometheus

Primarily a metrics database and query engine.

Think:

```text
"How is the system behaving?"
```

Examples:

- request rate
- error rate
- CPU
- memory
- latency
- queue depth

### Tempo

Trace backend.

Think:

```text
"Why did this particular request take 2 seconds?"
```

### Grafana

Visualization and exploration layer.

Think:

```text
"How do I understand the telemetry?"
```

## Suggested learning path

### Level 1 — Metrics

Learn:

- Counter
- Gauge
- Histogram
- Summary
- labels/attributes
- PromQL
- rate()
- increase()
- histogram_quantile()

### Level 2 — Tracing

Learn:

- trace
- span
- parent/child spans
- span attributes
- events
- exceptions
- status
- trace context

### Level 3 — Collector

Learn:

- receivers
- processors
- exporters
- pipelines
- batching
- filtering
- resource attributes

### Level 4 — Grafana

Learn:

- data sources
- dashboards
- panels
- variables
- PromQL
- Explore
- trace search

### Level 5 — Production architecture

Add:

```text
FastAPI
   │
   ▼
OpenTelemetry Collector
   │
   ├── Prometheus / Mimir
   ├── Tempo
   └── Loki
```

Then add:

- Docker/Kubernetes metadata
- node-exporter
- cAdvisor
- Alertmanager
- Grafana alerting
- service-level objectives
- exemplars
- log/trace correlation
- Kubernetes instrumentation
- RED metrics

## Cleanup

```bash
docker compose down
```

Remove all lab data:

```bash
docker compose down -v
```

The second command deletes Prometheus, Tempo and Grafana persistent volumes.
