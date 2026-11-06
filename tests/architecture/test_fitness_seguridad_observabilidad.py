"""Fitness functions de seguridad y observabilidad (ADR 0005): FF-03, FF-04 y FF-05.

  FF-03  Toda ruta fuera de la lista blanca lleva el decorador de autenticacion (@requiere_auth)  -> reglas S-1 y S-2
  FF-04  No hay sentencias print( en app/ (se usa logging estructurado)                           -> regla O-1
  FF-05  debug=True desactivado en app.py y la BD local (data/) ni versionada ni sin ignorar       -> regla S-5 / SEG-05, SEG-09

ESTADO: PENDIENTES. Hoy detectan violaciones reales del codigo de `main`, asi que estan marcadas como fallo esperado
(`xfail` estricto): el CI sigue en verde. Cuando el control correspondiente se implemente, la prueba pasa a cumplirse,
`strict=True` la convierte en error y el PR del control debe quitar la marca `@pendiente(...)`. Asi Git deja registrado
cuando cada regla paso a cumplirse.

Los DETECTORES se verifican siempre con codigo sintetico (pruebas sin marca): demuestran que la regla funciona aunque el
codigo real todavia la viole.

Solo usa la biblioteca estandar, pytest y `git`. Ejecucion: pytest tests/architecture -v
Documentacion: adrs/0005-politica-seguridad-observabilidad.md y docs/arquitectura/fitness-function.md
"""
import ast
import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "app"

# Rutas publicas vigentes (ADR 0005 S-1; CTL-01 de docs/seguridad/03-matriz-riesgos-controles.md). "/" devuelve un texto fijo.
PUBLICAS = {("/login", "POST"), ("/usuarios", "POST"), ("/categorias", "GET"), ("/estados-reporte", "GET"),
            ("/health", "GET"), ("/", "GET")}
DECORADORES_AUTH = {"requiere_auth", "requiere_rol"}


def pendiente(motivo):
    # raises=AssertionError: solo la violacion de la regla cuenta como fallo esperado; un error de codigo (p. ej. sintaxis rota) sigue fallando.
    return pytest.mark.xfail(reason=motivo, strict=True, raises=AssertionError)


def leer(ruta: Path) -> str:
    return ruta.read_bytes().decode("utf-8-sig", errors="replace")


def archivos_app():
    return sorted(APP.rglob("*.py"))


# ----------------------------------------------------------------------------- detectores
def _nombre(nodo):
    if isinstance(nodo, ast.Call):
        nodo = nodo.func
    if isinstance(nodo, ast.Attribute):
        return nodo.attr
    return getattr(nodo, "id", None)


def rutas_sin_proteccion(codigo, nombre="routes.py"):
    """Rutas (metodo + ruta + linea) fuera de la lista blanca cuya funcion no lleva un decorador de autenticacion."""
    encontradas = []
    for nodo in ast.walk(ast.parse(codigo, filename=nombre)):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        protegida = any(_nombre(d) in DECORADORES_AUTH for d in nodo.decorator_list)
        for d in nodo.decorator_list:
            if not (isinstance(d, ast.Call) and _nombre(d) == "route" and d.args and isinstance(d.args[0], ast.Constant)):
                continue
            metodos = ["GET"]
            for kw in d.keywords:
                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    metodos = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
            for metodo in metodos:
                if (d.args[0].value, metodo) not in PUBLICAS and not protegida:
                    encontradas.append(f"{metodo} {d.args[0].value} ({nombre}:{nodo.lineno})")
    return encontradas


