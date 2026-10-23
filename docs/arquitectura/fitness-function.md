# Fitness function de arquitectura — UrbanFix

**Entregable:** E5 · Fitness function definida
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha:** 2026-10-23
**Decisiones que protege:** [ADR 0001](../../adrs/0001-decision-estilo.md) (arquitectura por capas) · [ADR 0003](../../adrs/0003-mecanismo-integracion.md) (integración síncrona, sin broker de eventos)

---

## 1. Qué es y qué protege

Una *fitness function* es una regla automatizada que comprueba una característica arquitectónica y falla cuando una decisión registrada se viola. Aquí hay dos reglas, ejecutadas por una misma suite de pruebas:

| Regla | Característica arquitectónica | Decisión protegida | Qué comprueba |
|---|---|---|---|
| **FF-01** | Integración síncrona y simplicidad operativa | ADR 0003: no se introduce broker de eventos | Ningún archivo Python importa un cliente de mensajería (`pika`, `aio_pika`, `kombu`, `celery`, `kafka`, `confluent_kafka`, `aiokafka`), ninguna llamada `boto3.client/resource` usa `sqs`, `sns`, `kinesis`, `events`, `mq` ni `kafka`, y `requirements.txt` no declara paquetes de broker |
| **FF-02** | Dirección de dependencias entre capas | ADR 0001: Presentación → Negocio → Persistencia | `app/models.py` (persistencia) no importa `app/routes.py` (presentación) ni el framework web `flask` |

**Por qué estas reglas.** El ADR 0003 decidió que la integración se mantiene síncrona y que no se adopta un broker; sin una regla ejecutable, esa decisión solo depende de que alguien la recuerde. Las capas del ADR 0001 son lógicas (Blueprints en un solo proceso), por lo que nada impide que la persistencia empiece a depender de la presentación; FF-02 lo impide.

## 2. Cómo se verifica

- **Local:** desde la raíz del repo, `pip install pytest` y luego `pytest tests/architecture -v`.
- **En CI:** `.github/workflows/fitness-function.yml` ejecuta la misma suite en cada `push` y `pull_request`. Si una regla falla, el workflow queda en rojo.
- **Archivo que ejecuta la regla:** `tests/architecture/test_fitness_function.py`. Solo usa la biblioteca estándar y pytest (análisis estático con `ast`): no necesita base de datos, red ni las dependencias de la aplicación.
- **Mensaje de fallo:** indica la regla violada, la decisión que contradice y la línea del archivo. Para cambiar una decisión protegida hay que escribir un ADR nuevo que reemplace al anterior y actualizar la regla.

La suite incluye, además de las dos reglas, una prueba que evita el éxito vacuo (falla si `app/` o `requirements.txt` se mueven o no se pueden leer) y pruebas del propio detector con código sintético.

## 3. Qué detecta y qué no (límites)

- **Detecta:** imports directos de los paquetes listados, llamadas `boto3` a servicios de mensajería y paquetes de broker declarados en `requirements.txt` (que está en UTF-16 y se decodifica explícitamente).
- **No detecta:** brokers usados con otros paquetes no listados, a través de `subprocess`/CLI, imports dinámicos (`importlib`) o servicios externos llamados por HTTP.
- **FF-02 solo revisa `app/models.py`.** No verifica otras dependencias entre capas (por ejemplo, `utils.py` ya importa `flask`).
- **No bloquea el despliegue por sí sola:** el workflow `deploy.yml` se dispara en cada push a `main` de forma independiente. Se observó en el push que subió esta regla: el check de la fitness function salió en verde y el job «Deploy Backend to EC2» corrió y falló por su cuenta, sin relación con la regla. Para que una violación impida el merge hay que activar en GitHub (*Settings → Branches*) la regla que exige que este check pase.

## 4. Demostración de violación deliberada (la prueba decisiva)

### 4.1 Verificación local previa (entorno de preparación, 2026-10-22)
Sobre una copia del código de `main`, la suite pasa en limpio (6 pruebas) y falla al introducir cada violación:

