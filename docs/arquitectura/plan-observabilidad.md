# Plan de observabilidad — Backend UrbanFix

**Entregable:** Módulo 7 · Plan de observabilidad
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha:** 2026-11-06
**Commit de referencia (`main`):** `7d59b58`
**Documentos relacionados:** [matriz-fallos.md](./matriz-fallos.md) · [matriz-resiliencia.md](./matriz-resiliencia.md) · [riesgos-owasp-seleccionados.md](./riesgos-owasp-seleccionados.md) · [ADR 0001](../../adrs/0001-decision-estilo.md) · [ADR 0003](../../adrs/0003-mecanismo-integracion.md) · [ADR 0004](../../adrs/0004-decision-distribucion.md) · [crecimiento.md](../../experimentos/crecimiento.md) · [observabilidad/README.md](../../observabilidad/README.md)

---

## 1. Objetivo

Que el equipo pueda responder, cuando el sistema funciona, se degrada o falla, la pregunta central del sílabo: **si falla en producción, ¿cómo sabríamos qué ocurrió, dónde ocurrió, a quién afectó y qué decisión arquitectónica lo permitió?**

| Pregunta | Cómo se responde | Estado |
|---|---|---|
| ¿Qué ocurrió? | Eventos de log con nombre (`evento`), tipo de error (`error_tipo`) y, si hubo excepción, su traza de pila | Implementado (PoC) |
| ¿Dónde ocurrió? | Traza de la petición: ruta, consultas SQL y llamadas a S3, con la duración de cada etapa | Implementado (PoC) |
| ¿A quién afectó? | Hoy, el `request_id` permite contar las peticiones afectadas por ruta. **No identifica a la persona.** Propuesta: un identificador de usuario seudonimizado en el log (es dato personal, Ley 1581 de 2012) | Parcial · el resto propuesto |
| ¿Qué decisión arquitectónica lo permitió? | La columna "Decisión asociada" de la tabla de la sección 3 | Documentado |

Este plan parte de un hecho verificado en `main`: hoy el único diagnóstico es una serie de **16 `print(f"Error ...")`** en `app/routes.py` y 2 en `app/utils.py`, sin `logging`, sin métricas, sin trazas y sin alertas. Un `print` no tiene nivel, no tiene identificador de petición y desaparece con el contenedor.

## 2. Alcance

**Componentes observados** (con el ID de la [tabla de trazado C4](../07-c4-componentes.md)):

| Componente | ID C4 | Qué se observa |
|---|---|---|
| API Backend (proceso Flask, contenedor `urbanfixbackend`) | C4-2-02 | Peticiones por ruta y código, errores, latencia, excepciones |
| Módulo de Usuarios y Autenticación | C4-3-01 | `/login`: latencia, fallos, intentos rechazados |
| Módulo de Reportes | C4-3-02 | `POST` y `GET /reportes`: latencia, consultas por petición |
| Módulo de Interacciones | C4-3-03 | Reacciones: códigos `409` |
| Utilidades de Almacenamiento (S3) | C4-3-06 | Subidas fallidas y su tipo de error |
| PostgreSQL (contenedor `db`) | C4-2-03 | Disponibilidad y conexiones del pool |

**Operaciones contempladas:** iniciar sesión (ESC-07), crear un reporte con imágenes, listar reportes y reaccionar.

**Fuera de alcance:**
- Cliente Android (C4-2-01) y Gemini (el backend no la llama): los fallos F-15 y F-16 son del cliente y no se observan desde el backend.
- El flujo alternativo EC2 + Gunicorn + Neon: según la matriz de fallos, no está activo. El plan describe el montaje vigente (Docker Compose local).

**Qué está implementado y qué está propuesto.** Esta distinción es parte del entregable:

