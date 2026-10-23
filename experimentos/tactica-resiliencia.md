# Experimento E3 — Medición de una táctica: pool de conexiones externo (PgBouncer) bajo carga en `/login`

**Entregable:** E3 · Medición del efecto de una táctica antes y después de aplicarla
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha de la medición:** 2026-10-16 · **Fecha del informe:** 2026-10-22
**Evidencia cruda:** rama `spike/01-pgbouncer-login`, carpeta `exp/spike-01/` (este informe la resume; no la reemplaza). En `main` la carpeta de experimentos se llama `experimentos/`; la rama del spike conserva la ruta `exp/spike-01/` con la que se ejecutó (se creó antes del renombre).

---

## 1. Escenario

**ESC-07 — Autenticación concurrente bajo escalado agresivo** ([04-escenarios-calidad.md](../docs/04-escenarios-calidad.md)). Estímulo: rampa de usuarios virtuales contra `POST /login` hasta 800 VUs. Artefacto: endpoint `/login` del backend Flask y su consulta a PostgreSQL. Medida de referencia: tasa de error ≤ 5 % (umbral adoptado en el documento 04, no codificado en el script k6).

## 2. Táctica evaluada

**Pool de conexiones externo (PgBouncer, modo `transaction`)** entre el backend y PostgreSQL, con el pool interno de SQLAlchemy desactivado (`NullPool`). Es una táctica de gestión de recursos y contención de fallos. Se aplicó **un solo cambio** y con la misma capacidad que el sistema original (15 conexiones), para que cualquier diferencia no se deba a tener más conexiones.

## 3. Hipótesis y criterios (registrados antes de implementar)

Pre-registro: `experimentos/00-preregistro.md` (commit `288837f`, anterior a cualquier cambio).

> **H1.** Con PgBouncer, el p95 mediano de `http_req_duration` baja al menos 30 % frente a la línea base medida en las mismas condiciones, y la tasa de error mediana queda en ≤ 5 %.

Se acepta solo si se cumplen **todos**: (a) p95 spike ≤ 0,70 × p95 línea base; (b) error mediano ≤ 5 %; (c) los 5xx no aumentan. Basta un criterio fallido para refutar.

## 4. Método

- Dos brazos, **línea base** (sin PgBouncer) y **spike** (con PgBouncer), en la misma máquina y el mismo día, línea base primero.
- 4 corridas por brazo, con pausa de al menos 2 minutos y sin reiniciar contenedores entre corridas. **Se descarta la corrida 1** (calentamiento); se comparan las **medianas de las corridas 2 a 4**.
- Prueba negativa del instrumento antes de medir: con credenciales inválidas y una ruta inexistente, k6 debe reportar fallos (`exp/spike-01/resultados/negativa.txt`). La primera tanda de corridas se descartó porque k6 apuntaba a una IP inalcanzable desde Windows (`172.18.0.1`); se corrigió a `127.0.0.1` en ambos brazos antes de las corridas válidas.
- Instrumentación por corrida: CPU y memoria de los contenedores (`docker stats`, muestreo cada ~2–3 s) y conexiones abiertas en Postgres.

## 5. Condiciones de medición

| Aspecto | Valor |
|---|---|
| Máquina | Laptop de Samuel: Intel Core i5-1035G1, 16 GB de RAM, Windows 64 bits (HP 14-cf3xxx según el documento 04). k6 y el sistema compartieron la misma máquina |
| Software | Docker 29.7.2 · k6 v2.2.0 · Postgres 16-alpine (`sha256:cf78e766…`) · PgBouncer 1.26.0 (`edoburu/pgbouncer`, `sha256:9c789458…`) |
| Configuración — línea base | `docker compose up -d --build`. Backend → Postgres directo, pool de SQLAlchemy de 15 conexiones (5 + 10 de desborde) |
| Configuración — spike | `docker compose -f docker-compose.yml -f docker-compose.spike.yml up -d --build`. Backend → PgBouncer (`pool_mode=transaction`, `default_pool_size=15`, `max_client_conn=1000`) → Postgres; `DB_POOL_MODE=null` (NullPool) |
| Servidor de la aplicación | `python3 app.py` (servidor de desarrollo de Werkzeug, `debug=True`) en ambos brazos |
| Semilla / datos | No hay semilla aleatoria: credenciales fijas de un usuario de prueba (`test@urbanfix.com`, hash `scrypt:32768:8:1`). Base con 1 usuario, 10 reportes y 0 funcionarios (iguales en ambos brazos) |
| Carga | Rampa de 10 s a 50 VUs, 20 s a 300, 20 s a 800 y 10 s a 0; `sleep(0.1)` entre iteraciones; script `Pruebas/prueba2.js` |
| Duración | 60 s de carga por corrida (más el cierre ordenado de k6) |
| Corridas | 4 por brazo; válidas: 3 (corridas 2 a 4) |
| Commit | Corridas válidas de ambos brazos con el código del commit `9df270c`. El registro de condiciones de la línea base muestra `af01216`, anterior al commit del cambio de URL de k6; solo la corrida 1 (descartada) corrió antes de ese commit |
| Fecha y hora | 2026-10-16, entre las 19:14 y las 19:43 (hora local) |

## 6. Resultados

### 6.1 Corrida por corrida

