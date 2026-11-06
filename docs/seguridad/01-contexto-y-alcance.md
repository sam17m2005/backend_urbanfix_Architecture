# 01 · Contexto y alcance del análisis de seguridad

**Proyecto:** UrbanFix · **Módulo:** 7 — Seguridad por diseño · **Entregable:** 1 — Matriz de riesgos de seguridad y controles arquitectónicos
**Repositorios analizados:** `backend_urbanfix_Architecture` (prioritario) · `UrbanFix_Architecture` (cliente Android)
**Commit de referencia del backend:** `7d59b58` (ADR 0004) · **Cliente:** `2f5b706` · **Fecha del análisis:** 2026-11-06

> Este análisis parte del checklist de seguridad heredado de Ingeniería de Software (fila *Seguridad* de
> [`docs/02-stakeholders-drivers.md` §2.1](../../docs/02-stakeholders-drivers.md)) y lo convierte en un modelado de
> amenazas sobre el sistema completo. La tabla de la §8 muestra cómo cada ítem del checklist se transformó en riesgos.

---

## 1. Sistema analizado

UrbanFix es una app Android (Kotlin + Jetpack Compose) con la que los ciudadanos reportan daños del espacio público
(foto + geolocalización + descripción generada por Gemini) y los funcionarios de entidades (IDU, UAESP, EAB, alcaldías
locales) cambian el estado del reporte (`Nuevo → En proceso → Resuelto`). El backend es un **monolito Flask por capas en
un solo proceso** ([ADR 0001](../../adrs/0001-decision-estilo.md), [ADR 0004](../../adrs/0004-decision-distribucion.md)),
con PostgreSQL (local en Docker o Neon) y dos buckets S3.

**Driver de calidad:** Seguridad está priorizada como **Crítica** junto con Disponibilidad (02 §2.2), por la Ley 1581 de
2012 (datos personales: correo, teléfono, ubicación e imágenes).

## 2. Alcance

| Dentro del alcance | Fuera del alcance (y por qué) |
|---|---|
| API REST Flask (`app/routes.py`, 30 rutas; `app/models.py`, `app/utils.py`, `config.py`, `app.py`) | Infraestructura AWS real (EC2, IAM, políticas de bucket): no tenemos acceso de lectura para verificarla — se registra como supuesto |
| Persistencia PostgreSQL (`docker-compose.yml`, carpeta `data/` versionada, migraciones) | Pruebas de penetración contra la IP pública de EC2: el README indica que el despliegue no está activo y no está autorizado probarlo |
| Integración con S3 (boto3) | Seguridad interna de Gemini, Mapbox, Neon y AWS (se confía en el proveedor) |
| Cliente Android: red, almacenamiento local, secretos embebidos | Ofuscación / ingeniería inversa del APK más allá de lo visible en el código fuente |
| Cadena de entrega: GitHub, workflows `deploy.yml` y `fitness-function.yml`, Dockerfile | |

## 3. Componentes principales

| ID | Componente | Tecnología | Evidencia |
|---|---|---|---|
| C1 | App móvil | Kotlin, Retrofit, SharedPreferences | `network/RetrofitInstance.kt`, `data/UserPreferencesManager.kt` |
| C2 | API Backend (capa de presentación) | Flask 3.1 Blueprint `main` | `app/routes.py` |
| C3 | Modelos / negocio | SQLAlchemy 2.0, werkzeug.security | `app/models.py` |
| C4 | Adaptador de imágenes | Pillow + boto3 | `app/utils.py` |
| C5 | Base de datos | PostgreSQL 16 (compose) / Neon | `docker-compose.yml`, `config.py`, `data/` |
| C6 | Almacenamiento de objetos | AWS S3 (2 buckets) | `config.py`, `utils.py` |
| C7 | IA y mapas | Gemini `gemini-2.0-flash`, Mapbox | `services/AIService.kt`, `res/values/mapbox_access_token.xml` |
| C8 | Cadena de entrega | GitHub (repos públicos), Actions, Docker | `.github/workflows/*`, `dockerfile` |

## 4. Actores

| Actor | Confianza | Qué puede hacer hoy |
|---|---|---|
| Ciudadano | Autenticado *solo en la app* | Crear/editar/borrar reportes, reaccionar, comentar, editar perfil |
| Funcionario | Autenticado *solo en la app* | Además: cambiar el estado de un reporte |
| Administrador de entidades | **No existe como rol** | Crear entidades y funcionarios lo hace cualquiera (`POST /entidades`, `POST /funcionarios`) |
| Atacante externo | No confiable | Cualquier cliente HTTP llega a las mismas 30 rutas: **la API no verifica identidad** (comentarios en `routes.py:683` y `:729`) |
| Equipo de desarrollo | Confiable | Push a `main`, acceso a `.env`, AWS y Neon |
| Proveedores (AWS, Neon, Google, Mapbox, GitHub) | Confiables con contrato | Procesan datos y credenciales del sistema |

## 5. Activos a proteger

