"""Pruebas de verificación de controles de seguridad — Módulo 7, Entregable 1.

Cada prueba expresa el comportamiento ESPERADO cuando el control de la matriz
(modulo-7/seguridad/03-matriz-riesgos-controles.md) esté implementado.

Mientras el control no exista, la prueba se marca con xfail(strict=True):
  * Hoy: aparece como XFAIL  -> evidencia de que la vulnerabilidad existe.
  * Cuando se implemente el control: aparece como XPASS y, por ser strict, FALLA,
    obligando a quitar la marca. Así el estado propuesto/implementado queda trazable en Git.

Ejecución:  pytest tests/security -v -rxX
"""
import pytest

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def pendiente(seg):
    return pytest.mark.xfail(strict=True, reason=f"{seg}: control propuesto, no implementado")


# --------------------------------------------------------------------------- Autenticación
@pendiente("SEG-01")
def test_seg01_login_entrega_token(client, datos):
    """El login debe emitir un token firmado de corta duración (no solo datos del usuario)."""
    r = client.post("/login", json={"email": "a@test.co", "contrasena": "Clave-123"})
    assert r.status_code == 200
    assert "access_token" in r.get_json()


@pendiente("SEG-01")
def test_seg01_ruta_protegida_rechaza_peticion_sin_token(client, datos):
    """Sin credencial verificable, crear un reporte a nombre de otro debe dar 401."""
    r = client.post("/reportes", json={
        "descripcion": "x", "direccion": "x", "referencia": "x", "latitud": "4",
        "longitud": "-74", "usuario_creador_id": datos["a"], "categoria_id": 1,
        "img_prueba_1": "aGVsbG8=", "tipo_evento": "x"})
    assert r.status_code == 401


@pendiente("SEG-06")
def test_seg06_login_no_revela_si_la_cuenta_existe(client, datos):
    """Cuenta inexistente y contraseña errada deben responder igual (sin enumeración)."""
    r1 = client.post("/login", json={"email": "noexiste@test.co", "contrasena": "x"})
    r2 = client.post("/login", json={"email": "a@test.co", "contrasena": "x"})
    assert r1.status_code == r2.status_code
    assert r1.get_json() == r2.get_json()


# --------------------------------------------------------------------------- Autorización (IDOR / BOLA)
@pendiente("SEG-02")
def test_seg02_usuario_b_no_puede_borrar_reporte_de_a(client, datos):
    r = client.delete(f"/reportes/{datos['reporte']}?user_id={datos['b']}")
    assert r.status_code in (401, 403)


@pendiente("SEG-02")
def test_seg02_usuario_b_no_puede_cambiar_contrasena_de_a(client, datos):
    r = client.put(f"/usuarios/{datos['a']}", json={"contrasena": "tomada"})
    assert r.status_code in (401, 403)


@pendiente("SEG-02")
def test_seg02_cualquiera_no_puede_eliminar_cuenta_ajena(client, datos):
    r = client.delete(f"/usuarios/{datos['a']}")
    assert r.status_code in (401, 403)


@pendiente("SEG-02")
def test_seg02_comentario_solo_lo_edita_su_autor(client, datos):
    c = client.post(f"/reportes/{datos['reporte']}/comentarios",
                    json={"texto": "original", "usuario_id": datos["a"]})
    cid = c.get_json()["comentario"]["id"]
    r = client.put(f"/comentarios/{cid}", json={"texto": "editado por B"})
    assert r.status_code in (401, 403)


# --------------------------------------------------------------------------- Autorización por rol
@pendiente("SEG-03")
def test_seg03_cabecera_user_role_no_otorga_privilegios(client, datos):
    """Un ciudadano que envía 'User-Role: funcionario' NO debe poder cambiar el estado."""
    r = client.put(f"/reportes/{datos['reporte']}/estado",
                   headers={"User-Role": "funcionario", "User-Id": str(datos["b"])},
                   json={"estado": "Resuelto"})
    assert r.status_code in (401, 403)


@pendiente("SEG-03")
def test_seg03_registro_de_funcionario_no_es_publico(client, datos):
    r = client.post("/funcionarios", json={"nombre": "Falso", "email": "f@x.co",
                                           "contrasena": "x", "entidad_id": 1})
    assert r.status_code in (401, 403)


@pendiente("SEG-03")
def test_seg03_crear_entidad_publica_requiere_rol_admin(client, datos):
    r = client.post("/entidades", json={"nombre": "Entidad falsa"})
    assert r.status_code in (401, 403)


