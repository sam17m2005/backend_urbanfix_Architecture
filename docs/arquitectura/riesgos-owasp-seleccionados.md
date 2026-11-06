# Riesgos de seguridad seleccionados — OWASP Top 10:2025 — Backend UrbanFix

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha:** 2026-11-06
**Commit de referencia (`main`):** `7d59b58`
**Lista usada:** [OWASP Top 10:2025](https://owasp.org/Top10/2025/), la edición pública más reciente.
**Documentos relacionados:** [plan-observabilidad.md](./plan-observabilidad.md) · [matriz-fallos.md](./matriz-fallos.md) · [matriz-resiliencia.md](./matriz-resiliencia.md) · [07-c4-componentes.md](../07-c4-componentes.md) · [crecimiento.md](../../experimentos/crecimiento.md)

---

## 1. Qué se selecciona y con qué criterio

Se eligen **4 de las 10 categorías**. Cada una cumple cuatro condiciones:

1. Tiene **evidencia reproducida** sobre el código de `main` (ver sección 3), no solo una sospecha.
2. Se ubica en un **elemento concreto del C4** (ID de la [tabla de trazado](../07-c4-componentes.md)), con archivo y línea.
3. Se relaciona con un **escenario del Módulo 6** o con un experimento del proyecto.
4. Su control es **arquitectónico y verificable**: se puede comprobar con una prueba o con una regla en CI.

| # | Categoría OWASP:2025 | Dónde (C4) | Evidencia | Control propuesto | Relación |
|---|---|---|---|---|---|
| 1 | **A01 · Broken Access Control** | C4-3-01, C4-3-02, C4-3-04 (API Backend, C4-2-02) | Comprobada: 5 rutas sensibles responden sin credenciales | Token firmado y autorización por rol y por dueño del recurso | F-13; riesgo A07 |
| 2 | **A07 · Authentication Failures** | C4-3-01 (`login()`) | Comprobada: enumeración de cuentas, sin límite de intentos, sin token | Respuesta única, control de admisión y token con expiración | R-04 (matriz de resiliencia); E3 (≈ 16 logins/s) |
| 3 | **A09 · Security Logging & Alerting Failures** | Toda la API Backend | Inspección y prueba de concepto: 16 `print`, sin `logging` ni alertas | Plan de observabilidad: eventos de seguridad y alerta A-08 | [plan-observabilidad.md](./plan-observabilidad.md) |
| 4 | **A02 · Security Misconfiguration** | C4-2-02 (`app.py`, `dockerfile`), repositorio y CI | Comprobada y por inspección | Servidor de producción, quitar `/test-deploy` y `data/` del repositorio | F-13 |

Todos los controles están **propuestos**: ninguno está implementado en `main`.

## 2. Cómo se lee cada riesgo

Para evitar el "hay riesgo de X en el sistema", cada riesgo se escribe como **endpoint → elemento del C4 → mecanismo → control**: qué ruta concreta, en qué componente, con qué comportamiento verificado y qué control lo corrige.

## 3. Evidencia reproducida

`seguridad/comprobar_riesgos.py` ejecuta el **código real de `main`** con SQLite temporal y el cliente de pruebas de Flask. No usa red, no toca bases ni buckets reales y no corrige nada: solo comprueba el comportamiento actual. Resultado completo en `seguridad/evidencia/comprobacion-preparacion.txt`.

| OWASP | Prueba | Esperado si fuera seguro | Obtenido |
|---|---|---|---|
| A07 | `POST /login` con correo inexistente vs. correo existente y clave mala | Mismo código y mensaje | `404` "La cuenta no existe" vs. `401` "Credenciales incorrectas" |
| A07 | 30 intentos fallidos seguidos contra la misma cuenta | Bloqueo o `429` antes del intento 30 | Los 30 devolvieron `401` (2,8 s) |
| A07 | Respuesta de un login correcto | Un token firmado con expiración | `200` con `message`, `role` y `user_data`: sin token ni sesión |
| A01 | `GET /usuarios/2` sin credenciales | `401`/`403` | `200`, expone `email` y `telefono` de otra persona |
| A01 | `GET /misreportes?user_id=1` sin credenciales | `401`/`403` | `200`: el id lo elige quien llama |
| A01 | `PUT /reportes/1/estado` con las cabeceras inventadas `User-Role: funcionario` | `401`/`403` | `200`, el estado cambió a `Resuelto` |
| A01 | `POST /funcionarios` sin credenciales | `401`/`403` | `201`: se creó una cuenta con rol de funcionario |
| A01 | `DELETE /usuarios/2` sin credenciales | `401`/`403` | `200`; después, `GET /usuarios/2` da `404`: la cuenta ya no existe |
| A02 | `GET /test-deploy` | `404` | `200` "Funciona pe causa v2" |
| A02 | `app.py` arranca el servidor | `debug=False` | `debug=True` con `host='0.0.0.0'` |

**Observación para A09:** durante estas comprobaciones, el borrado de una cuenta, la creación de un funcionario y los 30 intentos fallidos no produjeron ninguna salida de la aplicación.

## 4. Los cuatro riesgos

### 4.1 A01 · Broken Access Control

**Dónde.** C4-3-01 (`delete_usuario`, `update_usuario`, `get_usuario`, `routes.py:621-663`, `77-80`), C4-3-02 (`get_mis_reportes`, `:429`; `update_reporte_estado`, `:721`) y C4-3-04 (`crear_funcionario`, `:587`; `delete_funcionario`, `:666`).

**Causa de fondo.** El login no emite ninguna credencial (`routes.py:41-74`), así que el servidor no tiene cómo saber quién llama. Las rutas toman la identidad de datos que controla el cliente: las cabeceras `User-Role` y `User-Id` (`routes.py:730-731`, con el comentario "JWT token si fuera real") o el parámetro `?user_id=` (`:437`).

**Amenaza concreta.** Quien conozca la URL puede ejecutar `DELETE /usuarios/<id>` con ids consecutivos y borrar todas las cuentas, o enviar `PUT /reportes/<id>/estado` con `User-Role: funcionario` para marcar como *Resuelto* el reporte de otra persona. Esto afecta la integridad del trámite del ciudadano y expone datos personales (correo y teléfono) a cualquiera, lo que además tensiona la Ley 1581 de 2012.

**Control (arquitectónico).** Autenticación y autorización en la frontera del contenedor API Backend:
- `/login` emite un token firmado con expiración.
- Un `before_request` del Blueprint `main` lo verifica y deja la identidad y el rol en el contexto de la petición.
- Cada ruta declara el rol que exige, y las rutas de un recurso comprueban que el id del token coincide con el del recurso.
- Se eliminan las cabeceras `User-Role` y `User-Id` y el parámetro `user_id` como fuente de identidad.
- Una lista blanca explícita define las rutas públicas (`/login`, el registro, `/health`, los catálogos).

**Cómo se verificaría.** Pruebas que llamen cada ruta sin token (esperan `401`) y con el token de otro usuario (esperan `403`). Y una **fitness function propuesta (FF-03)**: toda función de ruta fuera de la lista blanca debe llevar el decorador de autenticación, con análisis estático igual que FF-01 y FF-02 y su prueba negativa en CI.

**Costo y reversibilidad.** Cambia el contrato con el cliente Android, que debe enviar el token: es un cambio coordinado entre dos repositorios. No se estimó el esfuerzo.

**Observabilidad.** Eventos `acceso_denegado` y `recurso_eliminado`, y la alerta A-08 del plan.

### 4.2 A07 · Authentication Failures

**Dónde.** C4-3-01, `login()` (`routes.py:41-74`).

**Evidencia.** Dos respuestas distintas según exista o no la cuenta (`:53-54` frente a `:63-64` y `:73-74`), ningún límite de intentos y ningún token (sección 3).

**Relación con lo medido.** Un login tarda ≈ 0,2 s con un solo usuario (la causa sospechada, no demostrada, es el hash `scrypt:32768:8:1`), y el experimento de crecimiento midió una capacidad de ≈ 16 logins por segundo. El mismo mecanismo que agota la capacidad con tráfico legítimo permite agotarla con tráfico malicioso. Esa lectura es una **inferencia desde la capacidad medida**: no se probó con un atacante.

**Amenaza concreta.** Con la enumeración de cuentas, un atacante confirma qué correos existen y prueba contraseñas sin ser bloqueado; y con ≈ 16 intentos por segundo puede degradar el inicio de sesión de todos, porque la CPU es compartida por el único proceso (F-02).

**Control.**
1. Una sola respuesta, con el mismo código y mensaje, para cuenta inexistente y clave incorrecta.
2. **Control de admisión** por origen y por cuenta, con `429` y `Retry-After`. Es el mismo control **R-04** de la [matriz de resiliencia](./matriz-resiliencia.md): un solo mecanismo atiende un riesgo de seguridad y otro de disponibilidad.
3. Token con expiración (ver 4.1).

No se cambia el algoritmo de hash: `scrypt` es una buena práctica y su costo es la razón de ser del límite, no un defecto.

**Cómo se verificaría.** Una prueba con N intentos que espere `429` y el mismo mensaje en ambos casos, y la medición con el protocolo del E3 con y sin el límite, como ya define R-04.

### 4.3 A09 · Security Logging & Alerting Failures

**Dónde.** Toda la API Backend (C4-2-02 y los módulos C4-3-01 a C4-3-06).

**Evidencia.** Por inspección: 16 `print(f"Error ...")` en `routes.py` (líneas 150, 163, 245, 279, 302, 323, 344, 365, 475, 506, 517, 752, 778, 810, 858 y 913) y 2 en `utils.py` (40 y 73). No hay ninguna importación de `logging`, ni alertas. Los eventos de seguridad —login fallido, borrado de cuentas, creación de funcionarios— no dejan rastro (sección 3).

**Amenaza concreta.** Los ataques de 4.1 y 4.2 ocurrirían sin que nadie los vea. La edición 2025 de OWASP puso el énfasis en las alertas: registrar sin alertar aporta muy poco para detectar un incidente.

**Control.** El [plan de observabilidad](./plan-observabilidad.md): logs estructurados con identificador de petición, eventos de seguridad (`login_fallido`, `acceso_denegado`, `recurso_eliminado`), reemplazo de los `print` y la alerta **A-08**. La prueba de concepto ya implementa los logs estructurados y la correlación con las trazas; los eventos de seguridad y las alertas siguen propuestos.

**Cómo se verificaría.** Provocar cada ataque de 4.1 y 4.2 y comprobar que genera su evento; y una **fitness function propuesta (FF-04)**: ningún `print(` en `app/`.

### 4.4 A02 · Security Misconfiguration

**Dónde.** C4-2-02: `app.py:6`, `dockerfile` (`CMD ["python3", "app.py"]`) y `routes.py:861`; repositorio y flujo de CI.

**Evidencia.**
- *Comprobada:* `/test-deploy` responde `200`; `app.py` arranca con `debug=True` y `host='0.0.0.0'`, y el Dockerfile ejecuta ese archivo.
- *Por inspección:* la carpeta `data/` contiene 1.314 archivos de un clúster de PostgreSQL y está versionada en un repositorio público; `.gitignore` no la excluye. **Su contenido no se verificó.**
- *Por inspección:* credenciales `postgres/postgres` en `docker-compose.yml` (de desarrollo), y `deploy.yml` usa `appleboy/ssh-action@master` (referencia mutable) y `pip install --upgrade` sin versiones fijas, lo que se relaciona con A03:2025 *Software Supply Chain Failures*.

**Amenaza concreta.** El servidor de desarrollo expone información interna del servidor ante una excepción (F-13), y su depurador interactivo no debe estar accesible en un servicio expuesto. Si `data/` contiene datos reales, correos, teléfonos y hashes de contraseña quedan al alcance de quien clone el repositorio, y permanecen en el historial aunque se borre la carpeta.

**Control.**
- Servir con Gunicorn y controlar `debug` con una variable de entorno desactivada por defecto.
- Eliminar `/test-deploy` (`/health` cumple esa función).
- Sacar `data/` del control de versiones (`git rm -r --cached data/` y `.gitignore`). Esto **no borra el historial**: si hubo datos reales, hay que tratarlo como un incidente (revisar qué contiene y rotar lo que corresponda).
- Fijar la acción de CI por el SHA de un commit y fijar las versiones en el despliegue.

**Cómo se verificaría.** Una **fitness function propuesta (FF-05)**: `app.py` sin `debug=True`, sin rutas de prueba y con `data/` ignorada; el CI falla si reaparecen.

**Prioridad.** `data/` merece atención inmediata, antes que el resto de este documento.

## 5. Revisadas y no seleccionadas

| Categoría | Por qué no se selecciona |
|---|---|
| A05 · Injection | No se encontró SQL crudo en `app/` (no hay `text(` ni `execute(`): todo pasa por el ORM. Riesgo bajo |
| A03 · Software Supply Chain Failures | Se menciona dentro de A02 (acción de CI y dependencias sin fijar); no tiene evidencia propia más allá de eso |
| A10 · Mishandling of Exceptional Conditions | Muy relacionada con los falsos verdes F-05 y F-07 y con los `try/except` con `print`, pero ya se trata en las matrices de fallos y de resiliencia (R-07) |
| A04 · Cryptographic Failures | El hash `scrypt` es adecuado; el tráfico HTTP plano ya está registrado en el doc 03 |
| A06 · Insecure Design | Cubierta en parte por los controles de A01 y A07 |
| A08 · Software or Data Integrity Failures | Sin evidencia propia |

## 6. Limitaciones

- Las comprobaciones se hicieron en un entorno aislado (SQLite, cliente de pruebas): confirman el camino que sigue el código, no el comportamiento contra los servicios reales.
- Las amenazas descritas son escenarios razonados a partir de lo comprobado; **no se probaron con un atacante**.
- No se estimó el esfuerzo ni el costo de los controles.
- El contenido de `data/` no se inspeccionó.
- **No ejecutar `comprobar_riesgos.py` contra un sistema real:** sus pruebas borran y crean cuentas. Está pensado solo para el entorno aislado que él mismo crea.

## 7. Trazabilidad

| Elemento | Ubicación |
|---|---|
| Comprobaciones | `seguridad/comprobar_riesgos.py` · `seguridad/evidencia/comprobacion-preparacion.txt` |
| Elementos del C4 | [07-c4-componentes.md](../07-c4-componentes.md), §4 |
| Código señalado | `app/routes.py` · `app/utils.py` · `app.py` · `dockerfile` · `docker-compose.yml` · `.github/workflows/deploy.yml` |
| Observabilidad relacionada | [plan-observabilidad.md](./plan-observabilidad.md) (A-08, eventos de seguridad) |
| Control compartido con resiliencia | R-04 en [matriz-resiliencia.md](./matriz-resiliencia.md) |

**Relación con la matriz de riesgos de seguridad.** Estas cuatro filas deben incorporarse o referenciarse en esa matriz para no duplicar el trabajo.

**Uso de IA:** Claude (Anthropic) ayudó a revisar el código, a escribir y ejecutar las comprobaciones y a redactar este documento. La selección final de riesgos y la adopción de los controles son del equipo y están por ratificar.
