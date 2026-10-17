# Registro de cambios — Spike 01 (rama `spike/01-pgbouncer-login`)

**Base:** `main` en el commit del pre-registro (`288837f`, `exp/00-preregistro.md`). El código de la aplicación (`app/`) no se modifica.

## Archivos modificados

| Archivo | Cambio | Razón / criterio del pre-registro |
|---|---|---|
| `config.py` | +6 líneas: si existe la variable `DB_POOL_MODE=null`, SQLAlchemy usa `NullPool`. Sin la variable el comportamiento es idéntico al actual (verificado). | Alcance §5.2: delegar el pooling a PgBouncer sin cambiar el comportamiento por defecto. |

## Archivos nuevos

| Archivo | Para qué sirve |
|---|---|
| `docker-compose.spike.yml` | Override del compose: agrega el servicio `pgbouncer` (`pool_mode=transaction`, `default_pool_size=15`, `max_client_conn=1000`) y apunta el backend a PgBouncer con `DB_POOL_MODE=null`. `docker-compose.yml` queda intacto. |
| `exp/spike-01/correr.ps1` | Ejecuta una corrida de k6 y muestrea CPU/memoria y conexiones a Postgres. |
| `exp/spike-01/condiciones.ps1` | Registra versiones, digests de imágenes, filas por tabla y algoritmo de hash. |
| `exp/spike-01/negativa.js` | Prueba negativa del instrumento. |
| `exp/spike-01/resumir.py` | Calcula medianas, aplica los criterios del pre-registro y genera el borrador del veredicto. |
| `exp/spike-01/01-guia-ejecucion.md` | Pasos de ejecución. |

## No modificado (declaración de no-modificación del pre-registro §6)
`app/` (routes, models, utils), `migrations/`, `docker-compose.yml`, `dockerfile`, el servidor (sigue `python3 app.py`, `debug=True`), el algoritmo de hash y los ADR.

## Desviaciones respecto al pre-registro (declaradas)
1. **Carpeta:** los artefactos del spike van en `exp/spike-01/` (la carpeta que ya existe y donde quedó el pre-registro), no en `experimentos/spike-01/`.
2. **PgBouncer** se configura con variables de entorno en un override de compose, no con archivos en `pgbouncer/`.
3. **Compose:** en lugar de editar `docker-compose.yml`, el servicio nuevo está en `docker-compose.spike.yml`; ambos brazos corren desde la misma rama y se diferencian solo por ese archivo.
4. **Muestreo:** `docker stats` tarda ~1–2 s por llamada, así que el muestreo es cada ~2–3 s y no cada 1 s. Aplica igual a ambos brazos.
5. **Imagen de PgBouncer:** se usa `edoburu/pgbouncer:latest` y se registra el digest exacto con `condiciones.ps1` (reproducible por digest).
6. **URL de k6:** `172.18.0.1` no es alcanzable desde Windows con Docker Desktop (las corridas iniciales fallaron por timeout de conexión y se descartaron). `Pruebas/prueba2.js` y `negativa.js` apuntan a `127.0.0.1:5000` en ambos brazos; el cambio se hizo antes de las corridas válidas. Los números de la línea base anterior (~31 s) son solo referencia: la comparación válida es baseline vs. spike medidos aquí.

## Lo no verificado al preparar la rama
- El compose y los scripts no se ejecutaron en Docker/k6 reales durante la preparación (el entorno de preparación no tenía Docker). Lo que sí se probó: la lógica de `config.py` y el cálculo de `resumir.py` con datos sintéticos.
- La compatibilidad exacta de la imagen de PgBouncer con la autenticación de Postgres 16 se confirma en la primera ejecución (ver guía, sección "Si algo falla").
