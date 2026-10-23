# Matriz de fallos — Backend UrbanFix

**Entregable:** E1 · Matriz de fallos
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha:** 2026-10-23
**Commit de referencia (`main`):** `dc29ec9`
**Documentos relacionados:** [matriz-resiliencia.md](./matriz-resiliencia.md) · [ADR 0001](../../adrs/0001-decision-estilo.md) · [ADR 0002](../../adrs/0002-aislamiento-persistencia.md) · [ADR 0003](../../adrs/0003-mecanismo-integracion.md) · [04-escenarios-calidad.md](../04-escenarios-calidad.md) · [tactica-resiliencia.md](../../experimentos/tactica-resiliencia.md)

---

## 1. Propósito y alcance

Esta matriz identifica los fallos relevantes del backend de UrbanFix y sirve de base para la [matriz de resiliencia](./matriz-resiliencia.md). Se centra en el backend Flask, donde se concentran los cambios del proyecto. El cliente Android se incluye solo donde su comportamiento determina cómo el ciudadano percibe un fallo del backend.

**Sistema analizado:** el montaje vigente según el README, que tiene tres partes:

- un solo proceso Flask (`python3 app.py`, servidor de desarrollo de Werkzeug, `debug=True`) en un contenedor Docker;
- PostgreSQL 16 local en otro contenedor (`docker-compose.yml`);
- dos buckets de AWS S3.

La configuración original (EC2 + Gunicorn + Neon) no está activa y solo se menciona cuando cambia el análisis.

**Particularidad del sistema.** UrbanFix es un monolito por capas (ADR 0001): las llamadas entre contextos son *in-process* y no cruzan la red. Las únicas fronteras de red del backend son PostgreSQL y S3. Por eso los fallos de esta matriz no son fallos de comunicación entre servicios, sino de **recursos compartidos** (proceso, CPU, pool) y de **dependencias externas**. Que no haya red entre módulos no significa que no haya fallos: un proceso único también sufre contención y cuellos de botella.

### 1.1 Tipos de fallo

Se usa el vocabulario del Módulo 6:

| Tipo | Significado en este sistema |
|---|---|
| **Saturación** | CPU, memoria o conexiones a la BD llegan a un nivel que provoca esperas, rechazos o degradación |
| **Fallo parcial** | Una dependencia (BD, S3) falla o se vuelve lenta mientras el resto del sistema sigue encendido |
| **Cascada** | El fallo de una parte se propaga a otras por recursos compartidos: mismo proceso, mismo pool, misma respuesta |
| **Falso verde** | El sistema responde éxito (`200`/`201`) aunque la operación no se completó |
| **Fallo del instrumento** | La herramienta de medición, y no el sistema, produce o esconde el fallo |

### 1.2 Tipos de evidencia

| Tipo | Significado |
|---|---|
| **Medido** | Resultado de un experimento del equipo con protocolo pre-registrado (ESC-07, Spike 01) |
| **Comprobado** | Reproducido ejecutando el código real de `main` en un entorno aislado, no en la máquina de medición (ver §4) |
| **Inspección** | Se deduce de leer el código o la configuración; el fallo no se ha provocado |
| **Supuesto** | Plausible por diseño o por documentación previa, sin verificación en el repositorio |

---

## 2. Matriz

