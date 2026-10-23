# Guía de ejecución — experimento de crecimiento (PowerShell, en la laptop de Samuel)

**Antes de empezar:** laptop **conectada a la corriente**, plan de energía en alto rendimiento, **OneDrive en pausa**, sin otras aplicaciones pesadas, Docker Desktop abierto y k6 instalado. Cada corrida dura ~11 minutos, así que reserva ~1 hora en total y no uses el equipo durante las corridas.

## 0. Traer el código (rama `main`, sin cambios locales)
```powershell
git checkout main
git pull
git status
```
`git status` no debe mostrar cambios pendientes. Debe existir la carpeta `experimentos\crecimiento-S11\` con `00-plan.md` (si no, avisa).

## 1. Levantar el sistema SIN PgBouncer (compose original)
```powershell
docker compose down --remove-orphans
docker compose up -d --build
docker compose ps
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/login -ContentType 'application/json' -Body '{"email":"test@urbanfix.com","contrasena":"PasswordSeguro123!"}'
```
Debe responder "Inicio de sesión exitoso". Si no, para y avisa.

## 2. Registrar condiciones y pruebas del instrumento (~5 min)
```powershell
.\experimentos\crecimiento-S11\condiciones.ps1
k6 run -e HUMO=1 experimentos\crecimiento-S11\crecimiento.js
k6 run -e HUMO=1 -e CLAVE=mala experimentos\crecimiento-S11\crecimiento.js 2>&1 | Tee-Object experimentos\crecimiento-S11\resultados\negativa.txt
```
- **Prueba de humo:** los dos checks deben dar **100 %** de éxito.
- **Prueba negativa:** los checks deben dar **0 %** de éxito, y `http_req_duration` debe tener valores mayores que 0. Si sale casi 100 % de éxito con clave mala, **para y avisa**.

## 3. Las 4 corridas (sin reiniciar contenedores)
```powershell
.\experimentos\crecimiento-S11\correr.ps1 -Corrida 1
# esperar 2 minutos
.\experimentos\crecimiento-S11\correr.ps1 -Corrida 2
# esperar 2 minutos
.\experimentos\crecimiento-S11\correr.ps1 -Corrida 3
# esperar 2 minutos
.\experimentos\crecimiento-S11\correr.ps1 -Corrida 4
```
**Qué debe verse:** al terminar cada corrida, k6 imprime el resumen sin errores `connectex`, y en `experimentos\crecimiento-S11\resultados\` aparecen `corrida-N-filtrado.csv`, `corrida-N-muestreo.csv`, `corrida-N-resumen.json` y `corrida-N-consola.txt`. Es normal que en los escalones altos haya errores y latencias de decenas de segundos: es lo que se está midiendo.

**Si una corrida sale rara** (el equipo se durmió, Docker falló, aparece `connectex`): no la borres; anota qué pasó y repítela como corrida adicional (número 5).

## 4. Resumen y subida
```powershell
python experimentos\crecimiento-S11\resumir.py
git add experimentos\crecimiento-S11
git commit -m "exp(crecimiento): resultados crudos y resumen"
git push origin main
```