| Brazo | Corrida | p95 (s) | Promedio (s) | Error | Peticiones | Req/s | HTTP 200 | HTTP 500 | CPU máx. backend (%) |
|---|---|---|---|---|---|---|---|---|---|
| Línea base | 1 (descartada) | 41,31 | 17,74 | 19,87 % | 1.339 | 15,00 | 1.073 | 266 | 1.078 |
| Línea base | 2 | 40,13 | 18,27 | 17,94 % | 1.494 | 16,87 | 1.226 | 268 | 970 |
| Línea base | 3 | 41,44 | 17,10 | 15,24 % | 1.352 | 15,24 | 1.146 | 206 | 969 |
| Línea base | 4 | 43,70 | 18,40 | 18,41 % | 1.380 | 15,41 | 1.126 | 254 | 1.040 |
| Spike | 1 (descartada) | 43,84 | 22,46 | 0,00 % | 844 | 9,38 | 844 | 0 | 1.169 |
| Spike | 2 | 40,80 | 19,98 | 0,00 % | 1.166 | 12,96 | 1.166 | 0 | 978 |
| Spike | 3 | 40,84 | 19,74 | 0,00 % | 1.171 | 13,01 | 1.171 | 0 | 1.141 |
| Spike | 4 | 40,65 | 19,72 | 0,00 % | 1.161 | 12,90 | 1.161 | 0 | 1.117 |

El CPU se lee de `docker stats`, donde 100 % equivale a un núcleo.

### 6.2 Medianas de las corridas válidas (2 a 4)

| Métrica | Línea base | Spike | Variación |
|---|---|---|---|
| p95 (s) | 41,44 | 40,80 | −1,5 % |
| Promedio (s) | 18,27 | 19,74 | +8,0 % |
| Tasa de error | 17,94 % | 0,00 % | −17,94 pp |
| Respuestas HTTP 200 | 1.146 | 1.166 | +1,7 % |
| Respuestas HTTP 500 | 254 | 0 | −254 |
| Peticiones totales | 1.380 | 1.166 | −15,5 % |
| Throughput (req/s) | 15,41 | 12,96 | −15,9 % |
| CPU máxima del backend (%) | ≈ 970 | ≈ 1.117 | +15,2 % |
| Conexiones máximas a Postgres | 16 | 16 | 0 |

**Códigos de respuesta.** Todos los fallos de la línea base fueron `HTTP 500`; no hubo 4xx ni peticiones sin respuesta. En el spike todas las respuestas fueron `HTTP 200`. La causa interna de los 500 no se verificó en los logs del backend.

### 6.3 Criterios pre-registrados

| Criterio | Resultado | Cumple |
|---|---|---|
| p95 spike ≤ 0,70 × p95 línea base | 40,80 s frente a 41,44 s (mejora de 1,5 %) | **No** |
| Error mediano ≤ 5 % | 0,00 % | Sí |
| Los 5xx no aumentan | 0 frente a 254 | Sí |

## 7. Conclusión

**Hipótesis refutada** según la regla pre-registrada: el p95 casi no cambió. Lo que sí se observa:

- **Efecto sobre los fallos:** la táctica eliminó los errores (254 respuestas 500 por corrida a 0). Es una mejora de resiliencia en este escenario: las peticiones pasaron de fallar a esperar y terminar.
- **Sin efecto sobre la capacidad:** los logins exitosos por corrida casi no cambiaron (mediana 1.146 frente a 1.166) y el p95 se mantuvo cerca de 41 s. El usuario sigue esperando lo mismo.
- **No se afirma que la táctica mejoró el rendimiento.** El throughput de peticiones totales bajó porque antes las peticiones fallidas terminaban rápido y los usuarios virtuales reintentaban.
- **Recurso saturado:** la CPU del backend estuvo saturada en ambos brazos, mientras las conexiones a Postgres llegaron al mismo tope (16). Cada login calcula un hash `scrypt`, costoso en CPU. Esto es una **sospecha coherente con los datos, no una causa demostrada**; probarla requiere otro experimento.

## 8. Validez y límites

- Medición local en un laptop, con k6 corriendo en la misma máquina que el sistema (su CPU no se midió).
- Solo se probó el servidor de desarrollo de Werkzeug. El flujo de despliegue del repo (`deploy.yml`) indica que producción usa Gunicorn en EC2; **eso no se midió** y los resultados no se transfieren a producción.
- Un solo usuario de prueba, un solo endpoint, 3 corridas válidas por brazo (el mínimo del protocolo).
- La línea base se midió antes que el spike, sin alternar el orden: no se descarta un efecto térmico o de orden.
- El throughput de esta sesión (~15 req/s) es la mitad del de la medición previa del equipo (~30 req/s): solo es válida la comparación entre brazos medidos el mismo día.
- No se evaluaron costo, mantenibilidad ni el efecto sobre otros endpoints.

## 9. Trazabilidad

| Elemento | Ubicación |
|---|---|
| Pre-registro | `experimentos/00-preregistro.md` (en `main`, commit `288837f`) |
| Rama, cambios y scripts | rama `spike/01-pgbouncer-login`: `config.py`, `docker-compose.spike.yml`, `exp/spike-01/cambios.md`, `correr.ps1`, `condiciones.ps1`, `resumir.py` |
| Resultados crudos | rama `spike/01-pgbouncer-login`: `exp/spike-01/resultados/` (JSON y CSV de k6, `docker-stats`, conexiones, condiciones por brazo, `negativa.txt`) |
| Veredicto y decisión | rama `spike/01-pgbouncer-login`: `exp/spike-01/veredicto.md` |
| Decisión que usa este experimento | `adrs/0003-mecanismo-integracion.md` |

**Uso de IA:** Claude (Anthropic) ayudó a diseñar el protocolo, procesar los resultados y redactar este informe. Las mediciones las ejecutó el equipo; el veredicto sigue la regla pre-registrada.
