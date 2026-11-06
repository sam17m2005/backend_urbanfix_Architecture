# Hallazgos de la revisión de repositorios (2026-11-06)

> Este archivo **no reproduce** secretos ni datos personales; solo indica dónde están y cuántos son.

## Backend (`backend_urbanfix_Architecture`, commit `7d59b58`)

| Revisión | Resultado | Comando |
|---|---|---|
| Claves AWS o de Neon en el historial (111 commits, todas las ramas) | No se encontraron; el README solo contiene marcadores `[Tu …]` | `git log --all -p \| grep -E "AKIA[0-9A-Z]{16}\|PGPASSWORD="` |
| Archivos `.env` versionados alguna vez | Ninguno | `git log --all --diff-filter=A --name-only \| grep -i env` |
| Carpeta `data/` (cluster PostgreSQL) | **Versionada**: 1.314 archivos desde el commit `92f46ea` (2026-08-26) | `git ls-files data \| wc -l` |
| Hashes de contraseña dentro de `data/` | **20 hashes `scrypt:32768:8:1` distintos** | `grep -rhaoE 'scrypt:32768:8:1\$[A-Za-z0-9]{16}\$[0-9a-f]{128}' data \| sort -u \| wc -l` |
| Correos dentro de `data/` | **Más de diez** con dominios de proveedores personales y de `utadeo.edu.co` (no se listan aquí) | `grep -rhaoE '[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}' data/base \| sort -u` |
| `docker-compose.yml` | `POSTGRES_PASSWORD: postgres`, `ports: "5432:5432"` | lectura directa |
| `data/pg_hba.conf` / `postgresql.conf` | `trust` en conexiones locales; `listen_addresses = '*'` | lectura directa |
| `app.py` | `debug=True` con `host='0.0.0.0'` | lectura directa |

## Cliente (`UrbanFix_Architecture`, commit `2f5b706`)

| Revisión | Resultado | Ubicación |
|---|---|---|
| Clave de Google (Gemini) en el código | **Presente** en un repositorio público (prefijo `AIza…`, valor omitido) | `app/src/main/java/com/example/urbanfix/services/AIService.kt:10` |
| Token de Mapbox | Presente (prefijo `pk.`, token público por diseño; debe restringirse) | `app/src/main/res/values/mapbox_access_token.xml` |
| Tráfico en claro | `cleartextTrafficPermitted="true"`; `BASE_URL = "http://…:5000"` | `res/xml/network_security_config.xml`, `network/RetrofitInstance.kt` |
| Contraseña en el dispositivo | Guardada en claro (`saved_password`) cuando se marca «Recordarme» | `data/UserPreferencesManager.kt`, `screens/LoginScreen.kt:61` |
| Respaldo de datos de la app | `allowBackup="true"` | `AndroidManifest.xml:14` |
| Identidad enviada por el cliente | Cabeceras `User-Role` y `User-Id` construidas por la app | `network/ApiService.kt:72`, `:151-152` |