| ID | Componente o dependencia | Escenario de fallo | Efecto observable | Evidencia | Consecuencia |
|---|---|---|---|---|---|
| **F-01** · Saturación → Cascada | Pool de conexiones de SQLAlchemy (5 + 10 de desborde; `pool_timeout` de 30 s por defecto) | Muchas peticiones concurrentes piden conexión a la vez y el pool se agota | Las peticiones esperan en cola hasta 30 s y luego fallan con `HTTP 500`. El p95 queda pegado a ~30–41 s | **Medido.** ESC-07: error mediano de 11,11 % y p95 de 31,06 s con 800 VUs. Spike 01, línea base: error de 17,94 %, 254 respuestas 500 por corrida y un máximo de 16 conexiones a Postgres. El p95 coincide con el `pool_timeout` por defecto (pre-registro §11) | Falla el inicio de sesión. Como el pool es **compartido** por todos los contextos (ADR 0001), la saturación de `/login` puede bloquear `/reportes` y el resto (fallo en cascada). Esta propagación **no se ha medido**. El tiempo de espera es el valor por defecto de la librería, no uno calibrado con la latencia normal del sistema |
| **F-02** · Saturación | CPU del proceso backend (verificación de contraseña `scrypt:32768:8:1` en cada login) | Una carga concurrente de logins satura la CPU del único proceso | El throughput se estanca en ~13–15 req/s y el p95 queda en ≈ 41 s, con o sin errores | **Medido** (Spike 01). La CPU del backend llegó a ≈ 970–1.117 % en ambos brazos; PgBouncer eliminó los errores, pero el p95 solo bajó un 1,5 %. Que la causa sea `scrypt` es una **sospecha coherente con los datos, no una causa demostrada** | El ciudadano espera decenas de segundos para entrar. Todas las demás peticiones compiten por la misma CPU. **No se ha medido** con cuántos usuarios concurrentes empieza la degradación: ESC-07 y el Spike 01 usaron una rampa continua hasta 800 VUs sin métricas por escalón |
| **F-03** · Fallo parcial | PostgreSQL (contenedor `db` local; Neon en el flujo alternativo) | La base de datos no está disponible: contenedor detenido o reiniciando, red caída o Neon inaccesible | `POST /login` responde `500` con una **página HTML** (no tiene `try/except`). `GET /reportes` responde `500` JSON. `GET /` sigue respondiendo `200` "funcionando" | **Comprobado** (§4, prueba 4): `/login` respondió 500 HTML en 0,02 s; `/reportes`, 500 JSON; `/`, 200. `config.py` tiene `pool_pre_ping=True` | Se pierde toda la funcionalidad: login, reportes, reacciones y perfiles. Ningún componente detecta la caída, porque `/` no consulta la BD y no sirve como chequeo de salud: el servicio está encendido pero no es utilizable. El cliente recibe un 500 genérico, indistinguible de un error de programación |
| **F-04** · Fallo parcial | Arranque coordinado (`docker-compose.yml`) | El backend arranca antes de que Postgres acepte conexiones (`depends_on` sin `condition: service_healthy` ni `healthcheck`) | Las primeras peticiones tras `docker compose up` fallan con 500 hasta que la BD está lista | **Inspección** de `docker-compose.yml` | Hay una ventana de indisponibilidad en cada arranque o reinicio conjunto. También contamina cualquier medición que empiece justo después de levantar el sistema |
| **F-05** · Fallo parcial → **Falso verde** | AWS S3, subida de imágenes de reportes (`upload_base64_to_s3`) | S3 inalcanzable, credenciales inválidas o vencidas, bucket inexistente o sin permisos | La función captura la excepción, imprime un mensaje y **devuelve de todos modos una URL de S3** de un objeto que nunca se subió. `POST /reportes` persiste el reporte y responde `201` | **Comprobado** (§4, prueba 1): con S3 inalcanzable devolvió `https://bucket-prueba.s3.us-east-1.amazonaws.com/<uuid>.png`. El comentario del bloque `except` en `utils.py` indica que es intencional | El reporte queda sin su evidencia fotográfica y nadie se entera. El ciudadano ve "creado", la entidad recibe un reporte con la imagen rota y el único rastro es un `print` en la consola. Es el fallo más grave por invisible: una prueba de carga que solo revise el código HTTP lo daría por exitoso |
| **F-06** · Fallo parcial → Cascada | AWS S3, con latencia alta o conexión colgada | S3 responde muy lento, o la red descarta paquetes sin rechazar la conexión | El hilo que atiende `POST /reportes` (o `PUT /reportes/<id>`) queda bloqueado. `s3_client` usa los valores por defecto de botocore: 60 s de conexión y 60 s de lectura, más reintentos automáticos | **Comprobado** que los timeouts por defecto son de 60 s / 60 s (§4, prueba 5). **Inspección** de `app/__init__.py`: no se pasa `botocore.config.Config`. El bloqueo bajo latencia **no se ha provocado** | Los hilos bloqueados retienen memoria y, si la sesión de BD ya está abierta, conexiones del pool, lo que lo acerca a F-01. La espera del servidor puede superar el `readTimeout` de 60 s del cliente Android (`RetrofitInstance.kt`). Entonces la app muestra un error de red **mientras el servidor puede terminar guardando el reporte**; si el ciudadano reintenta, se crea un **reporte duplicado**, porque no hay idempotencia |
| **F-07** · **Falso verde** | Procesamiento de imagen (Pillow, `Image.open`) | El cliente envía base64 inválido o una imagen corrupta en `img_prueba_1` / `img_prueba_2` | Pasa lo mismo que en F-05: la excepción de Pillow se captura, se devuelve una URL inventada y el reporte se guarda con `201`. En cambio, la foto de perfil con el mismo fallo devuelve `None` y el endpoint responde `500` | **Comprobado** (§4, pruebas 2 y 3) | Se aceptan entradas inválidas como válidas. El chequeo `if img_1_url is None → 400` de `routes.py` solo se activa si el campo viene vacío, nunca ante una imagen corrupta. El comportamiento es inconsistente entre reportes y perfiles |
| **F-08** · Saturación → Cascada | Memoria y CPU del proceso al decodificar imágenes | Una petición con un base64 enorme o una imagen de dimensiones extremas | Sin `MAX_CONTENT_LENGTH`, Flask acepta el cuerpo completo. El base64, los bytes decodificados, la imagen y el PNG re-codificado conviven en la memoria del único proceso | **Comprobado** que `MAX_CONTENT_LENGTH = None` (§4). El efecto sobre la memoria es un **supuesto**: el ADR 0001 lo anticipa como consecuencia negativa ("todo el proceso de Flask se cae, inhabilitando también la autenticación") | Una sola petición puede degradar o tumbar el proceso para todos los usuarios (ver F-12). Pillow solo corta las imágenes que superan su límite de píxeles (protección contra *decompression bomb*); por debajo de ese límite no hay tope |
| **F-09** · Fallo parcial | Consistencia entre S3 y PostgreSQL en `POST /reportes` | Las imágenes se suben y luego falla el `commit`. Causas posibles: falta `tipo_evento`, que no está en `required_fields`; se viola una restricción; la BD se cae | `rollback` y respuesta `500`, pero las imágenes ya están en S3 | **Inspección** de `routes.py` (`handle_reportes`): el propio comentario reconoce que debería borrar las imágenes y no lo hace | Quedan objetos huérfanos en S3. Eso implica costo de almacenamiento y **fotos de ciudadanos sin reporte asociado ni finalidad**, en tensión con el principio de finalidad de la Ley 1581 de 2012. Es el problema que en un sistema distribuido resolvería una acción compensatoria (saga) |
| **F-10** · Saturación | Listados `GET /reportes` y `GET /reportes/geojson` | Crece el número de reportes en la base | La latencia crece en proporción al número de reportes. No hay paginación, y `Reporte.to_dict()` ejecuta ~4 consultas por reporte (likes, dislikes, categoría y creador). El GeoJSON hace 1 consulta de categoría por reporte (patrón N+1) | **Inspección** de `models.py` y `routes.py`. El ADR 0003 lo declara como consecuencia negativa: "rendimiento del listado sin medir" | El mapa y el listado son la vista principal de la app; se vuelven lentos y retienen conexiones del pool más tiempo, lo que agrava F-01. Es un supuesto del ADR 0003 pendiente de medir |
| **F-11** · Cascada | Conteo del respaldo comunitario (REL-06: Reportes → Validación, tabla `apoyos`) | Falla una de las consultas de conteo dentro de `to_dict()`: tabla bloqueada, error de consulta o timeout | Falla **la respuesta completa** del listado (`500`), no solo el conteo de ese reporte | **Inspección** de `models.py`. El ADR 0003 lo declara como consecuencia negativa ("un fallo al contar reacciones sigue haciendo fallar la respuesta completa del reporte") | Un dato secundario e informativo (apoyos y denuncias) tumba la función principal, que es ver los reportes. Es el acoplamiento dinámico de REL-06 dentro de un mismo proceso: el fallo de un contexto de soporte se propaga al contexto central |
| **F-12** · Cascada | Proceso único de Flask / contenedor `urbanfixbackend` | El proceso termina por una excepción fatal, falta de memoria (OOM) o un fallo del intérprete | Todos los endpoints dejan de responder (conexión rechazada) hasta que Docker reinicia el contenedor (`restart: always`) | **Inspección** de `docker-compose.yml` y del ADR 0001 (un solo espacio de memoria y un solo pool). El tiempo de recuperación **no se ha medido** | Caen todos los contextos a la vez: autenticación, reportes y validación. Las peticiones en curso se pierden. Es el punto único de falla que el doc 03 deja como riesgo remanente |
| **F-13** · Saturación | Servidor de aplicación (Werkzeug, `debug=True`, `host 0.0.0.0`) | Se usa el servidor de desarrollo para servir tráfico, sin gestor de procesos ni *workers* | No hay aislamiento entre peticiones a nivel de proceso. Ante una excepción no capturada (en `/login`, por ejemplo), el modo debug devuelve la página de diagnóstico de Werkzeug | **Inspección** de `app.py` y del `dockerfile` (`CMD ["python3", "app.py"]`). `requirements.txt` no incluye Gunicorn, aunque el doc 01 lo menciona para producción | La capacidad es acotada y no hay recuperación de *workers* individuales. Además expone información interna del servidor a cualquiera que llegue al puerto 5000, un riesgo de seguridad que se suma al tráfico HTTP plano verificado en el doc 03 |
| **F-14** · Concurrencia | Reacciones concurrentes (`POST /reportes/<id>/reaccion`) | El mismo actor envía dos reacciones simultáneas al mismo reporte (doble toque o reintento del cliente) | La segunda inserción viola `uq_usuario_reporte` / `uq_funcionario_reporte`; el endpoint hace `rollback` y responde `409` | **Inspección** de `models.py` (restricciones únicas) y de `routes.py` (`except IntegrityError → 409`) | Es un fallo **ya contenido**: se conserva "una reacción por actor" y el reintento es efectivamente idempotente. Se incluye como contraste, porque es el único camino del backend con manejo explícito de concurrencia |
| **F-15** · Fallo parcial (visto por el cliente) | Cliente Android ante un backend caído o lento (ESC-02) | El backend no responde o tarda | Retrofit espera hasta 60 s (conexión), 60 s (lectura) y 90 s (escritura) antes de mostrar `error_network_connection` | **Inspección** de `RetrofitInstance.kt` y `ReportViewModel.kt` (repositorio frontend) | El ciudadano puede esperar un minuto o más antes de ver un error, cuando ESC-02 pedía un mensaje en ≤ 3 s. No se verificó si el borrador del reporte se conserva. ESC-02 figura como descartado en el doc 04 por el montaje local |
| **F-16** · Fallo parcial → Falso verde | Gemini AI (consumido desde el cliente, ESC-03) | La API de Gemini falla, excede 10 s o rechaza la clave | `AIService.kt` captura la excepción y **devuelve el texto del error** (por ejemplo, "Error HTTP 429: …") como si fuera la descripción | **Inspección** de `AIService.kt` (timeouts de 10 s). El backend **no** llama a Gemini (doc 04 §7.2) | El backend no se ve afectado. Pero el reporte puede llegar con un mensaje de error como descripción si el ciudadano no lo edita. No se verificó en la interfaz |
| **F-17** · Fallo del instrumento | Generador de carga k6 (corre en la misma laptop que el sistema) | k6 apunta a una dirección inalcanzable, compite por CPU con el backend o agota sus propios recursos | Los errores o la latencia medidos pertenecen al instrumento y no al sistema | **Medido** (E3 §4). La primera tanda del Spike 01 se descartó porque k6 apuntaba a `172.18.0.1`, inalcanzable desde Windows. La CPU de k6 no se midió (E3 §8) | Sin control, se puede atribuir al backend una degradación que causa la máquina generadora. Como el backend satura la CPU (F-02) en el mismo equipo donde corre k6, este riesgo es real en todas las mediciones del proyecto |

