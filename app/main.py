import asyncio
import logging
import random
import time

from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("fastapi-demo")

resource = Resource.create({
    "service.name": "fastapi-demo",
    "service.version": "1.0.0",
    "deployment.environment": "docker",
})

# -----------------------------
# Traces
# -----------------------------
trace_provider = TracerProvider(resource=resource)
trace_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4317",
    insecure=True,
)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer("fastapi-demo")

# -----------------------------
# Metrics
# -----------------------------
metric_exporter = OTLPMetricExporter(
    endpoint="http://otel-collector:4317",
    insecure=True,
)
metric_reader = PeriodicExportingMetricReader(
    metric_exporter,
    export_interval_millis=5000,
)
meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("fastapi-demo")

orders_created = meter.create_counter(
    "demo_orders_created",
    description="Number of demo orders created",
)
demo_jobs = meter.create_counter(
    "demo_jobs_total",
    description="Number of demo jobs executed",
)
job_duration = meter.create_histogram(
    "demo_job_duration_seconds",
    description="Duration of demo jobs",
    unit="s",
)

# Auto-instrument FastAPI HTTP requests and Python logging.
app = FastAPI(title="OpenTelemetry FastAPI Lab", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)
LoggingInstrumentor().instrument(set_logging_format=True)


@app.get("/")
async def root():
    return {
        "service": "fastapi-demo",
        "message": "OpenTelemetry lab is running",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/slow",
            "/error",
            "/orders",
            "/work",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/slow")
async def slow():
    delay = random.uniform(0.2, 2.0)

    with tracer.start_as_current_span("simulate-slow-operation") as span:
        span.set_attribute("demo.delay_seconds", delay)
        await asyncio.sleep(delay)

    return {"status": "ok", "delay_seconds": round(delay, 3)}


@app.get("/error")
async def error():
    with tracer.start_as_current_span("simulate-error") as span:
        span.set_attribute("demo.error", True)
        logger.error("Intentional demo error endpoint was called")
        span.record_exception(RuntimeError("intentional demo error"))
        span.set_status(trace.Status(trace.StatusCode.ERROR))
    raise HTTPException(status_code=500, detail="Intentional demo error")


@app.post("/orders")
async def create_order():
    order_id = random.randint(10000, 99999)

    with tracer.start_as_current_span("create-order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.type", "demo")
        orders_created.add(1, {"order_type": "demo"})
        logger.info("Created demo order %s", order_id)

    return {"order_id": order_id, "status": "created"}


@app.get("/work")
async def work():
    started = time.perf_counter()
    iterations = random.randint(1, 5)

    with tracer.start_as_current_span("background-work") as span:
        span.set_attribute("work.iterations", iterations)

        for i in range(iterations):
            with tracer.start_as_current_span("work-step") as step:
                step.set_attribute("work.step", i + 1)
                await asyncio.sleep(random.uniform(0.05, 0.4))

        duration = time.perf_counter() - started
        demo_jobs.add(1, {"result": "success"})
        job_duration.record(duration, {"result": "success"})

    logger.info("Completed demo work in %.3f seconds", duration)

    return {
        "status": "completed",
        "iterations": iterations,
        "duration_seconds": round(duration, 3),
    }