# --------------------------------------------------------------------------- Exposición de datos
@pendiente("SEG-04")
def test_seg04_listado_de_usuarios_no_es_publico(client, datos):
    r = client.get("/usuarios")
    assert r.status_code in (401, 403)


@pendiente("SEG-04")
def test_seg04_perfil_publico_no_expone_email(client, datos):
    r = client.get(f"/usuarios/{datos['a']}/perfil")
    assert "email" not in r.get_json()


@pendiente("SEG-04")
def test_seg04_listado_de_funcionarios_no_expone_email(client, datos):
    r = client.get("/funcionarios")
    assert all("email" not in f for f in r.get_json())


# --------------------------------------------------------------------------- Validación de entrada
@pendiente("SEG-08")
def test_seg08_imagen_invalida_rechaza_el_reporte(client, datos, monkeypatch):
    """Si S3 falla, el backend no debe guardar un reporte con una URL inexistente (falso verde)."""
    from app import utils

    class S3Roto:
        def upload_fileobj(self, *a, **k):
            raise RuntimeError("S3 caído")

    monkeypatch.setattr(utils, "s3_client", S3Roto())
    from app import routes
    monkeypatch.setattr(routes, "upload_base64_to_s3", utils.upload_base64_to_s3)
    png_1x1 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA"
               "60e6kgAAAABJRU5ErkJggg==")
    r = client.post("/reportes", json={
        "descripcion": "x", "direccion": "x", "referencia": "x", "latitud": "4",
        "longitud": "-74", "usuario_creador_id": datos["a"], "categoria_id": 1,
        "img_prueba_1": png_1x1, "tipo_evento": "x"})
    assert r.status_code >= 400


@pendiente("SEG-08")
def test_seg08_rechaza_payload_desmesurado(app, client, datos):
    """Debe existir un límite de tamaño de petición (MAX_CONTENT_LENGTH)."""
    assert app.config.get("MAX_CONTENT_LENGTH") is not None


# --------------------------------------------------------------------------- Configuración segura
@pendiente("SEG-09")
def test_seg09_modo_debug_desactivado_en_punto_de_entrada():
    """app.py no debe arrancar con debug=True (consola Werkzeug = ejecución remota de código)."""
    assert "debug=True" not in (RAIZ / "app.py").read_text(encoding="utf-8")


@pendiente("SEG-09")
def test_seg09_rutas_de_prueba_no_estan_expuestas(client):
    assert client.get("/test-deploy").status_code == 404


@pendiente("SEG-10")
def test_seg10_errores_no_devuelven_excepciones_crudas(client, datos, monkeypatch):
    """Los 500 no deben incluir str(e) (filtra detalles de BD/ORM)."""
    from app import routes

    class ConsultaRota:
        def all(self):
            raise RuntimeError("detalle-interno-sqlalchemy")

    class CategoriaRota:
        query = ConsultaRota()

    monkeypatch.setattr(routes, "Categoria", CategoriaRota)
    r = client.get("/categorias")
    assert "detalle-interno" not in r.get_data(as_text=True)


# --------------------------------------------------------------------------- Secretos y datos en el repo
@pendiente("SEG-05")
def test_seg05_repositorio_no_versiona_datos_de_postgres():
    """La carpeta data/ (cluster de PostgreSQL con usuarios y hashes) no debe estar versionada."""
    assert not (RAIZ / "data" / "PG_VERSION").exists()


@pendiente("SEG-05")
def test_seg05_compose_no_tiene_contrasena_de_bd_en_claro():
    texto = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD: postgres" not in texto


# --------------------------------------------------------------------------- Controles ya presentes (línea base)
def test_base_contrasenas_se_guardan_con_hash(client, datos):
    """Control existente: las contraseñas se almacenan con hash (werkzeug/scrypt), nunca en claro."""
    from app.models import Usuario
    u = Usuario.query.get(datos["a"])
    assert u.contrasena_hash != "Clave-123"
    assert u.contrasena_hash.startswith(("scrypt:", "pbkdf2:"))


def test_base_login_no_devuelve_el_hash(client, datos):
    r = client.post("/login", json={"email": "a@test.co", "contrasena": "Clave-123"})
    assert "contrasena_hash" not in r.get_data(as_text=True)


def test_base_orm_parametriza_consultas(client, datos):
    """Control existente: SQLAlchemy parametriza; un email con inyección no rompe ni autentica."""
    r = client.post("/login", json={"email": "' OR '1'='1", "contrasena": "x"})
    assert r.status_code in (401, 404)