| Violación introducida | Regla que falla |
|---|---|
| `import pika` al inicio de `app/routes.py` | FF-01 |
| `from .routes import main` al inicio de `app/models.py` | FF-02 |
| `pika==1.3.2` agregado a `requirements.txt` | FF-01 |
| `boto3.client('sqs')` agregado a `app/utils.py` | FF-01 |

### 4.2 Demostración en CI (ejecutada el 2026-10-23)

**Qué se hizo, sin tocar `main`:** se creó la rama `fitness/violacion-demo` a partir de `main`, se agregó la línea `import pika` al inicio de `app/routes.py` y se hizo commit directo en esa rama (desde la interfaz web de GitHub). El push disparó el workflow «Fitness function (arquitectura)». Equivalente por terminal:

```powershell
git checkout main
git pull
git checkout -b fitness/violacion-demo
# agregar la línea  import pika  al inicio de app/routes.py
git add app/routes.py
git commit -m "demo: violacion deliberada de FF-01 (import pika)"
git push -u origin fitness/violacion-demo
```

**Evidencia:**

| Campo | Valor |
|---|---|
| Rama de la demostración | `fitness/violacion-demo` (creada desde `main`; se conserva sin mezclar) |
| Commit con la violación | `803c6d7` (`803c6d743670d30856d4fb99f6fbaee247e64f0b`): agrega `import pika` en la línea 1 de `app/routes.py` |
| Ejecución fallida en CI | [Run #3 — resultado *Failure*](https://github.com/sam17m2005/backend_urbanfix_Architecture/actions/runs/39985831676) (workflow «Fitness function (arquitectura)»; job de 8 s, ejecución total de 12 s) |
| Ejecución sin la violación (en `main`) | [Ejecución del commit `af82b1e` — resultado *Success*](https://github.com/sam17m2005/backend_urbanfix_Architecture/actions/runs/39985739220) (job de 8 s) |

**Extracto del log de la ejecución fallida** (`pytest tests/architecture -v`):

```text
test_el_analisis_no_es_vacuo PASSED
test_ff01_el_backend_no_usa_brokers_de_mensajeria FAILED
test_ff02_la_persistencia_no_depende_de_la_presentacion PASSED
test_el_detector_ff01_reconoce_violaciones_sinteticas PASSED
test_el_detector_ff02_reconoce_violaciones_sinteticas PASSED
test_el_detector_de_requirements_lee_utf16_y_versiones PASSED

E  AssertionError: FF-01 violada: se introdujo un broker/cola de mensajeria, lo que contradice el ADR 0003
   (integracion sincrona, sin broker de eventos). Para cambiar esta decision se debe escribir un ADR nuevo
   que reemplace al 0003.
E    - app/routes.py:1 importa 'pika' (cliente de broker de mensajeria)

1 failed, 5 passed in 0.09s
```

**Resultado.** La suite falló únicamente en FF-01, señaló el archivo y la línea de la violación y citó el ADR que contradice; FF-02 y las demás pruebas siguieron pasando. El mismo código sin la violación (ejecución en `main`) salió en verde. Los avisos que GitHub mostró en la ejecución (deprecación de Node.js 20 en las acciones y migración de `ubuntu-latest`) son advertencias informativas del servicio y no afectaron el resultado.

La rama `fitness/violacion-demo` se conserva sin mezclar como evidencia; no debe integrarse a `main`.

## 5. Mantenimiento

- Si se agrega o cambia una decisión protegida, se actualiza la lista de paquetes de la regla y este documento junto con el ADR correspondiente.
- Si se reorganiza `app/`, la prueba de éxito vacuo falla a propósito para obligar a revisar la regla.

## 6. Trazabilidad

| Elemento | Ubicación |
|---|---|
| Regla ejecutable | `tests/architecture/test_fitness_function.py` |
| Configuración de CI | `.github/workflows/fitness-function.yml` |
| Decisiones protegidas | `adrs/0001-decision-estilo.md` · `adrs/0003-mecanismo-integracion.md` |