| Elemento | Estado |
|---|---|
| Logs JSON por petición, evento de fallo de S3 y de BD, `request_id` | **Implementado y ejecutado** en el entorno de preparación (SQLite, sin Docker) |
| Trazas de Flask, SQLAlchemy y S3 (con propagación entre hilos) | **Implementado y ejecutado** en el entorno de preparación |
| Métricas HTTP por ruta y código, conexiones del pool y fallos de S3 | **Implementado y ejecutado** en el entorno de preparación |
| `GET /health` (liveness y readiness con `SELECT 1`) | **Implementado y ejecutado** en el entorno de preparación |
| Exportación OTLP/HTTP al Collector 0.164.0 | **Implementado y ejecutado** de punta a punta con el binario del Collector |
| Imagen Docker, Compose con Collector, PostgreSQL real | **Escrito, sin ejecutar** (no hay Docker en el entorno de preparación) |
| Las 8 alertas, tablero, almacenamiento de métricas | **Propuesto** |
| Métricas de CPU, memoria y reinicios; span del hash de contraseñas; eventos de seguridad; reemplazo de los 16 `print` de `routes.py`; seudónimo de usuario | **Propuesto** |

## 3. Escenarios de fallo (Módulo 6)

Se retoman los escenarios de la [matriz de fallos](./matriz-fallos.md). No se agregan escenarios nuevos. Los IDs de alerta (A-xx) se definen en la sección 8.

| Escenario | Componente | Métrica | Log | Traza | Alerta | Estado de la señal | Decisión asociada |
|---|---|---|---|---|---|---|---|
| **F-01** Pool agotado (medido, ESC-07 y Spike 01) | C4-2-02 / C4-2-03 | `urbanfix.db.pool.connections{estado=en_uso}` ≥ 15; p95 y tasa de 5xx de `/login` | `http_request` con `status=500`; excepción de SQLAlchemy con `trace_id` | `POST /login` con las consultas SQL | A-01, A-02, A-03 | Implementado (PoC) | ADR 0001 (pool compartido) |
| **F-02** CPU saturada por `scrypt` (medido, Spike 01 y E3) | C4-3-01 | p95 de `/login`; CPU del contenedor (propuesta) | — | Propuesto: span `auth.verificar_contrasena` que aísle el costo del hash | A-01, A-07 | p95 implementado · CPU y span propuestos | ADR 0001 (un solo proceso) |
| **F-03** PostgreSQL no disponible (comprobado) | C4-2-03 | Resultado de `/health`; tasa de 5xx | `health_bd_fallo`; excepción `OperationalError` | Span SQL con error; `/login` con excepción | A-04, A-02 | Implementado (PoC) | ADR 0001 (BD única) |
| **F-04** El backend arranca antes que la BD (inspección) | Compose | `/health` en `503` durante el arranque | `health_bd_fallo` en los primeros segundos | — | A-04 (se ignora la ventana de arranque) | Implementado (PoC) | — |
| **F-05** Falso verde en S3 (comprobado) | C4-3-06 | `urbanfix.s3.upload.failures` | `s3_upload_failed` (ERROR, con `bucket` y `error_tipo`) | Span `S3.PutObject` en `Error` **dentro** de un `POST /reportes` que responde `201` | A-05 | Implementado (PoC) · reproducido | Decisión de código en `utils.py` (comentario intencional) |
| **F-06** S3 lento o colgado (timeouts por defecto comprobados) | C4-3-06 | Propuesta: histograma de duración de la subida | — | Span `S3.PutObject` con su duración | A-01 (variante `/reportes`) | Span implementado · métrica propuesta | ADR 0001 (hilos del único proceso) |
| **F-07** Imagen corrupta (falso verde, comprobado) | C4-3-06 | `urbanfix.s3.upload.failures{error_tipo=UnidentifiedImageError}` | `s3_upload_failed` | No hay span de S3 (el error ocurre antes de la subida); el log lo registra | A-05 | Implementado (PoC) · reproducido | — |
| **F-08** Payload o imagen excesivos (límite ausente, comprobado) | C4-2-02 | Propuesta: memoria del contenedor y tamaño de la petición | — | — | A-07 | Propuesto | ADR 0001 (memoria compartida) |
| **F-09** Objetos huérfanos en S3 (inspección) | C4-3-02 / C4-3-06 | — | Hoy el error de `commit` solo sale en un `print` (invisible); propuesta: evento propio | `POST /reportes` en `500` con un span `S3.PutObject` correcto y un `INSERT` fallido | A-02 | Parcial: la traza lo muestra; el detalle sigue en un `print` | — |
| **F-10** Listados con N+1 y sin paginación (inspección) | C4-3-02 | p95 de `GET /reportes` | — | Una petición genera varios spans SQL (se observó el patrón en `POST /reportes`) | A-01 (variante `/reportes`) | Implementado (PoC) | ADR 0003 ("rendimiento del listado sin medir") |
| **F-11** Falla el conteo de apoyos (inspección) | C4-3-02 / C4-3-03 | Tasa de 5xx de `/reportes` | `http_request` con `status=500` | Span `SELECT count(apoyos …)` con error | A-02 | Implementado (PoC) | ADR 0003 (integración síncrona) |
| **F-12** Caída del proceso o del contenedor (inspección) | C4-2-02 | `/health` sin respuesta; reinicios (propuesta) | `observabilidad_iniciada` en cada arranque (marcador de reinicio) | — | A-04, A-06 | Marcador implementado · reinicios por Docker propuestos | ADR 0001 (un solo proceso) |
| **F-13** Servidor de desarrollo con `debug=True` (inspección) | `app.py` | — | La excepción se registra igual | — | Sin alerta: es un defecto de configuración | Ver riesgo A02 en [riesgos-owasp-seleccionados.md](./riesgos-owasp-seleccionados.md) | — |
| **F-14** Reacciones concurrentes (ya contenido) | C4-3-03 | Conteo de respuestas `409` en `/reportes/<id>/reaccion` | — | — | Sin alerta (contenido) | Implementado (PoC), por código de respuesta | — |
| **F-17** Fallo del instrumento de medición (medido, E3) | k6 | CPU de k6 por proceso (ya registrada en el experimento de crecimiento) | — | — | — | Implementado en el protocolo del E3 | — |

