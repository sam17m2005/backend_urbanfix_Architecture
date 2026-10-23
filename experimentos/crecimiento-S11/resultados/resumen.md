# Resumen — experimento de crecimiento (POST /login)

Corridas encontradas: [1, 2, 3, 4]. Se descarta la corrida 1 (calentamiento); válidas: 3 (mínimo 3).

## Por escalón: medianas de las corridas válidas

| VUs | Peticiones | p95 (ms) | Error | Logins OK/s | CPU total prom. (%) | CPU backend máx. (%) | k6 % del total | Conexiones BD máx. |
|---|---|---|---|---|---|---|---|---|
| 1 | 146 | 309 | 0.00 % | 3.20 | 37.1 | 79 | 0.2 | 6 |
| 5 | 503 | 522 | 0.00 % | 11.09 | 83.5 | 420 | 0.3 | 6 |
| 10 | 722 | 731 | 0.00 % | 15.91 | 99.2 | 810 | 0.4 | 11 |
| 25 | 760 | 1,984 | 0.00 % | 16.40 | 100.0 | 850 | 0.4 | 16 |
| 50 | 712 | 5,090 | 0.00 % | 14.76 | 100.0 | 1,065 | 0.4 | 16 |
| 100 | 639 | 15,078 | 0.00 % | 11.93 | 100.0 | 1,120 | 0.4 | 16 |
| 200 | 754 | 29,128 | 2.79 % | 12.16 | 100.0 | 1,161 | 0.5 | 16 |
| 400 | 1,189 | 38,052 | 23.83 % | 10.89 | 100.0 | 1,061 | 0.8 | 16 |
| 800 | 1,754 | 56,911 | 59.64 % | 12.04 | 98.1 | 1,081 | 0.9 | 16 |

## p95 por corrida (ms) — para ver la dispersión

| VUs | corrida 1 (descartada) | corrida 2 | corrida 3 | corrida 4 |
|---|---|---|---|---|
| 1 | 359 | 289 | 348 | 309 |
| 5 | 622 | 508 | 522 | 544 |
| 10 | 954 | 1,059 | 694 | 731 |
| 25 | 2,104 | 3,518 | 1,930 | 1,984 |
| 50 | 5,673 | 5,854 | 5,041 | 5,090 |
| 100 | 12,242 | 16,287 | 15,078 | 11,294 |
| 200 | 25,003 | 30,731 | 29,128 | 22,590 |
| 400 | 32,485 | 39,888 | 38,052 | 30,709 |
| 800 | 49,122 | 56,343 | 57,002 | 56,911 |

## Códigos de respuesta por escalón (mediana de peticiones por código)

| VUs | HTTP 0 | HTTP 200 | HTTP 500 |
|---|---|---|---|
| 1 | 0 | 146 | 0 |
| 5 | 0 | 503 | 0 |
| 10 | 0 | 722 | 0 |
| 25 | 0 | 760 | 0 |
| 50 | 0 | 712 | 0 |
| 100 | 0 | 639 | 0 |
| 200 | 0 | 733 | 21 |
| 400 | 185 | 890 | 68 |
| 800 | 887 | 708 | 159 |

## Puntos clave (definiciones del plan)

- **Punto de degradación** (p95 mediano > 1000 ms): primer escalón: **25 VUs**.
- **Punto de quiebre** (error mediano > 5 %): primer escalón: **400 VUs**.
- **Meseta de capacidad** (los logins OK/s crecen menos de 10 % al subir de escalón): desde **25 VUs**; capacidad máxima observada: 16.40 logins OK/s (en 25 VUs).
- **Límite del instrumento** (k6 consume > 25 % de la CPU total): no se superó en ningún escalón. Equipo con CPU total media > 90 %: 10, 25, 50, 100, 200, 400, 800 VUs.

## Evaluación de las predicciones pre-registradas

| Predicción | Resultado | Se cumple |
|---|---|---|
| (a) degradación de latencia con ≤ 50 VUs | 25 VUs | Sí |
| (b) quiebre por errores no antes de 200 VUs | 400 VUs | Sí |

**Veredicto según la regla pre-registrada: HIPÓTESIS RESPALDADA.**