| ID | Activo | Clasificación | Dónde vive |
|---|---|---|---|
| A1 | Credenciales de usuarios y funcionarios (hashes `scrypt`) | Confidencial | tabla `usuarios`, `funcionarios` |
| A2 | Datos personales: nombre, email, teléfono, foto de perfil | Personal (Ley 1581) | BD + bucket de perfiles |
| A3 | Reportes: ubicación, imágenes, descripción, autor | Personal / público | BD + bucket de reportes |
| A4 | Integridad del estado del reporte y del funcionario asignado | Integridad institucional | `reportes.estado`, `funcionario_asignado_id` |
| A5 | Integridad de la validación ciudadana (likes/dislikes, comentarios) | Integridad | `apoyos`, `comentarios` |
| A6 | Secretos: AWS keys, URL/contraseña de BD, clave Gemini, token Mapbox | Secreto | `.env`, `docker-compose.yml`, código del APK |
| A7 | Disponibilidad del proceso Flask (un solo proceso para todo, ADR 0001) | Disponibilidad | contenedor `urbanfixbackend` |
| A8 | Integridad del código desplegado | Integridad | GitHub → EC2 |

## 6. Puntos de entrada

Todas las rutas están en `app/routes.py` y **ninguna exige credencial**. La identidad del actor viaja en el cuerpo, en la
query string o en cabeceras escritas por el cliente.

| Grupo | Rutas | Cómo se identifica al actor hoy |
|---|---|---|
| Identidad | `POST /login`, `POST /usuarios`, `POST /funcionarios` | No aplica (registro y login abiertos) |
| Cuentas | `GET /usuarios`, `GET/PUT/DELETE /usuarios/<id>`, `GET /usuarios/<id>/perfil`, `POST /usuarios/<id>/foto_perfil`, equivalentes en `/funcionarios` | `id` en la URL |
| Reportes | `GET/POST /reportes`, `GET/PUT/DELETE /reportes/<id>`, `GET /misreportes?user_id=`, `GET /reportes/geojson` | `usuario_creador_id` en el body, `user_id` en query |
| Estado | `PUT /reportes/<id>/estado` | Cabeceras `User-Role` y `User-Id` |
| Validación | `POST/DELETE /reportes/<id>/reaccion`, `GET/POST /reportes/<id>/comentarios`, `PUT/DELETE /comentarios/<id>` | `actor_id`, `role`, `usuario_id` en el body |
| Institucional | `GET/POST /entidades`, `GET /categorias`, `GET /estados-reporte` | Ninguna |
| Otros | `GET /`, `GET /test-deploy`, `GET /usuarios/<id>/apoyos` y `/denuncias`, equivalentes de funcionarios | Ninguna |
| No HTTP | Puerto 5432 publicado por `docker-compose.yml`; repositorio público en GitHub; consola de depuración de Werkzeug (`debug=True`) | — |

## 7. Límites de confianza

Ver [02-diagrama-superficie-ataque.png](./02-diagrama-superficie-ataque.png) (fuente editable: `02-diagrama-superficie-ataque.dot`).

| ID | Límite | Qué cruza | Control actual |
|---|---|---|---|
| TB1 | Internet → API (HTTP `:5000`) | Todo el JSON, contraseñas incluidas | Ninguno: sin TLS (`cleartextTrafficPermitted="true"`, `BASE_URL = "http://…:5000"`), sin autenticación |
| TB2 | API → PostgreSQL | Consultas SQL | ORM parametrizado; credencial `postgres:postgres`; puerto 5432 publicado al host |
| TB3 | API → AWS S3 | Imágenes | Claves IAM estáticas en `.env` |
| TB4 | App → Gemini / Mapbox | Prompt con dirección y referencia | Clave Gemini embebida en el código del cliente |
| TB5 | Desarrollador / GitHub → servidor | Código y datos | Repos públicos; `deploy.yml` con `appleboy/ssh-action@master` sin fijar |
| TB6 | Dispositivo del usuario | Sesión y credenciales guardadas | `SharedPreferences` en claro, `allowBackup="true"` |

**Lectura clave:** el único límite que el diseño trata como confiable (la app) es justamente el que el atacante controla.
El backend confía en lo que la app dice ser, y esa es la raíz de los riesgos SEG-01 a SEG-04.

## 8. Del checklist heredado a la matriz

| Ítem del checklist (02 §2.1 y 01 §2) | Estado que el checklist registraba | Qué revela el modelado de amenazas | Riesgos |
|---|---|---|---|
| «Existe autenticación» | Login con email y contraseña | El login solo valida en la app; la API nunca vuelve a comprobar identidad | SEG-01, SEG-02, SEG-03 |
| «Credenciales en `.env` sin gestor de secretos» | Riesgo Alto | El `.env` sí está ignorado, pero el **cluster completo de PostgreSQL** (`data/`) y la clave de Gemini están en repos públicos | SEG-05, SEG-11, SEG-12 |
| «HTTPS por verificar» | Pendiente | Confirmado: tráfico en claro por diseño en cliente y servidor | SEG-07 |
| «Cifrado de *Recordarme* por confirmar» | Pendiente | Confirmado: contraseña en claro en `SharedPreferences` | SEG-11 |
| «Permisos IAM mínimos por bucket» | Recomendación | No verificable; URLs públicas directas sugieren lectura pública | SEG-12 |
| «Sin pruebas automatizadas» | Mantenibilidad | No hay evidencia de controles; se crea `tests/security/` | Todos |
| (no estaba) | — | Login CPU-intensivo (`scrypt`, ~16 logins/s, ADR 0004) = vector de denegación de servicio | SEG-06 |
| (no estaba) | — | Imágenes base64 sin límite procesadas en el mismo proceso que la autenticación | SEG-08 |