**Lo que las señales del PoC ya demostraron** (ver `observabilidad/evidencia/prueba-local.txt`): con S3 inalcanzable, `POST /reportes` responde `201`, y aun así queda un log ERROR `s3_upload_failed`, un span `S3.PutObject` en `Error` dentro de la misma traza y un incremento de `urbanfix.s3.upload.failures`. Sin la instrumentación, el único rastro de ese falso verde era un `print`.

## 4. Métricas

Se usan las métricas RED (tasa, errores, duración) para las peticiones y una de saturación para el pool.

| Métrica | Tipo | Dimensiones | Qué permite detectar | Estado |
|---|---|---|---|---|
| `http.server.request.duration` | Histograma (s) | `http.route`, `http.request.method`, `http.response.status_code` | Latencia p95 por ruta; tasa de 5xx; `409`, `429` y `503` cuando existan | Implementado (PoC) |
| `urbanfix.db.pool.connections` | Gauge | `estado` = `en_uso`, `tamano`, `desborde` | Pool lleno (F-01) antes de que aparezcan errores | Implementado (PoC) |
| `urbanfix.s3.upload.failures` | Contador | `bucket`, `error_tipo` | Falsos verdes de S3 (F-05, F-07) | Implementado (PoC) |
| `db.client.connections.usage` | Gauge | pool | Complemento automático de la instrumentación de SQLAlchemy | Implementado (PoC) |
| CPU y memoria del contenedor `urbanfixbackend` | Gauge | contenedor | Saturación de CPU (F-02) y de memoria (F-08) | Propuesto |
| Reinicios del contenedor | Contador | contenedor | Caída del proceso (F-12) | Propuesto |
| Duración de la subida a S3 | Histograma | `bucket` | S3 lento (F-06) | Propuesto |

**Valores de referencia medidos** para fijar umbrales (del [experimento de crecimiento](../../experimentos/crecimiento.md)): el p95 de `/login` es de 309 ms con 1 usuario, 522 ms con 5 y 731 ms con 10; supera 1 s desde 25 usuarios (1.984 ms); la capacidad es de ≈ 16 logins/s; el pool llega a su tope desde 25 usuarios; y aparecen los primeros `500` con 200 usuarios.

## 5. Logs

Cada línea es un objeto JSON por `stdout` (visible con `docker logs`). Campos comunes: `ts`, `level`, `logger`, `msg`, y, cuando hay una traza activa, `trace_id` y `span_id`, que permiten saltar del log a la traza.

