# Resumen de resultados — Spike 01

Corridas encontradas: baseline [1, 2, 3, 4], spike [1, 2, 3, 4]. Se descarta la corrida 1 de cada brazo; validas: baseline 3, spike 3 (minimo 3).

## Corrida por corrida (p95 s / error)

- **Linea base:** corrida 2: 40.13 s / 17.94 %; corrida 3: 41.44 s / 15.24 %; corrida 4: 43.70 s / 18.41 %
- **Spike:** corrida 2: 40.80 s / 0.00 %; corrida 3: 40.84 s / 0.00 %; corrida 4: 40.65 s / 0.00 %

## Medianas por brazo

| Metrica | Linea base | Spike |
|---|---|---|
| p95 http_req_duration (s) | 41.44 | 40.80 |
| promedio (s) | 18.27 | 19.74 |
| tasa de error | 17.94 % | 0.00 % |
| throughput (req/s) | 15.41 | 12.96 |
| peticiones | 1,380 | 1,166 |
| respuestas 2xx | 1,146 | 1,166 |
| respuestas 4xx | 0 | 0 |
| respuestas 5xx | 254 | 0 |
| sin respuesta / timeout | 0 | 0 |
| CPU backend promedio (%) | 788.47 | 819.53 |
| CPU backend maximo (%) | 969.78 | 1,117.15 |
| memoria backend maxima (MiB) | 708.00 | 646.20 |
| conexiones max. a Postgres | 16 | 16 |

## Criterios del pre-registro

| Criterio | Resultado | Cumple |
|---|---|---|
| p95 mediano spike <= 0,70 x linea base | 40.80 s vs 41.44 s (mejora 1.5 %) | NO |
| error mediano spike <= 5 % | 0.00 % | SI |
| 5xx no aumentan frente a linea base | 0.00 % vs 18.41 % de las respuestas | SI |

**Veredicto segun la regla pre-registrada: HIPOTESIS REFUTADA** (al menos un criterio no se cumple).
