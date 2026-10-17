# Veredicto del Spike 01 (BORRADOR — revisar y completar a mano)

**Veredicto:** HIPOTESIS REFUTADA. Regla aplicada: la definida en `exp/00-preregistro.md` (medianas de 3 corridas validas en linea base y 3 en spike, descartando la corrida 1 de cada brazo).

## Resultados
Ver `resultados/resumen.md` (tabla completa) y los archivos crudos en `resultados/`.

## Lo que muestran los datos de recursos
- CPU maxima mediana del backend: linea base 969.78 %, spike 1,117.15 %.
- Conexiones maximas a Postgres (mediana): linea base 16, spike 16.
- COMPLETAR: que recurso se saturo primero (CPU o conexiones) y que dice eso sobre la premisa del ADR 0002.

## Interpretacion acordada de antemano (pre-registro, seccion 9)
- Si fue respaldada: PgBouncer entra al ADR 3 como alternativa viable, con los limites declarados.
- Si fue refutada: la premisa "el pool es la causa" no se sostiene con esta evidencia; el ADR 3 se redacta con los datos de CPU y conexiones.

## Limites de la evidencia (del pre-registro, seccion 10)
- Medicion local en el laptop de Samuel (i5-1035G1, 16 GB), no en produccion (EC2 t2.micro + Neon).
- Un solo usuario de prueba y un solo endpoint (`POST /login`); no se evaluo aislamiento entre dominios.
- No se midio mantenibilidad, costo ni comportamiento de `/reportes`.
- COMPLETAR: cualquier desviacion del protocolo ocurrida durante las corridas.