| Evento (`evento`) | Nivel | Contexto que registra | Para qué sirve | Estado |
|---|---|---|---|---|
| `http_request` | INFO / WARNING (4xx) / ERROR (5xx) | `request_id`, `endpoint` (plantilla de la ruta, no la URL), `method`, `status`, `duration_ms` | Reconstruir qué pasó con una petición y contar las afectadas | Implementado (PoC) |
| `s3_upload_failed` | ERROR | `bucket`, `error_tipo` | Detectar los falsos verdes de F-05 y F-07 | Implementado (PoC) |
| `health_bd_fallo` | ERROR | `error_tipo` | Detectar la BD caída (F-03) | Implementado (PoC) |
| `observabilidad_iniciada` | INFO | — | Marcar cada arranque (conteo de reinicios, F-12) | Implementado (PoC) |
| Excepción no controlada | ERROR | Traza de pila, con `trace_id` | Diagnóstico de errores de programación | Implementado (PoC), con el registrador de Flask |
| `login_fallido`, `acceso_denegado`, `recurso_eliminado` | WARNING / INFO | Cuenta seudonimizada, motivo, origen | Seguridad (riesgos A01, A07, A09 de OWASP) | **Propuesto** |
| Error capturado por un `try/except` en las rutas | ERROR | Excepción y contexto | Hoy se emite con `print` y **no es visible** (ver sección 11) | **Propuesto**: reemplazar los 16 `print` por `log.exception` |

**Qué no se registra a propósito:** cuerpos de petición, contraseñas, correos ni teléfonos. Las sentencias SQL se registran con marcadores de posición, sin los valores.

## 6. Trazas

Cada petición produce una traza con un span por etapa: la ruta de Flask, cada consulta de SQLAlchemy y cada llamada de botocore a S3. Se verificó que `POST /login` genera la traza `POST /login → connect → SELECT usuarios → SELECT funcionarios`.

Hay un detalle que la prueba de control confirmó: la subida a S3 (`upload_fileobj`) se ejecuta en **hilos de trabajo**. Sin la instrumentación de hilos, el span `S3.PutObject` queda como una traza aparte y no aparece dentro de la petición que lo originó ([evidencia](../../observabilidad/evidencia/control-sin-threading.txt)). Con ella, queda como hijo de `POST /reportes`.

**Recorridos que deben poder reconstruirse:**
1. `POST /login`: ruta → consulta de `usuarios` → consulta de `funcionarios` (y, propuesto, el hash de la contraseña como span propio para aislar el costo de `scrypt`).
2. `POST /reportes`: ruta → subida a S3 (1 o 2 imágenes) → `INSERT` → consultas de serialización (apoyos, categoría, usuario).
3. `GET /reportes`: ruta → consulta de reportes → varias consultas por reporte (el patrón N+1 de F-10).

Se traza el 100 % de las peticiones: con el volumen del piloto no hace falta muestreo. La sobrecarga de la instrumentación **no se ha medido** (sección 11).

## 7. Monitoreo

Cómo se consultan las señales hoy y cómo se consultarían con el plan completo.

| Pregunta | Implementado (PoC) | Propuesto |
|---|---|---|
| ¿Qué pasó con esta petición? | `docker logs urbanfixbackend 2>&1 \| Select-String <request_id>` | — |
| ¿Hubo falsos verdes de S3? | `docker logs urbanfixbackend 2>&1 \| Select-String s3_upload_failed` | Panel con el contador `urbanfix.s3.upload.failures` |
| ¿Dónde se fue el tiempo de esta petición? | `docker logs urbanfix-otel-collector 2>&1 \| Select-String <trace_id>` (el exportador `debug` imprime los spans) | Visor de trazas (Jaeger o Tempo) |
| ¿Está sano el servicio? | `curl http://127.0.0.1:5000/health` | Sondeo periódico con `healthcheck` de Docker |
| ¿Cómo va la tasa, el error y la latencia? | — (el `debug` del Collector no almacena métricas) | Tablero de 4 paneles: tasa y p95 por ruta, % de 5xx, conexiones del pool en uso, fallos de S3 |

El exportador `debug` del Collector **no es almacenamiento**: sirve para verificar que las señales llegan, no para investigar incidentes. Por eso las alertas y el tablero están propuestos y no implementados.

## 8. Alertas

Todas las alertas están **propuestas**: no hay hoy un sistema que las evalúe ni un canal de notificación. Una alerta detecta un problema; no lo resuelve.

