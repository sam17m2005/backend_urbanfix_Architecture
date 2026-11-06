"""Fixtures para las pruebas de verificación de controles de seguridad (Módulo 7).

Levanta la app Flask real (app/routes.py, app/models.py) contra una base de datos de prueba en memoria y
reemplaza las subidas a S3 por un doble, para no necesitar red ni credenciales.
"""
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("S3_REPORTES", "bucket-reportes-test")
os.environ.setdefault("S3_PERFILES", "bucket-perfiles-test")


@pytest.fixture()
def app(monkeypatch):
    from app import create_app, db
    from app import routes

    contador = {"n": 0}

    def falso_s3(b64):
        if not b64:
            return None
        contador["n"] += 1
        return f"https://bucket-test.s3.amazonaws.com/{contador['n']}.png"

    monkeypatch.setattr(routes, "upload_base64_to_s3", falso_s3)
    monkeypatch.setattr(routes, "upload_profile_pic_to_s3", falso_s3)

    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def datos(app, client):
    """Dos ciudadanos (A y B), una entidad, un funcionario, una categoría y un reporte de A."""
    from app import db
    from app.models import Categoria, EntidadPublica, Funcionario
    from werkzeug.security import generate_password_hash

    db.session.add(Categoria(nombre="Vías", descripcion="Huecos"))
    ent = EntidadPublica(nombre="IDU")
    db.session.add(ent)
    db.session.commit()
    db.session.add(Funcionario(nombre="Func", email="func@idu.test",
                               contrasena_hash=generate_password_hash("Func-123"),
                               entidad_id=ent.id))
    db.session.commit()

    from app.models import Usuario
    ids = {}
    for clave, email in (("a", "a@test.co"), ("b", "b@test.co")):
        u = Usuario(nombre=clave.upper(), email=email,
                    contrasena_hash=generate_password_hash("Clave-123"),
                    foto_perfil_url=f"https://test/{clave}.png")
        db.session.add(u)
        db.session.commit()
        ids[clave] = u.id
    ids["func"] = Funcionario.query.first().id

    r = client.post("/reportes", json={
        "descripcion": "Hueco", "direccion": "Cra 7", "referencia": "Esquina",
        "latitud": "4.6", "longitud": "-74.07", "usuario_creador_id": ids["a"],
        "categoria_id": 1, "img_prueba_1": "aGVsbG8=", "tipo_evento": "Hueco"})
    assert r.status_code == 201, r.get_json()
    ids["reporte"] = r.get_json()["reporte"]["id"]
    return ids
