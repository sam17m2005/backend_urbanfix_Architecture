"""Fitness function de arquitectura de UrbanFix (entregable E5).

Regla automatizada que comprueba caracteristicas arquitectonicas y protege decisiones registradas:

  FF-01  Integracion sincrona, sin broker de eventos   -> protege el ADR 0003
  FF-02  La persistencia no depende de la presentacion  -> protege el ADR 0001 (arquitectura por capas)

Solo usa la biblioteca estandar y pytest: no necesita base de datos, red ni las dependencias de la app.
Ejecucion local:   pytest tests/architecture -v
Ejecucion en CI:   .github/workflows/fitness-function.yml
Documentacion:     docs/arquitectura/fitness-function.md
"""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "app"

# --- FF-01: lo que NO debe aparecer si se mantiene la integracion sincrona (ADR 0003) ---
MODULOS_BROKER = {"pika", "aio_pika", "kombu", "celery", "kafka", "confluent_kafka", "aiokafka"}
PAQUETES_BROKER = {"pika", "aio-pika", "kombu", "celery", "kafka-python", "confluent-kafka", "aiokafka"}
SERVICIOS_AWS_MENSAJERIA = {"sqs", "sns", "kinesis", "events", "mq", "kafka"}  # boto3.client("sqs"), etc.


# ----------------------------------------------------------------------------- utilidades
def leer_texto(ruta: Path) -> str:
    """Lee un archivo de texto tolerando UTF-8 (con o sin BOM) y UTF-16 (requirements.txt del repo)."""
    crudo = ruta.read_bytes()
    if b"\x00" in crudo[:400] or crudo.startswith((b"\xff\xfe", b"\xfe\xff")):
        return crudo.decode("utf-16", errors="replace")
    return crudo.decode("utf-8-sig", errors="replace")


def archivos_python():
    archivos = sorted(APP.rglob("*.py"))
    archivos += [RAIZ / n for n in ("app.py", "config.py") if (RAIZ / n).exists()]
    return archivos


def analizar(codigo: str, nombre: str = "<fuente>") -> ast.AST:
    return ast.parse(codigo, filename=nombre)