| ID | Condición | Señal evaluada | Por qué importa | A quién se notifica | Procedimiento |
|---|---|---|---|---|---|
| **A-01** | p95 de `http.server.request.duration` > 1 s durante 5 min en `/login` | Métrica | En el E3, el p95 pasa de 1 s con ~25 usuarios y ya hay saturación (≈ 16 logins/s). Umbral **medido**. Para `/reportes` no hay medición: el umbral queda **a calibrar** | Responsable de guardia | OP-01 |
| **A-02** | Más del 5 % de las peticiones con 5xx durante 5 min | Métrica | Es el umbral de error de ESC-07; con 200 usuarios ya aparecen los primeros `500` | Responsable de guardia | OP-02 |
| **A-03** | `urbanfix.db.pool.connections{estado=en_uso}` ≥ 15 durante 1 min | Métrica | El pool (5 + 10) se llenó desde 25 usuarios en el E3: es una alerta temprana de F-01, antes de los errores | Responsable de guardia | OP-01 |
| **A-04** | `/health` distinto de `200` en 3 sondeos seguidos (cada 15 s) | Sondeo | La BD o el proceso están caídos (F-03, F-12). Hoy `GET /` responde `200` aunque la BD esté caída | Responsable de guardia | OP-03 |
| **A-05** | Al menos 1 evento `s3_upload_failed` en 5 min | Métrica y log | Cada fallo es un reporte guardado con una imagen inexistente (F-05, F-07), sin que el ciudadano lo sepa | Responsable de guardia | OP-04 |
| **A-06** | 1 o más reinicios del backend en 10 min | Marcador `observabilidad_iniciada` o `RestartCount` | Indica caída del proceso (F-12) o un despliegue inesperado | Responsable de guardia | OP-03 |
| **A-07** | CPU del backend > 90 % o memoria > 80 % del límite durante 5 min | Métrica (propuesta) | En el E3 el equipo llega al 98 % de CPU desde ~10 usuarios; es la saturación de F-02 y F-08. Umbral **a calibrar**: en reposo el equipo marcó entre 17 % y 44 % | Responsable de guardia | OP-01 |
| **A-08** | Más de 20 respuestas `401` o `404` en `/login` por minuto desde un mismo origen o cuenta | Log y métrica | Posible fuerza bruta o enumeración de cuentas (riesgo A07 de OWASP). Umbral **inicial, a calibrar**. Requiere registrar origen y cuenta seudonimizada, que hoy no se registran | Responsable de seguridad | OP-05 |

**Destinatarios.** "Responsable de guardia" y "responsable de seguridad" son roles propuestos (rotación semanal entre los tres integrantes). El canal de notificación **no está definido en el repositorio**: es una decisión pendiente del equipo.

## 9. Respuesta operativa

**OP-01 · Latencia alta, pool lleno o CPU saturada (A-01, A-03, A-07)**
1. Confirmar con la métrica si el p95 es alto en una ruta o en todas.
2. Mirar `urbanfix.db.pool.connections{estado=en_uso}`: si está en 15, las peticiones esperan una conexión (F-01); si no, no es el pool.
3. Mirar `docker stats urbanfixbackend`: CPU cerca del tope indica saturación de CPU (F-02).
4. Tomar el `trace_id` de una línea `http_request` con `duration_ms` alto y abrir su traza: tiempo en spans SQL apunta a BD o pool; tiempo sin spans hijos apunta a CPU (hash).
5. Guardar los logs antes de reiniciar nada; documentar el hallazgo.

**OP-02 · Errores 5xx (A-02)**
1. Filtrar `http_request` con `status` ≥ 500 y agrupar por `endpoint`.
2. Con el `trace_id` de una de ellas, buscar el log de excepción con el mismo `trace_id`.
3. Si aparece `health_bd_fallo`, seguir OP-03; si aparece `s3_upload_failed`, OP-04.
4. Si el `500` no tiene excepción registrada, el error fue capturado por un `try/except` con `print`: mirar el código de la ruta (limitación de la sección 11).

**OP-03 · BD o proceso caídos (A-04, A-06)**
1. `docker compose ps` y `curl /health`.
2. Revisar los logs del contenedor `db` y contar los eventos `observabilidad_iniciada` recientes.
3. Tras recuperar el servicio, verificar `/health` en `200` **y** un login real cuya respuesta contenga "exitoso": no basta con el código HTTP.

