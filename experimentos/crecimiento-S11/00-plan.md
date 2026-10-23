# Plan del experimento de crecimiento — `POST /login` (pre-registro)

**Entregable:** E3 · camino 1 (repetir la medición anterior con carga aumentada y registrar dónde y cómo se degrada el sistema)
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha del plan:** 2026-10-23
**Estado:** PLAN. Este documento se commitea **antes** de la primera corrida y sus criterios no se cambian después.
**Relacionados:** [04-escenarios-calidad.md](../../docs/04-escenarios-calidad.md) (ESC-07) · [ADR 0003](../../adrs/0003-mecanismo-integracion.md)

> Los umbrales de la sección 4 y las predicciones de la sección 3 deben ser ratificados por los tres integrantes antes del commit.

---

## 1. Objetivo y escenario

Medir **dónde y cómo se degrada** el sistema al crecer el número de usuarios simultáneos en `POST /login` (ESC-07). La medición anterior (Spike 01) usó una rampa hasta 800 usuarios virtuales (VUs) y mostró un sistema ya degradado (p95 ≈ 41 s, error ≈ 18 %); no permite ver **en qué punto** empieza la degradación. Este experimento sube la carga por escalones, desde 1 VU hasta 800, para localizarlo.

## 2. Origen del diseño

La idea de **escalones discretos de carga**, **checks estrictos** (para evitar "falsos verdes") y **descarte de la primera corrida** viene de un script de ejemplo de un compañero, que estaba escrito para otro sistema (`/api/checkout`, puerto 8080, 50 a 200 VUs). Se adaptó a UrbanFix: endpoint real, escalones calculados con los datos del Spike 01 (el sistema se satura con muy pocos usuarios, así que empezar en 50 VUs no permitiría ver el punto de degradación) y umbrales definidos desde los datos.

## 3. Hipótesis y predicciones (derivadas del Spike 01)

Con ~15 logins exitosos por segundo como capacidad observada y un hash `scrypt:32768:8:1` costoso en CPU por cada login:

> **H1.** (a) La latencia se degrada (p95 > 1 s) con **50 VUs o menos**. (b) El **quiebre por errores** (error > 5 %) no ocurre antes de **200 VUs**, porque los errores aparecen cuando la espera en cola supera el tiempo máximo del pool. (c) La capacidad de logins exitosos por segundo llega a una **meseta** a partir de pocos VUs y no crece al subir la carga.

La hipótesis se **respalda** si se cumplen (a) y (b); la (c) se reporta como observación. Se **refuta** si falla (a) o (b).

## 4. Definiciones operativas (umbrales)

| Concepto | Definición |
|---|---|
| Punto de degradación | Primer escalón con p95 mediano > 1.000 ms |
| Punto de quiebre | Primer escalón con tasa de error mediana > 5 % (el umbral ya usado en ESC-07) |
| Meseta de capacidad | Primer escalón en que los logins exitosos por segundo crecen menos de 10 % respecto al escalón anterior |
| Login exitoso | Respuesta HTTP 200 cuyo cuerpo contiene "exitoso" (dos checks de k6) |
| Límite del instrumento | Escalones donde k6 consume más del 25 % de la CPU total del equipo |

## 5. Método

- **Escalones:** 1, 5, 10, 25, 50, 100, 200, 400 y 800 VUs constantes, uno tras otro. Cada uno dura **45 s** y entre escalones hay **30 s** de enfriamiento. Cada escalón es un *scenario* de k6 (`paso_NNNN`), de modo que cada métrica queda etiquetada con su escalón.
- **Corridas:** 4 en total (~11 min cada una), con pausa de al menos 2 minutos y **sin reiniciar contenedores**. Se **descarta la corrida 1** (calentamiento) y se usa la **mediana de las corridas 2 a 4** por escalón.
- **Carga por VU:** una petición, `sleep(0.1)`, repetir (igual que la medición anterior).
- **Instrumento:** `crecimiento.js`. Antes de medir se hace una prueba de humo (debe dar 100 % de checks correctos) y una prueba negativa con clave incorrecta (los checks deben fallar al 100 %).
- **Instrumentación:** cada ~2–3 s se registran CPU total del equipo, CPU consumida por k6, CPU y memoria del backend, CPU de la BD y conexiones abiertas a Postgres.
- **Análisis:** `resumir.py` calcula por escalón p95, error, logins OK/s y recursos, y aplica las definiciones de la sección 4.

## 6. Condiciones de medición

| Aspecto | Valor |
|---|---|
| Sistema medido | Rama `main` sin modificaciones, con el `docker-compose.yml` original (sin PgBouncer), servidor `python3 app.py` (`debug=True`) |
| Máquina | La misma de las mediciones anteriores: laptop de Samuel (Intel Core i5-1035G1, 16 GB). k6 corre en la misma máquina |
| Endpoint y datos | `POST http://127.0.0.1:5000/login`, usuario fijo de prueba; filas de la BD y hash registrados en `resultados/condiciones.txt` |
| Semilla | No hay aleatoriedad: credenciales y carga fijas |
| Orden | Una sola configuración; no hay brazo de comparación |

## 7. Alcance

Solo se **agregan** archivos bajo `experimentos/crecimiento-S11/`. No se modifica código de la aplicación, ni `main` fuera de esta carpeta, ni los scripts de mediciones anteriores.

## 8. Qué invalidaría la medición

1. k6 satura el equipo antes que el sistema (se revisa el % de CPU de k6 por escalón; si pasa del umbral se declara como límite del instrumento, no se oculta).
2. Otra aplicación pesada en ejecución, equipo con batería o suspendido durante la corrida.
3. Cambios en el código, la BD o la configuración entre corridas.
4. Menos de 3 corridas válidas.

## 9. Interpretación acordada de antemano

- **Respaldada:** se documenta el punto de degradación y de quiebre, y la meseta de capacidad como el límite observable del sistema en este entorno.
- **Refutada:** se documenta cuál predicción falló y se usa el dato medido; no se vuelve a correr hasta ver un resultado que encaje.
- En ambos casos el resultado vale **solo para este entorno** (servidor de desarrollo, laptop, un usuario, un endpoint) y no se extrapola a producción.

## 10. Límites conocidos de antemano

- k6 comparte CPU con el sistema; se mide su consumo pero no se elimina.
- La cola de un escalón alto puede seguir drenando durante el enfriamiento y contaminar parcialmente el siguiente (por eso los 30 s de pausa).
- Un escalón es un periodo corto (45 s): sirve para ubicar el punto de degradación, no para estimar estabilidad a largo plazo.
- El muestreo de recursos es aproximado (~2–3 s).