---

## 3. Lectura de la matriz

**Fallos con mayor consecuencia.** F-01, F-02, F-03 y F-12 dejan sin servicio a todos los contextos porque comparten proceso, CPU y pool (ADR 0001). En un monolito, el "fallo en cascada" no viaja por la red: viaja por el recurso compartido. F-05 y F-07 son los más peligrosos por invisibles. Son falsos verdes: el sistema responde "éxito" y pierde la evidencia del reporte, que es justamente lo que sustenta el derecho de petición.

**Lo que está medido y lo que no.** Solo F-01, F-02 y F-17 tienen evidencia de experimentos con protocolo (ESC-07 y Spike 01, ambos sobre `/login` en local). Otros fallos se comprobaron ejecutando el código real en un entorno aislado:

- F-03, F-05 y F-07;
- F-06, solo en cuanto a los timeouts por defecto;
- F-08, solo en cuanto a la ausencia de límite de tamaño.

El resto se apoya en inspección o en supuestos ya declarados en los ADR. Ningún fallo de `POST /reportes` ni de `GET /reportes` tiene medición bajo carga.

**Tácticas ya presentes en el código.** Existen tres, y ninguna tiene una prueba que demuestre que funciona:

- `pool_pre_ping=True`, para recuperar conexiones muertas tras F-03;
- `restart: always`, para reiniciar tras F-12;
- `UniqueConstraint` + `409`, para contener F-14.

