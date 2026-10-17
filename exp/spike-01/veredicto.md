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