def prints_en(codigo, nombre):
    return [f"{nombre}:{n.lineno}" for n in ast.walk(ast.parse(codigo, filename=nombre))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"]


def debug_activado(codigo):
    return re.search(r"debug\s*=\s*True", codigo) is not None


def gitignore_ignora_data(texto):
    return any(l.strip() in ("data", "data/", "/data", "/data/") for l in texto.splitlines())


def archivos_versionados(ruta):
    """Archivos que Git versiona bajo `ruta`. Usa el indice, asi que funciona aunque el checkout sea parcial."""
    try:
        salida = subprocess.run(["git", "ls-files", "--", ruta], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("no se pudo consultar Git en este entorno")
    return [l for l in salida.splitlines() if l.strip()]


# ----------------------------------------------------------------------------- reglas (pendientes hasta implementar el control)
@pendiente("FF-03 pendiente: ninguna ruta lleva @requiere_auth todavia (CTL-01, SEG-01 a SEG-03)")
def test_ff03_toda_ruta_fuera_de_la_lista_blanca_exige_autenticacion():
    violaciones = rutas_sin_proteccion(leer(APP / "routes.py"), "app/routes.py")
    assert not violaciones, ("FF-03 violada: rutas sin @requiere_auth fuera de la lista blanca (ADR 0005, S-1):\n  - "
                             + "\n  - ".join(violaciones))


@pendiente("FF-04 pendiente: los errores se siguen registrando con print( (regla O-1)")
def test_ff04_no_hay_print_en_app():
    violaciones = [v for f in archivos_app() for v in prints_en(leer(f), str(f.relative_to(RAIZ)))]
    assert not violaciones, ("FF-04 violada: usar logging estructurado en lugar de print( (ADR 0005, O-1):\n  - "
                             + "\n  - ".join(violaciones))


@pendiente("FF-05 pendiente: app.py usa debug=True y data/ esta versionada (CTL-05 y CTL-09)")
def test_ff05_debug_desactivado_y_bd_local_no_versionada():
    problemas = []
    if debug_activado(leer(RAIZ / "app.py")):
        problemas.append("app.py arranca con debug=True")
    versionados = archivos_versionados("data")
    if versionados:
        problemas.append(f"data/ esta versionada ({len(versionados)} archivos)")
    gitignore = RAIZ / ".gitignore"
    if not gitignore.exists() or not gitignore_ignora_data(leer(gitignore)):
        problemas.append(".gitignore no ignora data/")
    assert not problemas, "FF-05 violada (ADR 0005):\n  - " + "\n  - ".join(problemas)


# ----------------------------------------------------------------------------- autopruebas de los detectores (siempre corren)
def test_los_detectores_no_son_vacuos():
    assert (APP / "routes.py").exists() and (RAIZ / "app.py").exists()
    assert len(rutas_sin_proteccion(leer(APP / "routes.py"))) + len(PUBLICAS) > 5   # el analisis ve las rutas reales


def test_detector_ff03_con_codigo_sintetico():
    sin = "@main.route('/borrar/<int:i>', methods=['DELETE'])\ndef borrar(i):\n    pass\n"
    con = "@main.route('/borrar/<int:i>', methods=['DELETE'])\n@requiere_auth\ndef borrar(i):\n    pass\n"
    publica = "@main.route('/login', methods=['POST'])\ndef login():\n    pass\n"
    por_defecto_get = "@main.route('/secreto')\ndef secreto():\n    pass\n"
    assert rutas_sin_proteccion(sin) == ["DELETE /borrar/<int:i> (routes.py:2)"]
    assert rutas_sin_proteccion(con) == []
    assert rutas_sin_proteccion(publica) == []
    assert rutas_sin_proteccion(por_defecto_get) == ["GET /secreto (routes.py:2)"]


def test_detector_ff04_con_codigo_sintetico():
    assert prints_en("print('x')\n", "a.py") == ["a.py:1"]
    assert prints_en("log.info('x')\nobj.print('y')\n", "a.py") == []


def test_detector_ff05_con_codigo_sintetico():
    assert debug_activado("app.run(host='0.0.0.0', debug=True)")
    assert not debug_activado("app.run(host='0.0.0.0')")
    assert gitignore_ignora_data(".env\ndata/\n") and not gitignore_ignora_data(".env\nvenv/\n")