---

## 4. Comprobaciones ejecutadas para esta matriz

**Entorno.** Las pruebas se ejecutaron en un entorno aislado, no en la laptop de medición:

- copia de `app/` y `config.py` de `main` (`dc29ec9`);
- Python 3 con las versiones de `requirements.txt` para Flask 3.1.2, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.43 y boto3 1.40.55;
- `DATABASE_URL` apuntando a un puerto cerrado;
- el endpoint de S3 apuntando a otro puerto cerrado (`AWS_ENDPOINT_URL_S3`, `AWS_MAX_ATTEMPTS=1`), con credenciales falsas;
- el cliente de pruebas de Flask.

No se usaron buckets ni bases de datos reales.

| # | Prueba | Resultado obtenido | Fallo |
|---|---|---|---|
| 1 | `upload_base64_to_s3(<PNG válido de 10×10>)` con S3 inalcanzable | Devuelve `https://bucket-prueba.s3.us-east-1.amazonaws.com/<uuid>.png`, aunque el objeto no existe | F-05 |
| 2 | `upload_base64_to_s3(base64("no soy una imagen"))` | Devuelve otra URL inventada | F-07 |
| 3 | `upload_profile_pic_to_s3(<PNG válido>)` con S3 inalcanzable | Devuelve `None` (el endpoint respondería 500) | F-07 |
| 4 | BD inalcanzable: `POST /login`, `GET /reportes`, `GET /` | `500` HTML en 0,02 s · `500` `{"message":"Error al obtener los reportes."}` · `200` "¡La aplicación estructurada está funcionando!" | F-03 |
| 5 | Configuración efectiva | `MAX_CONTENT_LENGTH = None`; botocore: `connect_timeout = 60`, `read_timeout = 60` | F-06, F-08 |

**Límites de estas comprobaciones.** Con un puerto cerrado, la conexión se rechaza al instante. Una BD o un S3 que **cuelgan** la conexión sin rechazarla producirían esperas largas, y eso no se probó. Estas pruebas confirman el camino que sigue el código, no el comportamiento bajo carga. Deben repetirse en la máquina de medición como parte de la matriz de resiliencia.

---