**OP-04 · Falso verde en S3 (A-05)**
1. Leer `error_tipo` del evento `s3_upload_failed`: `EndpointConnectionError` es conectividad; un error de permisos o credenciales apunta a la configuración; `UnidentifiedImageError` es una imagen inválida del cliente.
2. Abrir la traza y revisar el span `S3.PutObject` y su excepción.
3. Identificar los reportes afectados: las peticiones `POST /reportes` con respuesta `201` en la misma ventana. Verificar con `HEAD` si la URL de la imagen existe.
4. Documentar los reportes sin imagen. La corrección (R-07 de la matriz de resiliencia) es un cambio de código, no una acción de la alerta.

**OP-05 · Intentos de acceso anómalos (A-08)**
1. Filtrar `http_request` en `/login` con `401` y `404` por ventana de tiempo.
2. Identificar el origen y las cuentas afectadas (requiere los campos propuestos en la sección 5).
3. Limitar el tráfico con el control de admisión propuesto en R-04 y revisar las cuentas afectadas.

## 10. Herramientas

Cada herramienta debe justificar qué pregunta responde y qué costo introduce. Los costos son cualitativos: **no se midieron** con `docker stats`.

| Herramienta | Qué información obtiene (y de qué componente) | Pregunta que responde | Por qué se necesita | Costo de instalación y operación | Estado |
|---|---|---|---|---|---|
| Módulo `logging` de Python con formato JSON | Eventos de la API Backend, con contexto | ¿Qué ocurrió exactamente? | No agrega dependencias y funciona con `docker logs` | ~100 líneas de código; sin operación adicional | Implementado (PoC) |
| OpenTelemetry SDK e instrumentaciones (Flask, SQLAlchemy, botocore, threading) | Trazas y métricas de las rutas, consultas y llamadas a S3, sin tocar las 35 rutas | ¿Dónde ocurrió y cuánto tardó cada etapa? | Estándar abierto y neutro; evita instrumentar a mano cada ruta | 7 paquetes fijados en `requirements-observabilidad.txt`; **sobrecarga sin medir** | Implementado (PoC) |
| Exportador OTLP por HTTP (puerto 4318) | Transporte de trazas y métricas al Collector | — | Evita compilar `grpcio` en la imagen Alpine del proyecto. Se acepta que gRPC es más eficiente; no se midió la diferencia | Ninguno adicional | Implementado (PoC) |
| OpenTelemetry Collector (núcleo, 0.164.0) | Recibe y procesa trazas y métricas de la API Backend | — | Desacopla la app del destino de la telemetría; `memory_limiter` protege a una máquina con poca RAM | 1 contenedor; la configuración usa solo componentes del núcleo. El exportador `debug` no almacena | Configuración validada y probada de punta a punta con el binario; contenedor sin ejecutar |
| Prometheus | Almacena métricas y evalúa las reglas A-01 a A-07 | ¿Cómo evoluciona el sistema y cuándo alertar? | Sin almacenamiento no hay alertas: es lo que falta al PoC | 1 contenedor y retención por configurar. Requiere un exportador de métricas del Collector (distribución *contrib*) o *remote write*, **no validado** | Propuesto |
| Grafana | Tablero de 4 paneles y notificaciones | ¿Cómo va la tasa, el error y la latencia? | Es la forma de "consultar" el monitoreo de la sección 7 | 1 contenedor | Propuesto |
| Visor de trazas (Jaeger o Tempo) | Lectura de trazas | ¿Dónde ocurrió, para trazas de incidentes pasados? | El `debug` del Collector no sirve para investigar; es opcional si el volumen es bajo | 1 contenedor | Propuesto (opcional, decisión pendiente) |
| `docker stats` y `docker inspect` | CPU, memoria y `RestartCount` del contenedor | F-02, F-08 y F-12 | Ya se usaron para medir el E3 | Gratis. Integrarlos al Collector requeriría su receptor `docker_stats` (distribución *contrib*), **no validado** | En uso manual · automatización propuesta |

**Descartadas.** Micrometer y Spring Boot Actuator: pertenecen al ecosistema Java/Spring y UrbanFix es Flask; OpenTelemetry cubre el mismo propósito en Python. Servicios gestionados de pago (Datadog, New Relic): no hay una necesidad demostrada que justifique su costo. Instrumentar a mano cada una de las 35 rutas: no escala y se olvidaría. Una alternativa gestionada de AWS (CloudWatch con X-Ray) no se evaluó: dependería de que el [ADR 0004](../../adrs/0004-decision-distribucion.md) lleve el sistema a esa nube.

