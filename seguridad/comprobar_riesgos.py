"""Reproduce, sobre el codigo real de la app, los hallazgos de seguridad de riesgos-owasp-seleccionados.md.

Usa SQLite temporal y el cliente de pruebas de Flask: no toca ninguna base de datos, bucket ni servicio real,
y no necesita red. Solo comprueba el comportamiento actual (no lo corrige).

Uso (desde la raiz del repo, con las dependencias de requirements.txt instaladas):
    python seguridad/comprobar_riesgos.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
TMP = tempfile.mkdtemp(prefix="urbanfix-seg-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{TMP}/prueba.db",
    "AWS_ACCESS_KEY_ID": "falsa", "AWS_SECRET_ACCESS_KEY": "falsa", "AWS_REGION": "us-east-1",
    "S3_REPORTES": "bucket-prueba", "S3_PERFILES": "bucket-prueba-perfiles",
    "AWS_ENDPOINT_URL_S3": "http://127.0.0.1:9", "AWS_MAX_ATTEMPTS": "1",
})
os.environ.pop("OTEL_ENABLED", None)

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Categoria, EntidadPublica, Funcionario, Reporte, Usuario  # noqa: E402

app = create_app()
with app.app_context():
    db.create_all()
    db.session.add(EntidadPublica(nombre="Entidad de prueba"))
    db.session.add(Categoria(nombre="Huecos"))
    db.session.flush()
    db.session.add(Funcionario(nombre="Func", email="func@x.co", entidad_id=1, contrasena_hash=generate_password_hash("Clave1234!")))
    db.session.add(Usuario(nombre="Usuario 1", email="test@urbanfix.com", telefono="3001112222",
                           contrasena_hash=generate_password_hash("PasswordSeguro123!"), foto_perfil_url="https://x/1.png"))
    db.session.add(Usuario(nombre="Victima", email="victima@x.co", telefono="3009998888",
                           contrasena_hash=generate_password_hash("OtraClave123!"), foto_perfil_url="https://x/2.png"))
    db.session.flush()
    db.session.add(Reporte(descripcion="d", direccion="d", referencia="r", latitud=4.6, longitud=-74.1, tipo_evento="hueco",
                           img_prueba_1="https://x/r1.png", estado="Nuevo", usuario_creador_id=1, categoria_id=1))
    db.session.commit()

c = app.test_client()
filas = []


def registrar(riesgo, prueba, esperado_si_fuera_seguro, obtenido, detalle=""):
    filas.append((riesgo, prueba, esperado_si_fuera_seguro, obtenido, detalle))
    print(f"[{riesgo}] {prueba}\n      esperado si fuera seguro: {esperado_si_fuera_seguro} | obtenido: {obtenido} {detalle}".rstrip(), flush=True)


# --- A07 Authentication Failures: enumeracion de cuentas y ausencia de limite de intentos ---
r1 = c.post("/login", json={"email": "no-existe@x.co", "contrasena": "x"})
r2 = c.post("/login", json={"email": "test@urbanfix.com", "contrasena": "mala"})
registrar("A07", "POST /login con correo inexistente vs. correo existente con clave mala",
          "mismo codigo y mismo mensaje", f"{r1.status_code} vs {r2.status_code}",
          f"-> {r1.get_json()['message']!r} vs {r2.get_json()['message']!r}")
t0 = time.perf_counter()
codigos = {c.post("/login", json={"email": "test@urbanfix.com", "contrasena": f"mala{i}"}).status_code for i in range(30)}
registrar("A07", "30 intentos fallidos seguidos contra la misma cuenta, sin pausa",
          "bloqueo o 429 antes del intento 30", f"codigos {sorted(codigos)}", f"({time.perf_counter() - t0:.1f} s)")
r = c.post("/login", json={"email": "test@urbanfix.com", "contrasena": "PasswordSeguro123!"})
registrar("A07", "Respuesta de un login correcto", "un token firmado con expiracion",
          f"{r.status_code}, claves {sorted(r.get_json().keys())}", "(sin token ni sesion: no hay forma de probar identidad despues)")

# --- A01 Broken Access Control ---
r = c.get("/usuarios/2")
registrar("A01", "GET /usuarios/2 sin credenciales (datos de otra persona)", "401/403", r.status_code,
          f"-> expone {sorted(k for k in r.get_json() if k in ('email', 'telefono'))}")
r = c.get("/misreportes?user_id=1")
registrar("A01", "GET /misreportes?user_id=1 sin credenciales (el id lo elige quien llama)", "401/403", r.status_code)
r = c.put("/reportes/1/estado", json={"estado": "Resuelto"}, headers={"User-Role": "funcionario", "User-Id": "1"})
registrar("A01", "PUT /reportes/1/estado con cabeceras 'User-Role: funcionario' inventadas", "401/403", r.status_code,
          f"-> estado ahora {r.get_json().get('estado')!r}")
r = c.post("/funcionarios", json={"nombre": "Intruso", "email": "intruso@x.co", "contrasena": "x", "entidad_id": 1})
registrar("A01", "POST /funcionarios sin credenciales (crear una cuenta con rol de funcionario)", "401/403", r.status_code)
r = c.delete("/usuarios/2")
r_despues = c.get("/usuarios/2")
registrar("A01", "DELETE /usuarios/2 sin credenciales", "401/403", r.status_code,
          f"-> despues, GET /usuarios/2 = {r_despues.status_code} (la cuenta ya no existe)")

# --- A02 Security Misconfiguration ---
r = c.get("/test-deploy")
registrar("A02", "GET /test-deploy (endpoint de prueba en el codigo de produccion)", "404", r.status_code, f"-> {r.get_data(as_text=True)[:40]!r}")
codigo_app = (RAIZ / "app.py").read_text(encoding="utf-8", errors="replace")
registrar("A02", "app.py arranca el servidor con debug=True y host 0.0.0.0", "debug=False",
          "debug=True" if "debug=True" in codigo_app else "debug=False", "(el Dockerfile ejecuta `python3 app.py`)")

print("\nResumen:", json.dumps({r[0]: sum(1 for x in filas if x[0] == r[0]) for r in filas}))
