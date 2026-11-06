"""Observabilidad de UrbanFix (prueba de concepto, Modulo 7).

Se activa con OTEL_ENABLED=1. Sin esa variable no hace nada y la aplicacion se comporta igual que antes.

Senales que produce:
  - Logs JSON por stdout (visibles con `docker logs`), con trace_id/span_id para correlacionarlos con las trazas.
  - Trazas OpenTelemetry: Flask (peticion), SQLAlchemy (consultas) y botocore (llamadas a S3).
  - Metricas OpenTelemetry: las de Flask (duracion y conteo por ruta y codigo) mas dos propias:
    conexiones del pool en uso y fallos de subida a S3.
  - GET /health: liveness + readiness con SELECT 1 (escenario F-03 de la matriz de fallos).

Exportacion: OTLP/HTTP al Collector (puerto 4318) cuando OTEL_EXPORTER_OTLP_ENDPOINT esta definido;
con OTEL_CONSOLE=1 las senales tambien se imprimen por consola (util sin Collector).
"""
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone

_ACTIVO = False
_contador_fallos_s3 = None

# Convenciones semanticas estables de HTTP: la metrica de duracion trae http.route y el codigo de respuesta.
os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "http")
log = logging.getLogger("urbanfix")


def activo():
    return _ACTIVO


def _verdadero(valor):
    return str(valor or "").strip().lower() in ("1", "true", "yes", "si")


class JsonFormatter(logging.Formatter):
    """Una linea JSON por evento, con el contexto de traza cuando existe."""

    CAMPOS = ("evento", "request_id", "endpoint", "method", "status", "duration_ms", "bucket", "error_tipo")

    def format(self, record):
        d = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            d["trace_id"] = format(ctx.trace_id, "032x")
            d["span_id"] = format(ctx.span_id, "016x")
        for campo in self.CAMPOS:
            if hasattr(record, campo):
                d[campo] = getattr(record, campo)
        if record.exc_info:
            d["exc"] = self.formatException(record.exc_info)
        return json.dumps(d, ensure_ascii=False)


def registrar_fallo_s3(exc, bucket):
    """Deja rastro de un fallo de subida a S3 (escenarios F-05 / F-07).

    No cambia el comportamiento de la aplicacion: quien llama decide que devolver.
    Con la observabilidad apagada conserva el `print` original.
    """
    if not _ACTIVO:
        print(f"Error al subir a S3: {exc}")
        return
    log.error(
        "Fallo al subir a S3",
        extra={"evento": "s3_upload_failed", "bucket": bucket, "error_tipo": type(exc).__name__},
    )
    if _contador_fallos_s3 is not None:
        _contador_fallos_s3.add(1, {"bucket": bucket, "error_tipo": type(exc).__name__})


def init_observabilidad(app, span_processors_extra=(), metric_readers_extra=()):
    """Configura logs, trazas, metricas y /health. Devuelve True si quedo activa."""
    global _ACTIVO, _contador_fallos_s3
    if not _verdadero(os.getenv("OTEL_ENABLED")):
        return False

    from flask import g, jsonify, request
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.threading import ThreadingInstrumentor
    from opentelemetry.metrics import Observation
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    from sqlalchemy import text

    from . import db

    # ---------------- logs JSON ----------------
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(JsonFormatter())
    raiz = logging.getLogger()
    raiz.handlers = [manejador]
    raiz.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # el acceso ya se registra como evento http_request

    # ---------------- trazas y metricas ----------------
    recurso = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "urbanfix-backend"),
        "service.version": os.getenv("APP_VERSION", "dev"),
        "deployment.environment": os.getenv("DEPLOY_ENV", "local"),
    })
    hay_otlp = bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
    consola = _verdadero(os.getenv("OTEL_CONSOLE"))

    proveedor_trazas = TracerProvider(resource=recurso)
    if hay_otlp:
        proveedor_trazas.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    if consola:
        proveedor_trazas.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    for procesador in span_processors_extra:
        proveedor_trazas.add_span_processor(procesador)
    trace.set_tracer_provider(proveedor_trazas)

    lectores = list(metric_readers_extra)
    if hay_otlp:
        lectores.append(PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=10000))
    if consola:
        lectores.append(PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60000))
    proveedor_metricas = MeterProvider(resource=recurso, metric_readers=lectores)
    metrics.set_meter_provider(proveedor_metricas)
    medidor = metrics.get_meter("urbanfix")

    _contador_fallos_s3 = medidor.create_counter(
        "urbanfix.s3.upload.failures", unit="1", description="Subidas a S3 que lanzaron una excepcion"
    )

    with app.app_context():
        engine = db.engine

    def _observar_pool(_opciones):
        pool = engine.pool
        salida = []
        for estado, metodo in (("en_uso", "checkedout"), ("tamano", "size"), ("desborde", "overflow")):
            funcion = getattr(pool, metodo, None)
            if funcion is not None:
                valor = funcion()
                salida.append(Observation(max(valor, 0) if estado == "desborde" else valor, {"estado": estado}))
        return salida

    medidor.create_observable_gauge(
        "urbanfix.db.pool.connections", callbacks=[_observar_pool], unit="1",
        description="Conexiones del pool de SQLAlchemy (F-01: saturacion del pool)",
    )

    # ---------------- instrumentacion automatica ----------------
    ThreadingInstrumentor().instrument()  # s3transfer sube en hilos: sin esto el span de S3 queda fuera de la traza
    FlaskInstrumentor().instrument_app(app, excluded_urls="health")
    SQLAlchemyInstrumentor().instrument(engine=engine)
    BotocoreInstrumentor().instrument()

    # ---------------- evento por peticion ----------------
    @app.before_request
    def _inicio():
        g._t0 = time.perf_counter()
        entrante = request.headers.get("X-Request-ID", "")
        g.request_id = entrante if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", entrante) else uuid.uuid4().hex

    @app.after_request
    def _fin(respuesta):
        respuesta.headers["X-Request-ID"] = getattr(g, "request_id", "")
        if request.path == "/health" and respuesta.status_code < 400:
            return respuesta
        nivel = logging.ERROR if respuesta.status_code >= 500 else logging.WARNING if respuesta.status_code >= 400 else logging.INFO
        log.log(nivel, "peticion", extra={
            "evento": "http_request",
            "request_id": getattr(g, "request_id", ""),
            "endpoint": request.url_rule.rule if request.url_rule else "(sin ruta)",  # plantilla, no la URL: baja cardinalidad
            "method": request.method,
            "status": respuesta.status_code,
            "duration_ms": round((time.perf_counter() - getattr(g, "_t0", time.perf_counter())) * 1000, 1),
        })
        return respuesta

    # ---------------- /health ----------------
    def _health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(estado="ok", bd="ok"), 200
        except Exception as e:  # noqa: BLE001 - cualquier fallo de la BD significa "no listo"
            log.error("BD no disponible", extra={"evento": "health_bd_fallo", "error_tipo": type(e).__name__})
            return jsonify(estado="degradado", bd="error"), 503

    app.add_url_rule("/health", "health", _health, methods=["GET"])

    _ACTIVO = True
    log.info("Observabilidad activa", extra={"evento": "observabilidad_iniciada"})
    return True
