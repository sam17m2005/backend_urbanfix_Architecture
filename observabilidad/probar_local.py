"""Prueba local de la instrumentacion (sin Docker, sin Postgres y sin S3 reales).

Reproduce, sobre el codigo real de la app, tres escenarios de la matriz de fallos y muestra que dejan rastro:
  - F-05  S3 inalcanzable: la app responde 201 (falso verde) pero el fallo queda en log, traza y metrica.
  - F-07  imagen corrupta: tambien responde 201, y el log registra el tipo de error.
  - F-03  la BD falla: /login lanza una excepcion (500) y /health responde 503.
  - Camino normal: login correcto y fallido, con su traza (peticion -> consultas SQL).

Uso (desde la raiz del repo, con las dependencias de requirements-observabilidad.txt instaladas):
    python observabilidad/probar_local.py
Usa SQLite temporal y un puerto cerrado como S3. No toca ninguna base ni bucket reales.
"""
import base64
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
TMP = tempfile.mkdtemp(prefix="urbanfix-obs-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{TMP}/prueba.db",
    "AWS_ACCESS_KEY_ID": "falsa", "AWS_SECRET_ACCESS_KEY": "falsa", "AWS_REGION": "us-east-1",
    "S3_REPORTES": "bucket-prueba", "S3_PERFILES": "bucket-prueba-perfiles",
    "AWS_ENDPOINT_URL_S3": "http://127.0.0.1:9",   # puerto cerrado: S3 inalcanzable
    "AWS_MAX_ATTEMPTS": "1",
})
os.environ.pop("OTEL_ENABLED", None)

from opentelemetry.sdk.metrics.export import InMemoryMetricReader  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Categoria, Usuario  # noqa: E402
from app.observabilidad import init_observabilidad  # noqa: E402

app = create_app()                       # sin OTEL_ENABLED: comportamiento original
exportador = InMemorySpanExporter()
lector = InMemoryMetricReader()
os.environ["OTEL_ENABLED"] = "1"
init_observabilidad(app, span_processors_extra=[SimpleSpanProcessor(exportador)], metric_readers_extra=[lector])

with app.app_context():
    db.create_all()
    db.session.add(Categoria(nombre="Huecos"))
    db.session.add(Usuario(nombre="Prueba", email="test@urbanfix.com", telefono="1",
                           contrasena_hash=generate_password_hash("PasswordSeguro123!"), foto_perfil_url="https://x/y.png"))
    db.session.commit()

png = io.BytesIO()
Image.new("RGB", (10, 10), "red").save(png, format="PNG")
IMG = base64.b64encode(png.getvalue()).decode()
cliente = app.test_client()


def paso(titulo):
    print(f"\n{'=' * 78}\n{titulo}\n{'=' * 78}", flush=True)


def arbol(span_exportados, raiz_nombre_contiene):
    spans = list(span_exportados)
    raices = [s for s in spans if s.parent is None and raiz_nombre_contiene in s.name]
    if not raices:
        print("  (sin trazas que coincidan)")
        return
    tid = raices[-1].context.trace_id
    de_la_traza = [s for s in spans if s.context.trace_id == tid]
    hijos = {}
    for s in de_la_traza:
        hijos.setdefault(s.parent.span_id if s.parent else None, []).append(s)

    def imprimir(s, nivel):
        estado = s.status.status_code.name
        dur = (s.end_time - s.start_time) / 1e6
        extra = ""
        codigo_http = s.attributes.get("http.response.status_code") or s.attributes.get("http.status_code")
        if codigo_http:
            extra = f" http={codigo_http}"
        if s.attributes.get("db.statement"):
            extra = f" sql={str(s.attributes['db.statement'])[:60]!r}"
        eventos = [e.name for e in s.events]
        print(f"  {'  ' * nivel}- {s.name}  [{estado}] {dur:.1f} ms{extra}" + (f"  eventos={eventos}" if eventos else ""))
        for h in sorted(hijos.get(s.context.span_id, []), key=lambda x: x.start_time):
            imprimir(h, nivel + 1)

    print(f"  trace_id={format(tid, '032x')}")
    imprimir(raices[-1], 0)


paso("1) Login correcto (200): log JSON + traza peticion -> consultas SQL")
exportador.clear()
r = cliente.post("/login", json={"email": "test@urbanfix.com", "contrasena": "PasswordSeguro123!"}, headers={"X-Request-ID": "demo-login-ok"})
print(f"  respuesta: {r.status_code}  X-Request-ID={r.headers['X-Request-ID']}")
arbol(exportador.get_finished_spans(), "/login")

paso("2) Login fallido (401): el log deja el evento con su codigo")
cliente.post("/login", json={"email": "test@urbanfix.com", "contrasena": "mala"})

paso("3) F-05 · S3 inalcanzable: POST /reportes responde 201 (falso verde) pero el fallo NO pasa desapercibido")
exportador.clear()
datos = {"descripcion": "Hueco", "direccion": "Calle 1", "referencia": "Frente al parque", "latitud": 4.6, "longitud": -74.1,
         "usuario_creador_id": 1, "categoria_id": 1, "tipo_evento": "hueco", "img_prueba_1": IMG}
r = cliente.post("/reportes", json=datos)
print(f"  respuesta HTTP: {r.status_code}  (el cliente ve exito)")
arbol(exportador.get_finished_spans(), "/reportes")

paso("3b) F-07 · imagen corrupta: tambien responde 201, y el log dice por que")
exportador.clear()
datos_corruptos = dict(datos, img_prueba_1=base64.b64encode(b"no soy una imagen").decode())
r = cliente.post("/reportes", json=datos_corruptos)
print(f"  respuesta HTTP: {r.status_code}  (el cliente ve exito)")

paso("4) F-03 · la BD falla: /login lanza excepcion (500) y /health responde 503")
exportador.clear()
with mock.patch("sqlalchemy.orm.Session.execute", side_effect=OperationalError("SELECT 1", {}, Exception("conexion rechazada"))):
    try:
        r = cliente.post("/login", json={"email": "test@urbanfix.com", "contrasena": "x"})
        print(f"  /login   -> {r.status_code}")
    except Exception as e:  # el cliente de pruebas propaga la excepcion cuando no hay manejador
        print(f"  /login   -> excepcion propagada: {type(e).__name__} (en produccion el cliente recibe un 500 HTML)")
    r = cliente.get("/health")
    print(f"  /health  -> {r.status_code} {r.get_json()}")

paso("5) /health con la BD sana")
r = cliente.get("/health")
print(f"  /health  -> {r.status_code} {r.get_json()}")

paso("6) Metricas recogidas (resumen)")
datos_m = lector.get_metrics_data()
for rm in datos_m.resource_metrics:
    for sm in rm.scope_metrics:
        for m in sm.metrics:
            if m.name.startswith("urbanfix") or m.name == "http.server.request.duration":
                for p in m.data.data_points:
                    attrs = {k: v for k, v in p.attributes.items() if k in ("http.route", "http.request.method", "http.response.status_code", "estado", "bucket", "error_tipo")}
                    valor = getattr(p, "value", None)
                    if valor is None:
                        valor = f"n={p.count} suma={p.sum:.1f}"
                    print(f"  {m.name:34s} {valor!s:>16}  {attrs}")
