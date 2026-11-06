# 03 · Matriz de riesgos de seguridad y controles arquitectónicos

**Criterio de calificación:** [04-criterios-evaluacion.md](./04-criterios-evaluacion.md) (P × I, escala 3 × 3).
**Contexto, activos (A#), componentes (C#) y límites (TB#):** [01-contexto-y-alcance.md](./01-contexto-y-alcance.md).
**Pruebas de verificación:** [`tests/security/test_controles_seguridad.py`](../../tests/security/test_controles_seguridad.py) —
línea base en [05-evidencias-verificacion/](./05-evidencias-verificacion/).

---

## 1. Matriz resumen

| ID | Amenaza | Activo | Componente | STRIDE · OWASP | P | I | Riesgo | Control | Estado |
|---|---|---|---|---|---|---|---|---|---|
| SEG-01 | Suplantación de identidad: la API acepta cualquier `usuario_creador_id`, `actor_id` o `usuario_id` | A3, A4, A5 | C2 · TB1 | S · A07, API2 | 3 | 3 | **9 Crítico** | CTL-01 Autenticación con token firmado en el borde de la API | Propuesto |
| SEG-02 | Acceso a objetos ajenos (IDOR/BOLA): editar, borrar o cambiar la contraseña de otra cuenta, reporte o comentario | A1, A2, A3, A5 | C2, C3 | T, E · A01, API1 | 3 | 3 | **9 Crítico** | CTL-02 Autorización por propiedad del recurso | Propuesto |
| SEG-03 | Escalamiento a funcionario/admin con la cabecera `User-Role` o registrándose por `POST /funcionarios` | A4 | C2 · TB1 | E · A01, API5 | 3 | 3 | **9 Crítico** | CTL-03 RBAC + ABAC por entidad en servidor | Propuesto |
| SEG-04 | Volcado de datos personales de todos los usuarios y funcionarios | A2 | C2, C3 | I · A01, API3 | 3 | 3 | **9 Crítico** | CTL-04 Minimización de datos por audiencia | Propuesto |
| SEG-05 | Cluster PostgreSQL (`data/`) y credenciales de BD publicados en el repositorio | A1, A2, A6 | C5, C8 · TB2, TB5 | I · A05, A02 | 3 | 3 | **9 Crítico** | CTL-05 Higiene del repositorio + BD aislada | Propuesto |
| SEG-06 | Fuerza bruta, enumeración de cuentas y denegación de servicio sobre `/login` | A1, A7 | C2 · TB1 | S, D, I · A07, API4 | 3 | 2 | **6 Alto** | CTL-06 Limitación de tasa en el borde + respuesta uniforme | Propuesto |
| SEG-07 | Interceptación de contraseñas y datos en tránsito (HTTP en claro) | A1, A2 | C1, C2 · TB1 | I, T · A02 | 2 | 3 | **6 Alto** | CTL-07 Terminación TLS en proxy inverso | Propuesto |
| SEG-08 | Imágenes base64 sin límite tumban el proceso; reporte guardado con imagen que no existe | A7, A3 | C4 | D, T · API4, A04 | 2 | 3 | **6 Alto** | CTL-08 Validación de entrada y subida desacoplada | Propuesto |
| SEG-09 | Configuración insegura: `debug=True` en `0.0.0.0`, ruta `/test-deploy`, contenedor como root | A7, A8 | C2, C8 | E, I · A05 | 2 | 3 | **6 Alto** | CTL-09 Configuración por entorno endurecida | Propuesto |
| SEG-10 | Errores 500 devuelven `str(e)` con detalles internos | A6 | C2 | I · A05 | 2 | 2 | **4 Medio** | CTL-10 Manejador global de errores | Propuesto |
| SEG-11 | Secretos y credenciales en el cliente: clave Gemini en el código, contraseña en `SharedPreferences` | A1, A6 | C1, C7 · TB4, TB6 | I · A02, A05 | 3 | 2 | **6 Alto** | CTL-11 Ningún secreto en el cliente | Propuesto |
| SEG-12 | Claves AWS estáticas con permisos no acotados; buckets con lectura pública | A2, A3, A6 | C4, C6 · TB3 | I, E · A05, A01 | 2 | 3 | **6 Alto** | CTL-12 Identidad de carga de trabajo y mínimo privilegio en S3 | Propuesto · no verificable |
| SEG-13 | Cadena de entrega: acción de terceros sin fijar, despliegue directo a `main`, dependencias sin auditar | A8 | C8 · TB5 | T · A08, A06 | 1 | 3 | **3 Medio** | CTL-13 Pipeline con controles de integridad | Propuesto |
| SEG-14 | Sin rastro de auditoría: no se puede probar quién cambió un estado o borró un reporte | A4, A5 | C2, C3 | R · A09 | 3 | 1 | **3 Medio** | CTL-14 Registro de eventos de seguridad | Propuesto |

**Controles ya presentes en la línea base (implementados y verificados):**

| ID | Control existente | Evidencia |
|---|---|---|
| BASE-01 | Contraseñas con hash adaptativo (`werkzeug` → `scrypt:32768:8:1`) | `routes.py:26`, `models.py:check_password`; prueba `test_base_contrasenas_se_guardan_con_hash` ✅ |
| BASE-02 | El hash nunca sale en las respuestas (`to_dict` lo excluye) | prueba `test_base_login_no_devuelve_el_hash` ✅ |
| BASE-03 | Consultas parametrizadas por el ORM (mitiga A03 Inyección SQL) | prueba `test_base_orm_parametriza_consultas` ✅ |
| BASE-04 | `.env` excluido por `.gitignore`; sin claves AWS/Neon en el historial del backend (111 commits revisados) | revisión con `git log --all -p`, ver 05 |

---

## 2. Fichas de riesgo y control

### SEG-01 · Suplantación de identidad en la API · **Crítico (9)**

| Campo | Contenido |
|---|---|
| Activo | A3 reportes, A4 estado, A5 validación ciudadana |
| Componente | C2 API — todas las rutas de escritura en `app/routes.py` · límite TB1 |
| Origen | Atacante externo con cualquier cliente HTTP; también un usuario legítimo malintencionado |
| Vulnerabilidad | `POST /login` (`routes.py:41-74`) devuelve los datos del usuario y nada más: no emite sesión ni token. Las rutas posteriores toman la identidad del cuerpo (`usuario_creador_id`, `routes.py:129`; `actor_id`, `:180`; `usuario_id`, `:685`). El propio código lo reconoce: «JWT TOKEN REALMENTE NO TENEMOS» (`:683`). |
| Escenario | Un atacante publica reportes falsos a nombre de un ciudadano real, o automatiza miles de `like` con `actor_id` distintos para subir la prioridad de un reporte ante el IDU. |
| Impacto | Pérdida total de integridad de reportes y de la validación ciudadana; responsabilidad atribuida a personas que no actuaron. |
| Probabilidad | Alta (3): basta `curl`; los IDs son enteros secuenciales. |
| **Control CTL-01** | **Autenticación con token de acceso firmado, verificado en el borde de la API.** `POST /login` emite un JWT de acceso (15 min, firmado HS256 con secreto de entorno o RS256) y un *refresh token* rotativo. Un decorador `@requiere_auth` en un módulo nuevo `app/security/auth.py` valida firma, expiración y emisor, y deja la identidad en `g.actor = {id, rol, entidad_id}`. Las rutas **dejan de leer** `usuario_creador_id`, `actor_id` y `usuario_id` del body y usan `g.actor`. Política *deny by default*: el Blueprint aplica `before_request` y solo una lista blanca (`/login`, `POST /usuarios`, `GET /categorias`, `GET /estados-reporte`) queda pública. |
| Ubicación | Capa de presentación (C2), antes de cualquier lógica de negocio. No requiere estado en memoria: compatible con varias copias del monolito (ADR 0004). |
| Verificación | `test_seg01_login_entrega_token`, `test_seg01_ruta_protegida_rechaza_peticion_sin_token`. Además: prueba con token expirado y con firma alterada → 401. |
| Riesgo residual | Robo del token en el dispositivo (mitiga CTL-11) o en tránsito (CTL-07). Revocación anticipada de tokens de acceso no es inmediata (ventana ≤ 15 min). |

### SEG-02 · Acceso a objetos de otros usuarios (IDOR / BOLA) · **Crítico (9)**

| Campo | Contenido |
|---|---|
| Activo | A1 credenciales, A2 cuentas, A3 reportes, A5 comentarios |
| Componente | C2 + C3: `PUT/DELETE /usuarios/<id>` (`routes.py:621`, `:658`), `PUT/DELETE /funcionarios/<id>` (`:639`, `:666`), `PUT/DELETE /reportes/<id>` (`:868`, `:479`), `PUT/DELETE /comentarios/<id>` (`:702`, `:712`, con `TODO` de permisos), `POST …/foto_perfil` (`:370`, `:400`) |
| Origen | Usuario autenticado o anónimo que cambia el `id` de la URL |
| Vulnerabilidad | Ninguna operación compara al dueño del recurso con quien hace la petición. `PUT /usuarios/<id>` cambia la contraseña sin pedir la actual. |
| Escenario | El atacante recorre `PUT /usuarios/1..N` con `{"contrasena": "x"}` y toma control de todas las cuentas; o borra reportes ajenos en estado `Nuevo`. |
| Impacto | Toma de cuentas masiva, pérdida de datos, afectación a Ley 1581. |
| Probabilidad | Alta (3): verificado en la línea base (las 4 pruebas SEG-02 responden 200). |
| **Control CTL-02** | **Autorización a nivel de objeto en la capa de negocio.** Módulo `app/security/policies.py` con funciones puras `puede_modificar_reporte(actor, reporte)`, `puede_modificar_cuenta(actor, id)`, `puede_modificar_comentario(actor, comentario)`. Cada ruta carga el recurso y llama a la política antes de mutar; si la política niega → 403 (o 404 para no revelar existencia). El cambio de contraseña exige la contraseña actual. Las políticas se prueban de forma unitaria, sin HTTP. |
| Ubicación | Capa de negocio, entre la ruta y el modelo; se apoya en `g.actor` de CTL-01. |
| Verificación | `test_seg02_*` (4 pruebas con dos usuarios A y B, como en el ejemplo del curso). Revisión: toda ruta con `<int:…_id>` y método distinto de GET debe invocar una política (se puede automatizar como fitness function con `ast`, igual que FF-02). |
| Riesgo residual | Rutas alternativas que tocan el mismo recurso (p. ej. la ruta duplicada `POST /reportes/<id>/comentarios` en `:541` y `:679`) deben revisarse una a una; la fitness function lo reduce, no lo elimina. |

### SEG-03 · Escalamiento de privilegios a funcionario o administrador · **Crítico (9)**

| Campo | Contenido |
|---|---|
| Activo | A4 integridad del estado del reporte y del funcionario asignado |
| Componente | C2: `PUT /reportes/<id>/estado` (`routes.py:721-744`), `POST /funcionarios` (`:587`), `POST /entidades` (`:565`), `GET /reportes/<id>` con `User-Role` (`:487`) |
| Origen | Ciudadano o anónimo |
| Vulnerabilidad | El rol se lee de la cabecera `User-Role` escrita por el cliente y el funcionario asignado de `User-Id`. Además, cualquiera puede registrarse como funcionario de cualquier entidad o crear entidades nuevas. No existe rol administrador. |
| Escenario | Un ciudadano envía `User-Role: funcionario` y marca como `Resuelto` un hueco sin reparar; o se registra como «funcionario del IDU» y responde comentarios con la insignia de verificado. |
| Impacto | Reportes cerrados sin atención real; pérdida de confianza institucional; suplantación de una entidad pública. |
| Probabilidad | Alta (3): verificado (las 3 pruebas SEG-03 responden 200/201). |
| **Control CTL-03** | **RBAC en servidor + ABAC por entidad.** Roles `ciudadano`, `funcionario`, `admin` como *claim* firmado del token (CTL-01), nunca de una cabecera. Decorador `@requiere_rol("funcionario")`. Regla de atributo: un funcionario solo cambia el estado de reportes cuya categoría corresponde a su `entidad_id` (tabla de enrutamiento categoría → entidad). Alta de funcionarios solo por `admin` mediante invitación con código de un solo uso; `POST /entidades` solo `admin`. |
| Ubicación | Capa de presentación (decorador de rol) + capa de negocio (regla de entidad). |
| Verificación | `test_seg03_cabecera_user_role_no_otorga_privilegios`, `test_seg03_registro_de_funcionario_no_es_publico`, `test_seg03_crear_entidad_publica_requiere_rol_admin`; más una prueba con funcionario de otra entidad → 403. |
| Riesgo residual | Un funcionario legítimo puede abusar de su rol dentro de su entidad (lo detecta CTL-14, no lo previene). Proceso manual de alta de administradores fuera del sistema. |

### SEG-04 · Exposición masiva de datos personales · **Crítico (9)**

| Campo | Contenido |
|---|---|
| Activo | A2 nombre, email, teléfono, fecha de registro y foto de todos los usuarios y funcionarios |
| Componente | C2/C3: `GET /usuarios` (`routes.py:37`), `GET /usuarios/<id>` (`:77`), `GET /funcionarios` (`:612`), `GET …/perfil` (`:756`, `:782`); `Usuario.to_dict` devuelve `email` y `telefono` |
| Origen | Anónimo en Internet |
| Vulnerabilidad | Listados sin autenticación ni paginación; un único serializador para todas las audiencias. |
| Escenario | Una sola petición `GET /usuarios` entrega la base completa de ciudadanos con correo y teléfono, útil para *phishing* o venta de datos. |
| Impacto | Incidente de datos personales reportable bajo Ley 1581/2012 (SIC). |
| Probabilidad | Alta (3): verificado. |
| **Control CTL-04** | **Minimización por audiencia (DTOs).** Cada modelo expone `to_public()` (id, nombre, iniciales, foto) y `to_private()` (además email, teléfono) y la ruta elige según la política de CTL-02 (`to_private` solo para el propio titular). Se elimina `GET /usuarios`; `GET /funcionarios` devuelve solo nombre, cargo y entidad. Listados con paginación y límite máximo. |
| Ubicación | Capa de presentación (serialización) apoyada en la política de la capa de negocio. |
| Verificación | `test_seg04_listado_de_usuarios_no_es_publico`, `test_seg04_perfil_publico_no_expone_email`, `test_seg04_listado_de_funcionarios_no_expone_email`. |
| Riesgo residual | Los reportes siguen siendo públicos con ubicación e imágenes (necesario para el negocio); una foto puede mostrar rostros o placas → requiere aviso de privacidad y, a futuro, difuminado. |

### SEG-05 · Datos de PostgreSQL y credenciales de BD en el repositorio · **Crítico (9)**

| Campo | Contenido |
|---|---|
| Activo | A1 hashes de contraseña, A2 datos personales, A6 credencial de BD |
| Componente | C5 base de datos, C8 repositorio · TB2, TB5 |
| Origen | Cualquiera que clone el repositorio público |
| Vulnerabilidad | La carpeta `data/` (1.314 archivos, agregada en el commit `92f46ea`) es un *cluster* PostgreSQL completo. Contiene **20 hashes `scrypt` distintos** y más de diez correos con apariencia de cuentas reales, incluidos de dominio institucional (ver 05). `docker-compose.yml` fija `POSTGRES_PASSWORD: postgres` y publica `5432:5432` en todas las interfaces; `data/pg_hba.conf` usa `trust` para conexiones locales y `data/postgresql.conf` tiene `listen_addresses = '*'`. El propio workflow de fitness function lo nota y hace *sparse checkout* para evitarla. |
| Escenario | El atacante clona el repo, levanta la carpeta con `postgres:16`, extrae correos y hashes y ataca los hashes fuera de línea; los usuarios que reutilizan contraseña quedan expuestos en otros servicios. Si el equipo de desarrollo corre el compose en una red compartida, la BD queda accesible con `postgres:postgres`. |
| Impacto | Exposición de datos personales **ya materializada** mientras el repositorio sea público. |
| Probabilidad | Alta (3): la exposición existe hoy. |
| **Control CTL-05** | **Higiene del repositorio y aislamiento de la BD.** (1) `git rm -r --cached data/`, añadir `data/` a `.gitignore` y reescribir el historial (`git filter-repo --path data --invert-paths`), coordinando el *force push* con el equipo. (2) Pedir cambio de contraseña a las cuentas reales afectadas y no reutilizar ese volcado. (3) `docker-compose.yml`: credenciales desde `.env`/`secrets`, `ports: "127.0.0.1:5432:5432"` o sin publicar el puerto (el backend accede por la red interna de compose). (4) `gitleaks` como *pre-commit* y como paso de CI para bloquear secretos y datos. |
| Ubicación | Límite TB5 (repositorio y CI) y TB2 (red de contenedores). |
| Verificación | `test_seg05_repositorio_no_versiona_datos_de_postgres`, `test_seg05_compose_no_tiene_contrasena_de_bd_en_claro`; `gitleaks detect` en verde en CI; `git log --all -- data` vacío tras la reescritura. |
| Riesgo residual | Copias ya clonadas o en *forks* no se pueden recuperar: la exposición pasada se acepta y se trata con el cambio de contraseñas. |

### SEG-06 · Fuerza bruta, enumeración y denegación de servicio en `/login` · **Alto (6)**

| Campo | Contenido |
|---|---|
| Activo | A1 credenciales, A7 disponibilidad |
| Componente | C2 `POST /login` (`routes.py:41-74`) · TB1 |
| Origen | Atacante automatizado |
| Vulnerabilidad | Sin límite de intentos. Responde 404 «La cuenta no existe» y 401 «Credenciales incorrectas»: permite enumerar correos. Cada login cuesta ~0,21 s de CPU (`scrypt`) y el sistema satura a **~16 logins/s** (experimento S11, ADR 0004): unas pocas decenas de peticiones por segundo bastan para dejar sin servicio a *todo* el monolito. |
| Escenario | Con una lista de correos filtrados se confirma cuáles tienen cuenta y se prueban contraseñas comunes; o simplemente se envían 50 logins/s y nadie puede crear reportes. |
| Impacto | Medio (2): toma de cuentas puntuales y caída temporal recuperable. |
| Probabilidad | Alta (3): verificado (`test_seg06` muestra 404 vs 401). |
| **Control CTL-06** | **Limitación de tasa en el borde + respuesta uniforme.** (1) `limit_req` en el proxy inverso de CTL-07 (p. ej. 5 req/min por IP en `/login`) para rechazar *antes* de gastar CPU en Flask; (2) Flask-Limiter por cuenta (10 intentos fallidos/15 min con bloqueo progresivo); (3) misma respuesta 401 y mismo mensaje para cuenta inexistente y contraseña errada, ejecutando un `check_password_hash` ficticio para igualar tiempos. **Trade-off:** no se baja el costo de `scrypt` (protege contra ataques fuera de línea, relevante por SEG-05); se protege la capacidad limitando la tasa. |
| Ubicación | Límite TB1 (proxy) y capa de presentación (decorador en `/login`). |
| Verificación | `test_seg06_login_no_revela_si_la_cuenta_existe`; prueba k6 reutilizando `Pruebas/prueba2.js`: con el límite activo, las peticiones excedentes reciben 429 y el p95 de `GET /reportes` de un usuario legítimo se mantiene bajo 1 s. |
| Riesgo residual | Ataques distribuidos desde muchas IP superan el límite por IP; el registro (`POST /usuarios`) aún revela si un correo existe (409) → aceptado en el piloto. |

### SEG-07 · Datos y contraseñas en tránsito sin cifrar · **Alto (6)**

| Campo | Contenido |
|---|---|
| Activo | A1 contraseñas (viajan en cada login), A2 datos personales, tokens futuros |
| Componente | C1 `RetrofitInstance.kt` (`BASE_URL = "http://54.144.11.53:5000"`), `network_security_config.xml` (`cleartextTrafficPermitted="true"`); C2 Werkzeug/Gunicorn en `:5000` sin TLS |
| Origen | Atacante en la misma red (Wi-Fi pública, TransMilenio, universidad) |
| Vulnerabilidad | HTTP en claro permitido explícitamente en el cliente; el servidor no termina TLS. |
| Escenario | Un atacante en una red Wi-Fi abierta captura el JSON de `/login` con correo y contraseña. |
| Impacto | Alto (3): robo de credenciales, frecuentemente reutilizadas. |
| Probabilidad | Media (2): requiere posición en la red. |
| **Control CTL-07** | **Terminación TLS en un proxy inverso delante de la aplicación.** Nginx (o un ALB de AWS) con certificado Let's Encrypt en `:443`, HSTS, y redirección 80→443; Gunicorn escucha solo en `127.0.0.1:8000`. En el cliente: `BASE_URL` `https://` con dominio, `cleartextTrafficPermitted="false"`. El proxy es también el punto donde se aplica CTL-06. |
| Ubicación | Nuevo contenedor `proxy` en el borde TB1; configuración de red del cliente C1. |
| Verificación | `curl -I http://dominio` → 301 a https; `testssl.sh`/SSL Labs grado A; la app instalada no conecta si se fuerza HTTP; revisión del XML en PR. |
| Riesgo residual | Sin *certificate pinning*, un dispositivo con una CA maliciosa instalada podría interceptar (aceptado en el piloto). |

### SEG-08 · Imágenes sin validar: caída del proceso e integridad del reporte · **Alto (6)**

| Campo | Contenido |
|---|---|
| Activo | A7 disponibilidad del proceso único, A3 integridad del reporte |
| Componente | C4 `app/utils.py` (`upload_base64_to_s3`, `upload_profile_pic_to_s3`) llamado desde `POST/PUT /reportes` y `…/foto_perfil` |
| Origen | Cualquier cliente |
| Vulnerabilidad | No hay `MAX_CONTENT_LENGTH`; la imagen base64 se decodifica y se abre con Pillow sin validar tamaño, dimensiones ni formato, dentro del mismo proceso que atiende login (ADR 0001 ya lo señala como consecuencia negativa). Además, si S3 falla, `upload_base64_to_s3` **igual devuelve la URL** (`utils.py:39-42`): se guarda un reporte cuya imagen no existe (los falsos verdes F-05/F-07 de la matriz de fallos). |
| Escenario | Un JSON de 200 MB o una «bomba de descompresión» PNG agota la memoria y reinicia el contenedor, tumbando también la autenticación. |
| Impacto | Alto (3): caída de todo el servicio y reportes corruptos. |
| Probabilidad | Media (2). |
| **Control CTL-08** | **Validación de entrada en el borde y subida desacoplada.** (1) `MAX_CONTENT_LENGTH = 12 MB` en `Config` y `client_max_body_size` en el proxy; (2) en `utils.py`: `Image.MAX_IMAGE_PIXELS` acotado (p. ej. 25 MP), `image.verify()`, solo PNG/JPEG, y en caso de excepción devolver `None` (la ruta responde 502 y no guarda); (3) esquema de validación de campos (marshmallow/pydantic) para tipos y longitudes; (4) evolución: URL prefirmada `PUT` a S3 para que el binario no pase por Flask. |
| Ubicación | TB1 (proxy), capa de presentación (`Config`, esquemas) y adaptador C4. |
| Verificación | `test_seg08_imagen_invalida_rechaza_el_reporte`, `test_seg08_rechaza_payload_desmesurado`; prueba de una imagen 20 000 × 20 000 → 413/400 sin reinicio del contenedor. |
| Riesgo residual | Contenido inapropiado en imágenes válidas (moderación fuera del alcance). |

### SEG-09 · Configuración insegura de ejecución · **Alto (6)**

| Campo | Contenido |
|---|---|
| Activo | A7, A8 |
| Componente | `app.py:6` (`app.run(host='0.0.0.0', port=5000, debug=True)`), `dockerfile` (`CMD ["python3", "app.py"]`, usuario root, imagen sin fijar), ruta `GET /test-deploy` (`routes.py:861`) |
| Origen | Atacante con acceso de red al puerto 5000 |
| Vulnerabilidad | El montaje medido y documentado ejecuta el servidor de desarrollo con depurador interactivo escuchando en todas las interfaces. Gunicorn no está en `requirements.txt` (ADR 0004). |
| Escenario | Una excepción no controlada expone la consola del depurador de Werkzeug; si el PIN se obtiene o se filtra, hay ejecución de código en el contenedor (que corre como root). |
| Impacto | Alto (3): control del servidor y de las claves AWS del `.env`. |
| Probabilidad | Media (2): el PIN dificulta el ataque, pero el modo de depuración no debe existir fuera del equipo del desarrollador. |
| **Control CTL-09** | **Configuración por entorno endurecida.** `debug` solo desde `FLASK_DEBUG` y apagado por defecto; `CMD` del contenedor con Gunicorn (añadido a `requirements.txt`) en `127.0.0.1` detrás del proxy; `USER app` no root en el Dockerfile; imagen base fijada por *digest*; eliminar `/test-deploy`. |
| Ubicación | Punto de entrada `app.py`, `dockerfile`, `Config`. |
| Verificación | `test_seg09_modo_debug_desactivado_en_punto_de_entrada`, `test_seg09_rutas_de_prueba_no_estan_expuestas`; `docker exec urbanfixbackend id -u` ≠ 0. |
| Riesgo residual | Un desarrollador puede encender `FLASK_DEBUG` en producción por error → se mitiga con revisión de PR. |

### SEG-10 · Fuga de información en errores · **Medio (4)**

| Campo | Contenido |
|---|---|
| Activo | A6 (detalles de esquema, conexión y librerías) |
| Componente | C2: `return jsonify({"error": str(e)}), 500` en `routes.py:530`, `:539`, `:618`, `:700`, `:779`, `:811`; `print` como único registro |
| Origen | Cualquier cliente que provoque una excepción |
| Vulnerabilidad | La excepción cruda viaja al cliente (texto de SQLAlchemy/psycopg2, nombres de tablas, a veces el host de BD). |
| Escenario | El atacante fuerza errores para mapear el esquema y afinar otros ataques. |
| Impacto / P | Medio (2) / Media (2). |
| **Control CTL-10** | **Manejador global de errores.** `@app.errorhandler(Exception)` en `create_app` devuelve `{"error": "Error interno", "id": <uuid>}` y registra la traza completa con `logging` asociada a ese `id`; se reemplazan los `str(e)` en las rutas. |
| Ubicación | Fábrica de la aplicación (`app/__init__.py`). |
| Verificación | `test_seg10_errores_no_devuelven_excepciones_crudas`; `grep -n "str(e)" app/routes.py` sin resultados (puede añadirse a la fitness function). |
| Riesgo residual | Bajo; los registros mismos deben protegerse (no registrar contraseñas ni tokens). |

### SEG-11 · Secretos y credenciales guardados en el cliente · **Alto (6)**

| Campo | Contenido |
|---|---|
| Activo | A6 clave de Gemini, A1 contraseña del usuario |
| Componente | C1/C7: `services/AIService.kt:10` (clave Gemini literal, enviada en la query string, `:59`), `res/values/mapbox_access_token.xml`, `data/UserPreferencesManager.kt` (`saved_password` en claro), `AndroidManifest.xml:14` (`allowBackup="true"`) · TB4, TB6 |
| Origen | Cualquiera que lea el repositorio público del cliente o descompile el APK; malware o respaldo del dispositivo |
| Vulnerabilidad | Secretos embebidos en código de un componente no confiable; contraseña almacenada sin cifrar e incluida en respaldos. |
| Escenario | Un tercero usa la clave de Gemini publicada para su propio consumo, agotando la cuota del proyecto o generando cobros; un respaldo del teléfono expone la contraseña. |
| Impacto | Medio (2): costo y caída de la función de IA; credencial de un usuario. |
| Probabilidad | Alta (3): la clave está en un repositorio público. |
| **Control CTL-11** | **Ningún secreto en el cliente.** (1) **Revocar y rotar de inmediato** la clave de Gemini expuesta. (2) Mover la llamada a Gemini al backend: `POST /ia/descripcion` autenticado (CTL-01) y limitado (CTL-06); la clave vive solo en el servidor. (3) Token de Mapbox público con restricción por aplicación/URL. (4) «Recordarme» guarda el *refresh token* (no la contraseña) en `EncryptedSharedPreferences` respaldado por Android Keystore; `allowBackup="false"`. |
| Ubicación | Límite TB4 (la integración con IA pasa a ser servidor→servidor) y almacenamiento del dispositivo (TB6). |
| Verificación | `gitleaks detect` en el repo del cliente sin hallazgos; la clave antigua responde 400/403 en Google AI Studio; revisión de código de `UserPreferencesManager` en PR. |
| Riesgo residual | La clave antigua sigue en el historial y en *forks* (por eso la rotación es obligatoria); el backend asume el costo de proxy de IA. |

### SEG-12 · Claves AWS estáticas y buckets potencialmente públicos · **Alto (6) · no verificado**

| Campo | Contenido |
|---|---|
| Activo | A3 imágenes de reportes (con ubicación), A2 fotos de perfil, A6 claves AWS |
| Componente | C4/C6: `app/__init__.py` (cliente boto3 con `AWS_ACCESS_KEY_ID`/`SECRET` del `.env`), `utils.py` construye URLs públicas directas `https://bucket.s3…/uuid.png` |
| Origen | Quien obtenga el `.env` (SEG-09, equipo comprometido) o adivine/enumere objetos |
| Vulnerabilidad | Credenciales de larga duración sin rotación documentada; se desconoce el alcance de la política IAM; que el cliente muestre URLs directas implica lectura pública de los buckets. |
| Escenario | Con la clave filtrada se listan y descargan todas las fotos de perfil, o se borran los buckets. |
| Impacto / P | Alto (3) / Media (2). |
| **Control CTL-12** | **Identidad de carga de trabajo y mínimo privilegio.** En EC2: rol IAM de instancia (sin claves en `.env`); fuera de AWS: usuario IAM con política limitada a `s3:PutObject` y `s3:GetObject` sobre `arn:aws:s3:::urbanfix*/*`. *Block Public Access* activado; lectura mediante URLs prefirmadas de vida corta o CloudFront con OAC. Secretos restantes (URL de BD) en AWS SSM Parameter Store. |
| Ubicación | Límite TB3 y configuración de AWS. |
| Verificación | `aws s3api get-public-access-block`, `aws iam simulate-principal-policy` para confirmar que `s3:DeleteBucket`/`ListAllMyBuckets` están denegados; `curl` anónimo a un objeto → 403. **Pendiente: el equipo no tiene evidencia del estado actual de la cuenta AWS.** |
| Riesgo residual | Las URLs prefirmadas compartidas siguen siendo válidas hasta expirar. |

### SEG-13 · Integridad de la cadena de entrega · **Medio (3)**

| Campo | Contenido |
|---|---|
| Activo | A8 código desplegado, acceso SSH a EC2 |
| Componente | `.github/workflows/deploy.yml` (`appleboy/ssh-action@master`, `git reset --hard origin/main`, `sudo systemctl`), `requirements.txt` sin auditoría |
| Origen | Compromiso de una acción de terceros o de una dependencia; push directo a `main` |
| Vulnerabilidad | La acción se referencia por rama móvil (`@master`) y recibe la llave SSH privada; cualquier push a `main` despliega sin revisión. |
| Escenario | Una versión maliciosa de la acción exfiltra `SSH_PRIVATE_KEY`. |
| Impacto / P | Alto (3) / Baja (1): el README indica que este despliegue **no está activo**. |
| **Control CTL-13** | Fijar acciones por SHA; protección de rama `main` con PR obligatorio y la fitness function + `tests/security` como *checks* requeridos; `pip-audit` y Dependabot; usuario de despliegue con `sudo` limitado a reiniciar el servicio. |
| Ubicación | Límite TB5. |
| Verificación | Configuración de *branch protection* visible en GitHub; workflow con `uses: …@<sha>`; `pip-audit` en verde. |
| Riesgo residual | Riesgo de proveedor (GitHub) aceptado. |

### SEG-14 · Repudio: no hay rastro de quién hizo qué · **Medio (3)**

| Campo | Contenido |
|---|---|
| Activo | A4 estado de reportes, A5 comentarios |
| Componente | C2/C3: no existe registro de eventos; `funcionario_asignado_id` se toma de la cabecera `User-Id` (`routes.py:744`) |
| Vulnerabilidad | Las acciones sensibles no dejan registro confiable; el actor registrado es el que el cliente declara. |
| Escenario | Un reporte pasa a `Resuelto` y nadie puede demostrar qué funcionario lo hizo ni cuándo. |
| Impacto / P | Bajo (1) / Alta (3). |
| **Control CTL-14** | Tabla `eventos_seguridad` (append-only: actor del token, acción, recurso, resultado, IP, fecha) escrita en login fallido, cambio de estado, borrados y cambios de contraseña; historial `reporte_estados` con el funcionario del token. |
| Ubicación | Capa de negocio (servicio de auditoría) + persistencia. |
| Verificación | Prueba: cambiar un estado genera exactamente un evento con el `id` del funcionario autenticado. |
| Riesgo residual | Sin monitoreo/alertas sobre los eventos (fuera del alcance del prototipo). |

---

## 3. Controles por ámbito del módulo

| Ámbito | Controles | Cómo se aplica en UrbanFix |
|---|---|---|
| **Autenticación** | CTL-01, CTL-06, CTL-07, CTL-11 | Token firmado de vida corta verificado en cada petición; login limitado y uniforme; credenciales solo por TLS; sin contraseñas en el dispositivo |
| **Autorización** | CTL-02, CTL-03, CTL-04 | Propiedad del recurso (BOLA), rol firmado + entidad (BFLA), minimización por audiencia |
| **Gestión de secretos** | CTL-05, CTL-11, CTL-12 | Fuera del repositorio (gitleaks), fuera del cliente (proxy de IA), fuera del `.env` en producción (rol IAM, SSM), rotación de lo ya expuesto |
| **Superficie de ataque** | CTL-04, CTL-05, CTL-08, CTL-09 | Se eliminan `GET /usuarios`, `/test-deploy`, el puerto 5432 publicado y el depurador; el binario de imágenes sale de Flask |
| **Zero Trust** | CTL-01, CTL-02, CTL-03, CTL-07, CTL-12, CTL-14 | *Verificar explícitamente*: ninguna petición se acepta por venir «de la app». *Mínimo privilegio*: roles, entidad e IAM acotados. *Asumir brecha*: BD sin exponer, secretos fuera de los repos, auditoría para reconstruir incidentes |
| **OWASP Top Ten 2021** | — | A01 (SEG-02, 03, 04), A02 (SEG-05, 07, 11), A04 (SEG-08), A05 (SEG-09, 10, 11, 12), A06/A08 (SEG-13), A07 (SEG-01, 06), A09 (SEG-14). **A03 Inyección** mitigado por el ORM (BASE-03). **A10 SSRF** no aplica: el backend no hace peticiones a URLs provistas por el usuario. |

## 4. Orden de implementación sugerido

1. **Inmediato, sin código de aplicación:** rotar la clave de Gemini (CTL-11) y retirar `data/` del repositorio (CTL-05).
2. **Bloque de identidad:** CTL-01 → CTL-02 → CTL-03 → CTL-04 (cada uno se apoya en el anterior; juntos cierran los cuatro riesgos críticos de la API).
3. **Borde:** CTL-07 + CTL-06 + CTL-08 en el mismo proxy inverso.
4. **Endurecimiento:** CTL-09, CTL-10, CTL-12, CTL-13, CTL-14.

Cada control se integra en un PR propio que quita la marca `xfail` de sus pruebas.
