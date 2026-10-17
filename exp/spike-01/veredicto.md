# Veredicto del Spike 01 (BORRADOR — revisar y completar a mano)

**Veredicto:** HIPOTESIS REFUTADA. Regla aplicada: la definida en `exp/00-preregistro.md` (medianas de 3 corridas validas en linea base y 3 en spike, descartando la corrida 1 de cada brazo).

## Resultados
Ver `resultados/resumen.md` (tabla completa) y los archivos crudos en `resultados/`.

## Lo que muestran los datos de recursos
- CPU maxima mediana del backend: linea base 969.78 %, spike 1,117.15 %.
- Conexiones maximas a Postgres (mediana): linea base 16, spike 16.
- Recurso saturado: en ambos brazos la CPU del backend estuvo saturada (mediana del máximo ≈ 970 % en baseline y ≈ 1.117 % en spike; 100 % equivale a un núcleo), y las conexiones a Postgres llegaron al tope de 16 en ambos. PgBouncer eliminó los errores (5xx: 254 → 0; error 17,9 % → 0 %), pero no redujo el p95 (41,44 s → 40,80 s, −1,5 %). La premisa del ADR 0002 ("el agotamiento del pool es la causa de la degradación") no se sostiene con esta evidencia: el pool explicaba los errores, no la latencia. La CPU, coherente con el hash scrypt:32768:8:1 por login, queda como causa candidata para el ADR 3; este spike no la demuestra.

## Interpretacion acordada de antemano (pre-registro, seccion 9)
- Si fue respaldada: PgBouncer entra al ADR 3 como alternativa viable, con los limites declarados.
- Si fue refutada: la premisa "el pool es la causa" no se sostiene con esta evidencia; el ADR 3 se redacta con los datos de CPU y conexiones.

## Limites de la evidencia (del pre-registro, seccion 10)
- Medicion local en el laptop de Samuel (i5-1035G1, 16 GB), no en produccion (EC2 t2.micro + Neon).
- Un solo usuario de prueba y un solo endpoint (`POST /login`); no se evaluo aislamiento entre dominios.
- No se midio mantenibilidad, costo ni comportamiento de `/reportes`.
- Desviaciones y límites adicionales: (1) k6 corrió en la misma laptop que el sistema y su CPU no se midió; (2) el throughput de esta sesión (~15 req/s) es la mitad de la medición anterior, así que solo es válida la comparación baseline vs. spike de hoy; (3) el baseline se midió antes que el spike, sin alternar; (4) la causa de los 5xx del baseline no se verificó; (5) 3 corridas válidas por brazo (el mínimo); (6) las primeras corridas fallaron por una URL inalcanzable (172.18.0.1) y se descartaron.

## Validación metodológica
| Aspecto | Resultado |
|---|---|
| Condiciones equivalentes | Sí: misma laptop, mismo día, mismo código en las corridas válidas (commit 9df270c). Límite: el baseline se midió antes que el spike, sin alternar |
| Número de corridas | 4 por brazo; se descarta la 1 y se usan 3 |
| Herramienta de medición | k6 v2.2.0, mismo script (Pruebas/prueba2.js) |
| Carga de prueba | Igual en ambos brazos (rampa hasta 800 VUs) |
| Datos de prueba | Mismos: 1 usuario, 10 reportes, 0 funcionarios |
| Respuestas correctas | Spike: 100 % 2xx. Baseline: ~82 % 2xx y ~18 % 5xx, por debajo de lo ideal para una comparación limpia, y se declara como límite |

## Decisión
Con base en el veredicto (hipótesis refutada), se decide:
1. **No adoptar PgBouncer ni la capa de repositorios del ADR 0002 como solución a la latencia de ESC-07.** No redujo el p95 (−1,5 % frente al −30 % exigido).
2. **No invertir las ~30 h del ADR 0002 con esa premisa**, porque la evidencia de este spike la refuta.
3. **PgBouncer queda como opción para controlar errores bajo carga** (5xx: 254 → 0; error 17,9 % → 0 %). No se interpreta como mejora de capacidad: el p95 sigue en ~41 s.
4. **Siguiente hipótesis fuera de este spike:** el costo de CPU por login (scrypt), que este spike no demuestra.
Reversibilidad: el spike vive en su rama y no se mezcló con `main`.
