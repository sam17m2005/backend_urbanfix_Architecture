# Pre-registro del Spike 01 — PgBouncer frente al agotamiento de conexiones en `/login`

**Proyecto:** UrbanFix — Arquitectura de Software, Módulo 5
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha del pre-registro:** 2026-10-16
**Commit base (`main`):** `c2e2d4cb24a9ca8954011796068bcd2cab3f9631`
**Estado:** PRE-REGISTRO. Este documento se commitea **antes** de abrir la rama `spike/01-pgbouncer-login` y antes de cualquier cambio de implementación.
**Documentos relacionados:** `adrs/0002-aislamiento-persistencia.md` · `docs/04-escenarios-calidad.md` (ESC-07, §5) · `docs/integracion/decision-integracion.md`

> Los umbrales de la sección 4 fueron ratificados por los tres integrantes antes de este commit y no se modifican después. Los datos que solo existen al medir (versiones, volumen de la BD, hash del usuario de prueba) se registran en `resultados/` antes de la primera corrida.

---

## 1. Escenario de calidad evaluado

**ESC-07 — Autenticación concurrente bajo escalado agresivo** (atributo: rendimiento / capacidad de acceso).
Estímulo: rampa k6 de 0 a 800 usuarios virtuales (VUs) contra `POST /login`.
Línea base publicada (5 corridas válidas, laptop de Samuel, Docker local, servidor de desarrollo de Flask): p95 mediano **31,06 s**, tasa de error mediana **11,11 %**, ~30 req/s.

## 2. Decisión arquitectónica candidata

Poner **PgBouncer** (modo `transaction`) entre el backend y PostgreSQL, y delegar el pooling a PgBouncer en lugar del pool de SQLAlchemy de la aplicación. Es solo la parte de infraestructura del ADR 0002; **no** incluye la capa de repositorios ni los pools por dominio.

Premisa del ADR 0002 que se pone a prueba: *la degradación de ESC-07 se debe al agotamiento del pool de 15 conexiones y un pool gestionado por PgBouncer la mitiga*.

## 3. Hipótesis experimental

> **H1.** Con PgBouncer (`default_pool_size = 15`, igual capacidad que el pool actual) y el pool de SQLAlchemy desactivado, bajo la misma rampa de 800 VUs contra `POST /login`, el **p95 mediano de `http_req_duration` baja al menos 30 %** respecto a la línea base medida en las mismas condiciones, y la **tasa de error mediana queda en ≤ 5 %**.

La hipótesis es falsable: si el p95 mejora menos de 30 % o el error supera 5 %, se refuta.

## 4. Criterios de aceptación y refutación

Se usan **medianas de 3 corridas válidas por brazo** (se corren 4 y se descarta la primera por calentamiento).

| Criterio | Aceptación (deben cumplirse **todos**) | Refutación (basta **uno**) |
|---|---|---|
| p95 `http_req_duration` | mediana spike ≤ 0,70 × mediana línea base | mediana spike > 0,70 × mediana línea base |
| Tasa de error (`http_req_failed`) | mediana spike ≤ 5 % | mediana spike > 5 % |
| Respuestas correctas | el 100 % de los `200` corresponden a logins válidos (check de k6) y no aumentan los `5xx` frente a la línea base | los `5xx` aumentan frente a la línea base |

- El 30 % de mejora sigue el ejemplo de la guía del curso; el 5 % es el umbral de referencia ya adoptado en `04-escenarios-calidad.md` (no estaba codificado en el script k6).
- **Resultado inconcluso (no es veredicto):** si falla la validez metodológica (sección 8), se repite el brazo afectado; no se emite veredicto con corridas no equivalentes.

## 5. Alcance — qué se toca

Solo en la rama `spike/01-pgbouncer-login`:

1. `docker-compose.yml`: servicio nuevo `pgbouncer` (imagen `edoburu/pgbouncer`, versión fija que se registra en `cambios.md`), con `pool_mode=transaction`, `default_pool_size=15`, `max_client_conn=1000`. El backend apunta a PgBouncer mediante `DATABASE_URL`.
2. `config.py`: `SQLALCHEMY_ENGINE_OPTIONS` con `NullPool` **solo si** la variable de entorno `DB_POOL_MODE=null` está definida. Sin la variable, el comportamiento es idéntico al actual.
3. Archivos de configuración de PgBouncer nuevos (`pgbouncer/`).
4. Scripts de instrumentación y captura de métricas (carpeta `experimentos/spike-01/`).

## 6. No tocar (declaración de no-modificación)

