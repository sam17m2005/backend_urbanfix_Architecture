# Guía de ejecución — Spike 01 (laptop de Samuel, PowerShell, desde la raíz del repo)

Reglas durante todo el proceso: laptop **conectada a la corriente**, plan de energía en alto rendimiento, sin otras aplicaciones pesadas abiertas, mismo día para los dos brazos. Todo el spike se hace en la rama `spike/01-pgbouncer-login`.

## 0. Preparar la rama (una vez)
```powershell
git fetch origin
git checkout -b spike/01-pgbouncer-login origin/main
# copia aquí los archivos del zip (config.py, docker-compose.spike.yml y exp/spike-01/*)
git add config.py docker-compose.spike.yml exp/spike-01
git commit -m "spike(01): override de compose con PgBouncer, NullPool opcional y scripts de medicion"
```

## 1. Prueba negativa del instrumento (~5 min)
```powershell
docker compose down --remove-orphans
docker compose up -d --build
k6 run exp\spike-01\negativa.js
```
**Esperado:** el check `Status 200` falla (≈100 % de fallos). Guarda la salida en `exp\spike-01\resultados\negativa.txt`. Si reporta 100 % de éxito, avísame antes de seguir.

## 2. Brazo LÍNEA BASE (compose original)
```powershell
docker compose down --remove-orphans
docker compose up -d --build
Invoke-RestMethod -Method Post -Uri http://localhost:5000/login -ContentType 'application/json' -Body '{"email":"test@urbanfix.com","contrasena":"PasswordSeguro123!"}'
.\exp\spike-01\condiciones.ps1 -Brazo baseline
.\exp\spike-01\correr.ps1 -Brazo baseline -Corrida 1
# espera 2 min y repite con -Corrida 2, 3 y 4
```
El `Invoke-RestMethod` debe devolver "Inicio de sesión exitoso". La corrida 1 se descarta luego (calentamiento), pero **se guarda**.

## 3. Brazo SPIKE (con PgBouncer)
```powershell
docker compose down --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.spike.yml up -d --build
docker logs urbanfixpgbouncer --tail 20      # no debe haber errores de autenticacion
Invoke-RestMethod -Method Post -Uri http://localhost:5000/login -ContentType 'application/json' -Body '{"email":"test@urbanfix.com","contrasena":"PasswordSeguro123!"}'
.\exp\spike-01\condiciones.ps1 -Brazo spike
.\exp\spike-01\correr.ps1 -Brazo spike -Corrida 1
# espera 2 min y repite con -Corrida 2, 3 y 4
```

## 4. Resultados y veredicto
```powershell
python exp\spike-01\resumir.py
copy exp\spike-01\resultados\veredicto-borrador.md exp\spike-01\veredicto.md
# edita veredicto.md: completa las lineas "COMPLETAR"
git add exp\spike-01
git commit -m "exp(spike-01): resultados crudos, resumen y veredicto"
git push origin spike/01-pgbouncer-login
```
No reformatees ni edites los archivos crudos de `resultados/`.

## Si algo falla
- **El backend no conecta a PgBouncer / error de autenticación:** en `docker-compose.spike.yml` cambia `AUTH_TYPE: scram-sha-256` por `md5`, reinicia el brazo y anótalo en `cambios.md`.
- **k6 no llega al backend:** la IP `172.18.0.1` de `prueba2.js` es el gateway de la red de Docker. Verifícala con `docker network inspect` y avísame antes de cambiar nada (el script no debe modificarse entre brazos).
- **Una corrida salió rara (error de Docker, la máquina se durmió, etc.):** no la borres; anota qué pasó y repítela como una corrida adicional.