**Coherencia con el ADR 0004.** El backend se mantiene como un solo monolito, así que las trazas no cruzan servicios propios: solo PostgreSQL y S3 son fronteras de red. Eso reduce el costo de la propagación de contexto entre procesos, que aquí no hace falta.

## 11. Limitaciones

Lo que todavía **no** se puede observar o no se ha comprobado:

1. **Errores invisibles.** Los 16 `print` de `routes.py` no se tocaron y siguen siendo ciegos: un error capturado por un `try/except` con `print` no genera un log estructurado. Solo se ve como un `500` en las métricas y como un span con error de estado, sin la excepción. Es el caso de F-09.
2. **No hay alertas ni almacenamiento.** Las ocho alertas y el tablero son propuestas. El exportador `debug` solo permite verificar que las señales llegan.
3. **CPU, memoria y reinicios** no se recogen automáticamente (hoy solo con `docker stats` a mano).
4. **"A quién afectó"** solo se responde en número de peticiones. No hay identificador de usuario en los logs. Agregarlo implica tratar datos personales (Ley 1581 de 2012) y definir retención.
5. **Origen de las peticiones** (IP) y cuenta no se registran: A-08 no puede evaluarse todavía.
6. **Sobrecarga de la instrumentación sin medir.** El sistema satura su CPU con ≈ 16 logins/s; trazar el 100 % de las peticiones podría reducir esa capacidad. Debe medirse con el protocolo del experimento de crecimiento (corridas con y sin `OTEL_ENABLED=1`) antes de activarlo en cualquier despliegue.
7. **Entorno de la prueba.** Se ejecutó con SQLite y sin Docker. La imagen, el Compose y el uso con PostgreSQL y `psycopg2` están escritos pero no ejecutados.
8. **Datos personales en las trazas.** La instrumentación de Flask registra la URL de la petición, que puede incluir parámetros como `?user_id=` (ruta `/misreportes`). Habría que redactarlos antes de enviar las trazas fuera de la máquina local.
9. **El cliente Android y Gemini** no emiten telemetría: F-15 y F-16 son invisibles para el backend.
10. **Umbrales a calibrar:** A-01 para `/reportes`, A-07 y A-08 son valores iniciales; solo A-01 para `/login`, A-02 y A-03 salen de mediciones del proyecto.

## 12. Trazabilidad

| Elemento | Ubicación |
|---|---|
| Este plan | `docs/arquitectura/plan-observabilidad.md` |
| Escenarios F-01 a F-17 y tácticas R-xx | [matriz-fallos.md](./matriz-fallos.md) · [matriz-resiliencia.md](./matriz-resiliencia.md) |
| Riesgos OWASP relacionados (A09 y A07) | [riesgos-owasp-seleccionados.md](./riesgos-owasp-seleccionados.md) |
| Módulo de instrumentación | `app/observabilidad.py`; cambios mínimos en `app/__init__.py` y `app/utils.py` |
| Configuración | `observabilidad/otel-collector-config.yaml` · `requirements-observabilidad.txt` · `dockerfile.observabilidad` · `docker-compose.observabilidad.yml` |
| Prueba y cómo repetirla | `observabilidad/probar_local.py` · [observabilidad/README.md](../../observabilidad/README.md) |
| Evidencias de ejecución (entorno de preparación) | `observabilidad/evidencia/prueba-local.txt` · `colector-recibido.txt` · `control-sin-threading.txt` |
| Valores medidos usados en los umbrales | [crecimiento.md](../../experimentos/crecimiento.md) (E3) · [tactica-resiliencia.md](../../experimentos/tactica-resiliencia.md) (Spike 01) |
| Entrega | Rama `observabilidad/plan` y su *pull request*, con los tres autores |

**Verificación pendiente del equipo:** repetir las pruebas en su máquina con Docker (sección B de `observabilidad/README.md`) y adjuntar las cuatro capturas indicadas allí. Las evidencias de este repositorio provienen del entorno de preparación y no sustituyen la ejecución del equipo.

**Uso de IA:** Claude (Anthropic) ayudó a revisar el repositorio, a escribir y probar la prueba de concepto de instrumentación y a redactar este plan. Los umbrales, los destinatarios de las alertas y las decisiones sobre qué herramientas adoptar son del equipo y están por ratificar.