- `app/routes.py`, `app/models.py`, `app/utils.py`, `migrations/` y el esquema de la BD.
- La capa de repositorios y los pools por dominio del ADR 0002 (no se implementan en este spike).
- El servidor de la aplicación: sigue siendo `python3 app.py` (Werkzeug, `debug=True`). No se introduce Gunicorn.
- El algoritmo y los parámetros de hash de contraseñas.
- `Pruebas/prueba2.js` (el instrumento no cambia entre brazos).
- Cualquier ADR existente y la rama `main`.

## 7. Condiciones de medición

| Aspecto | Valor |
|---|---|
| Herramienta | k6 (versión registrada al medir), `Pruebas/prueba2.js` sin modificar |
| Carga | Rampa 10 s→50, 20 s→300, 20 s→800, 10 s→0 VUs; `sleep(0.1)`; 60 s por corrida |
| Endpoint | `POST /login` en `http://172.18.0.1:5000` |
| Datos | Usuario fijo `test@urbanfix.com`; filas por tabla: se registra al medir |
| Hash del usuario de prueba | prefijo del algoritmo: se registra al medir |
| Máquina | **la misma para ambos brazos:** laptop con Intel Core i5-1035G1 y 16 GB de RAM |
| Entorno | Docker Compose local, Postgres 16-alpine, `debug=True` en ambos brazos |
| Protocolo | Mismo día, misma máquina, conectada a la corriente, sin otras cargas pesadas. Por brazo: `docker compose up -d --build`, esperar estabilización, 4 corridas con 2 min de pausa; la corrida 1 se descarta. Orden: línea base primero, luego spike. |
| Salidas | `k6 run --summary-export=resultados/<brazo>-corrida-N.json` más la salida de consola guardada en texto plano sin reformatear |
| Instrumentación | Cada 1 s durante la corrida: `docker stats` (CPU y memoria de backend y BD) y conteo de conexiones en `pg_stat_activity`. Sirven para atribuir la causa, no para el veredicto. |
| Separación de errores | `5xx`, timeouts/rechazos de conexión (`status 0`) y `4xx` se reportan por separado |

**Prueba negativa del instrumento (antes de medir):** una corrida corta de k6 con credenciales inválidas y otra contra una ruta inexistente, para confirmar que los fallos detectados son del sistema y no del instrumento.

## 8. Qué invalidaría la medición

1. El generador de carga (k6) satura CPU o red antes que el servidor → se revisa el CPU de k6 durante la corrida.
2. Los dos brazos no corrieron en la misma máquina, el mismo día o con la misma configuración de Docker.
3. Otra aplicación pesada en ejecución, o la máquina con batería o throttling térmico.
4. El `contrasena_hash` o el volumen de BD cambian entre brazos.
5. Menos de 3 corridas válidas por brazo.

## 9. Interpretación acordada de antemano

- **Hipótesis respaldada:** se documenta la mejora y la evidencia, y el ADR 3 considera PgBouncer como alternativa viable. Los límites declarados: un solo pool (no se probó aislamiento entre dominios), un solo endpoint, entorno local.
- **Hipótesis refutada:** se documenta que la premisa del ADR 0002 (el pool es la causa) no se sostiene con esta evidencia. Los datos de CPU y conexiones determinan qué recurso se saturó, y el ADR 3 se redacta con esa evidencia (incluyendo el costo de verificación de contraseña por solicitud como causa candidata). No se vuelve a correr el spike hasta que se observe un resultado que se ajuste.

## 10. Supuestos y límites declarados

- Medición local en una laptop; no es el entorno de producción (EC2 `t2.micro` + Neon). No permite concluir nada sobre producción.
- Un solo usuario de prueba; la caché de consulta puede favorecer a ambos brazos por igual.
- No se mide mantenibilidad, costo ni comportamiento de otros endpoints (`/reportes`).
- Con transacciones abiertas durante la petición, el modo `transaction` de PgBouncer puede retener la conexión del servidor hasta el cierre de la transacción; es una razón por la que la hipótesis podría refutarse y se declara aquí antes de medir.

## 11. Declaración de uso de IA

Claude (Anthropic) ayudó a revisar el repositorio, a detectar que el p95 coincide con el `pool_timeout` de 30 s y que el throughput observado (~30 req/s) sugiere un límite de CPU, y a redactar este borrador. Los umbrales, el alcance y la ratificación son decisión del equipo. Las cifras de CPU de verificación de contraseña (~107 ms por `check_password_hash` en el entorno de revisión) son orientativas y deben confirmarse en la máquina de medición.

## 12. Commit previo

```bash
git checkout main && git pull
git add experimentos/spike-01/00-preregistro.md
git commit -m "docs(spike-01): pre-registro de hipótesis, criterios y alcance (antes de implementar)"
git push origin main
# solo después:
git checkout -b spike/01-pgbouncer-login
```