def importaciones(arbol: ast.AST):
    """Devuelve (linea, nivel_relativo, modulo, nombres_importados) por cada import."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield nodo.lineno, 0, alias.name, []
        elif isinstance(nodo, ast.ImportFrom):
            yield nodo.lineno, nodo.level, nodo.module or "", [a.name for a in nodo.names]


def llamadas_a_servicios_aws(arbol: ast.AST):
    """Detecta boto3.client("sqs") / boto3.resource("sns") y similares (mensajeria gestionada de AWS)."""
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in ("client", "resource") and nodo.args
                and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str)
                and nodo.args[0].value.lower() in SERVICIOS_AWS_MENSAJERIA):
            yield nodo.lineno, nodo.args[0].value


def nombres_en_requirements(texto: str):
    nombres = set()
    for linea in texto.splitlines():
        linea = linea.split("#")[0].strip()
        if not linea or linea.startswith("-"):
            continue
        nombre = linea
        for sep in ("==", ">=", "<=", "~=", "!=", ">", "<", "[", ";", " "):
            nombre = nombre.split(sep)[0]
        nombres.add(nombre.strip().lower().replace("_", "-"))
    return nombres


def violaciones_ff01_codigo(codigo: str, nombre: str):
    arbol = analizar(codigo, nombre)
    encontradas = []
    for linea, nivel, modulo, _ in importaciones(arbol):
        if nivel == 0 and modulo.split(".")[0] in MODULOS_BROKER:
            encontradas.append(f"{nombre}:{linea} importa '{modulo}' (cliente de broker de mensajeria)")
    for linea, servicio in llamadas_a_servicios_aws(arbol):
        encontradas.append(f"{nombre}:{linea} usa el servicio AWS de mensajeria '{servicio}'")
    return encontradas


def violaciones_ff02_codigo(codigo: str, nombre: str):
    """La capa de persistencia (models.py) no puede importar la presentacion (routes) ni el framework web."""
    arbol = analizar(codigo, nombre)
    encontradas = []
    for linea, nivel, modulo, nombres in importaciones(arbol):
        importa_routes = (
            (nivel >= 1 and modulo.split(".")[0] == "routes")
            or (nivel >= 1 and modulo == "" and "routes" in nombres)
            or (nivel == 0 and (modulo == "app.routes" or modulo.startswith("app.routes.")))
            or (nivel == 0 and modulo == "app" and "routes" in nombres)
        )
        importa_flask = nivel == 0 and modulo.split(".")[0] == "flask"
        if importa_routes:
            encontradas.append(f"{nombre}:{linea} importa la capa de presentacion (routes)")
        if importa_flask:
            encontradas.append(f"{nombre}:{linea} importa el framework web '{modulo}'")
    return encontradas


# ----------------------------------------------------------------------------- pruebas de la regla
def test_el_analisis_no_es_vacuo():
    """Evita que la regla 'pase' sin mirar nada si se renombran o mueven los archivos."""
    assert APP.is_dir(), "No existe app/: la fitness function debe actualizarse junto con la estructura"
    assert (APP / "routes.py").exists() and (APP / "models.py").exists()
    assert (RAIZ / "requirements.txt").exists()
    assert len(archivos_python()) >= 4
    # si requirements.txt no se decodifica bien, la regla pasaria sin leer nada
    assert "flask" in nombres_en_requirements(leer_texto(RAIZ / "requirements.txt"))


def test_ff01_el_backend_no_usa_brokers_de_mensajeria():
    """FF-01 (ADR 0003): la integracion entre contextos es sincrona; no hay broker de eventos."""
    violaciones = []
    for ruta in archivos_python():
        violaciones += violaciones_ff01_codigo(leer_texto(ruta), str(ruta.relative_to(RAIZ)))
    paquetes = nombres_en_requirements(leer_texto(RAIZ / "requirements.txt")) & PAQUETES_BROKER
    violaciones += [f"requirements.txt declara el paquete de broker '{p}'" for p in sorted(paquetes)]
    assert not violaciones, (
        "FF-01 violada: se introdujo un broker/cola de mensajeria, lo que contradice el ADR 0003 "
        "(integracion sincrona, sin broker de eventos). Para cambiar esta decision se debe escribir un "
        "ADR nuevo que reemplace al 0003.\n  - " + "\n  - ".join(violaciones)
    )


def test_ff02_la_persistencia_no_depende_de_la_presentacion():
    """FF-02 (ADR 0001): arquitectura por capas; las dependencias van de presentacion hacia persistencia."""
    ruta = APP / "models.py"
    violaciones = violaciones_ff02_codigo(leer_texto(ruta), "app/models.py")
    assert not violaciones, (
        "FF-02 violada: la capa de persistencia depende de la presentacion, lo que invierte el sentido de "
        "las capas del ADR 0001.\n  - " + "\n  - ".join(violaciones)
    )


# ----------------------------------------------------------------------------- autoprueba del detector
def test_el_detector_ff01_reconoce_violaciones_sinteticas():
    assert violaciones_ff01_codigo("import pika\n", "x.py")
    assert violaciones_ff01_codigo("from celery import Celery\n", "x.py")
    assert violaciones_ff01_codigo("import boto3\nsqs = boto3.client('sqs')\n", "x.py")
    assert not violaciones_ff01_codigo("import boto3\ns3 = boto3.client('s3')\n", "x.py")


def test_el_detector_ff02_reconoce_violaciones_sinteticas():
    assert violaciones_ff02_codigo("from .routes import main\n", "m.py")
    assert violaciones_ff02_codigo("from . import routes\n", "m.py")
    assert violaciones_ff02_codigo("from flask import request\n", "m.py")
    assert not violaciones_ff02_codigo("from . import db\nfrom sqlalchemy import func\n", "m.py")


def test_el_detector_de_requirements_lee_utf16_y_versiones(tmp_path):
    archivo = tmp_path / "requirements.txt"
    archivo.write_bytes("Flask==3.1.2\npika>=1.3  # broker\nKafka_Python==2.0\n".encode("utf-16"))  # UTF-16 con BOM
    assert nombres_en_requirements(leer_texto(archivo)) >= {"flask", "pika", "kafka-python"}
