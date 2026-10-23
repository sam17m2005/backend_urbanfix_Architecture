# Fitness function de arquitectura — UrbanFix

**Entregable:** E5 · Fitness function definida
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha:** 2026-10-22
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
- **No bloquea el despliegue por sí sola:** el workflow `deploy.yml` se dispara en cada push a `main` de forma independiente. Para que una violación impida el merge hay que activar en GitHub (*Settings → Branches*) la regla que exige que este check pase.

## 4. Demostración de violación deliberada (la prueba decisiva)

### 4.1 Verificación local previa (entorno de preparación, 2026-10-22)
Sobre una copia del código de `main`, la suite pasa en limpio (6 pruebas) y falla al introducir cada violación:

| Violación introducida | Regla que falla |
|---|---|
| `import pika` al inicio de `app/routes.py` | FF-01 |
| `from .routes import main` al inicio de `app/models.py` | FF-02 |
| `pika==1.3.2` agregado a `requirements.txt` | FF-01 |
| `boto3.client('sqs')` agregado a `app/utils.py` | FF-01 |

### 4.2 Demostración en CI (a completar al ejecutarla)
Procedimiento, sin tocar `main`:

```powershell
git checkout main
git pull
git checkout -b fitness/violacion-demo
# agrega la línea  import pika  al inicio de app/routes.py
git add app/routes.py
git commit -m "demo: violacion deliberada de FF-01 (import pika)"
git push -u origin fitness/violacion-demo
```

En GitHub → *Actions* debe aparecer el workflow "Fitness function (arquitectura)" en rojo. Después se elimina la rama (no se mezcla).

| Campo | Valor |
|---|---|
| Commit con la violación | `<<hash del commit de la rama fitness/violacion-demo>>` |
| Ejecución fallida en CI | `<<enlace a la ejecución del workflow en rojo>>` |
| Mensaje de fallo observado | `<<pegar la línea "FF-01 violada: ..." del log>>` |
| Ejecución del mismo código sin la violación (en `main`) | `<<enlace a la ejecución en verde>>` |

## 5. Mantenimiento

- Si se agrega o cambia una decisión protegida, se actualiza la lista de paquetes de la regla y este documento junto con el ADR correspondiente.
- Si se reorganiza `app/`, la prueba de éxito vacuo falla a propósito para obligar a revisar la regla.

## 6. Trazabilidad

| Elemento | Ubicación |
|---|---|
| Regla ejecutable | `tests/architecture/test_fitness_function.py` |
| Configuración de CI | `.github/workflows/fitness-function.yml` |
| Decisiones protegidas | `adrs/0001-decision-estilo.md` · `adrs/0003-mecanismo-integracion.md` |

**Uso de IA:** Claude (Anthropic) ayudó a diseñar y escribir la regla, el workflow y este documento, y a verificar localmente que detecta las violaciones de la sección 4.1. La demostración en CI (4.2) la ejecuta el equipo.
