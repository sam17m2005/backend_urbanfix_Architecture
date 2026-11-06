# Observabilidad de UrbanFix — prueba de concepto (Módulo 7)

Instrumentación inactiva por defecto: **sin `OTEL_ENABLED=1` la aplicación se comporta igual que antes.** El plan completo está en [`docs/arquitectura/plan-observabilidad.md`](../docs/arquitectura/plan-observabilidad.md).

## Qué contiene
| Archivo | Para qué sirve |
|---|---|
| `app/observabilidad.py` | Logs JSON, trazas y métricas de OpenTelemetry, y `GET /health` |
| `app/__init__.py` (+4 líneas) y `app/utils.py` (+1 `import`, 2 líneas cambiadas) | Activan el módulo y reemplazan el `print` de fallo de S3 por un evento; el comportamiento no cambia |
| `requirements-observabilidad.txt` | Dependencias de OpenTelemetry, separadas de `requirements.txt` |
| `dockerfile.observabilidad`, `docker-compose.observabilidad.yml` | Imagen con las dependencias y Collector (superpuestos al compose original, que queda intacto) |
| `observabilidad/otel-collector-config.yaml` | Configuración del Collector (solo componentes del núcleo) |
| `observabilidad/probar_local.py` | Prueba sin Docker que reproduce F-03, F-05 y F-07 |
| `observabilidad/evidencia/` | Salidas reales de las pruebas (entorno de preparación) |

## Cómo ejecutarlo

### A) Prueba rápida, sin Docker (~10 s)
```powershell
pip install -r requirements.txt -r requirements-observabilidad.txt
python observabilidad/probar_local.py
```
Usa SQLite temporal y un puerto cerrado como S3. No toca ninguna base ni bucket reales.

### B) Con Docker Compose y Collector
```powershell
docker compose down --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.observabilidad.yml up -d --build
curl http://127.0.0.1:5000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/login -ContentType 'application/json' -Body '{"email":"test@urbanfix.com","contrasena":"PasswordSeguro123!"}'
docker logs urbanfixbackend --tail 20
docker logs urbanfix-otel-collector --tail 60
```
Para volver al sistema sin observabilidad: `docker compose down --remove-orphans` y `docker compose up -d --build`.

## Qué debe verse
- `docker logs urbanfixbackend`: una línea JSON por petición (`"evento":"http_request"`) con `trace_id`, `endpoint`, `status` y `duration_ms`.
- `docker logs urbanfix-otel-collector`: spans `POST /login` con hijos de SQLAlchemy, y las métricas `http.server.request.duration`, `urbanfix.db.pool.connections` y `urbanfix.s3.upload.failures`.
- `/health` responde `200` con la BD arriba y `503` con ella detenida (`docker compose stop db`).

## Capturas del equipo (evidencia propia, tomadas el 2026-11-06)
1. Una línea de log de `/login` y la traza con el mismo `trace_id` en el log del Collector.
2. `/health` en `200` y luego en `503` con la BD detenida.
3. El evento `s3_upload_failed` al provocar un fallo de S3 (credencial inválida en un bucket de prueba).
4. La métrica `urbanfix.db.pool.connections` durante una corrida de carga.

## Lo que NO está verificado
- Subidas reales a S3 (las pruebas usan un S3 inalcanzable a propósito) y el comportamiento bajo carga sostenida.
- La imagen Docker, el Compose, el Collector y PostgreSQL real **sí** los ejecutó el equipo: ver `observabilidad/evidencia/`.
- El costo de la instrumentación: **no se midió el efecto sobre la capacidad de `/login`** (≈ 16 logins/s). Debe medirse con el protocolo del experimento de crecimiento antes de activarla en producción.
- La etiqueta `otel/opentelemetry-collector:0.164.0` en Docker Hub: es la versión del binario con el que se validó la configuración, pero no se pudo consultar el registro. Registre el *digest* tras el primer `docker pull`.
