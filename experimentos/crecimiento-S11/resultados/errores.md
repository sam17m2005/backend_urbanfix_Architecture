# Errores por tipo y momento (experimento de crecimiento)

Fuente: avisos `Request Failed` de la consola de k6 (corridas válidas 2 a 4) y códigos de respuesta del CSV.

## Conexiones rechazadas: ¿cuándo ocurren?

- Primeros 5 s de un escalón: **2656** · resto del escalón: **0** (suma de las 4 corridas).

## Tasa de error por escalón: total y sin contar las conexiones rechazadas (mediana de las corridas válidas)

| VUs | Error total | Error sin conexiones rechazadas | HTTP 500 | Sin respuesta (todas) | de ellas: rechazadas | de ellas: timeout 60 s |
|---|---|---|---|---|---|---|
| 1 | 0.00 % | 0.00 % | 0 | 0 | 0 | 0 |
| 5 | 0.00 % | 0.00 % | 0 | 0 | 0 | 0 |
| 10 | 0.00 % | 0.00 % | 0 | 0 | 0 | 0 |
| 25 | 0.00 % | 0.00 % | 0 | 0 | 0 | 0 |
| 50 | 0.00 % | 0.00 % | 0 | 0 | 0 | 0 |
| 100 | 0.00 % | 0.00 % | 0 | 0 | 0 | 0 |
| 200 | 2.79 % | 2.79 % | 21 | 0 | 0 | 0 |
| 400 | 23.83 % | 7.46 % | 68 | 185 | 185 | 0 |
| 800 | 59.64 % | 37.36 % | 159 | 887 | 585 | 289 |

Nota: los avisos de k6 se ubican en su escalón por la hora (tolerancia de 2 s); la clasificación es aproximada en los bordes de cada escalón.