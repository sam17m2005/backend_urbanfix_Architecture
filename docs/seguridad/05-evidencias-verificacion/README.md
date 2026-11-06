# 05 · Evidencias de verificación

| Archivo | Qué demuestra | Cómo reproducirlo |
|---|---|---|
| `pytest-linea-base.txt` | Estado de los controles al 2026-11-06: **3 PASSED** (controles existentes) y **20 XFAIL** (riesgos confirmados, controles no implementados) | `pip install -r requirements.txt pytest` y `pytest tests/security -v -rxX` desde la raíz del backend |
| `hallazgos-repositorio.md` | Revisión de secretos y datos en ambos repositorios | Comandos incluidos en el archivo |

## Cómo se leen las pruebas

- Las pruebas corren la **app real** (`create_app()`, rutas y modelos del repositorio) con una base de datos de prueba en memoria; S3 se
  reemplaza por un doble para no requerir red ni claves.
- Cada prueba se escribió para pasar **solo cuando el control exista**. Hoy fallan por la razón esperada; esto se comprobó
  ejecutando `pytest tests/security --runxfail --tb=line`, que muestra la aserción concreta que falla
  (p. ej. `assert 200 in (401, 403)` al borrar un reporte ajeno).
- Al implementar un control, sus pruebas pasan a XPASS y `strict=True` las vuelve error: el PR del control debe quitar
  la marca `@pendiente(...)`. Así el historial de Git muestra cuándo cada control pasó a **Verificado**.
- `tests/architecture` (fitness function existente) sigue en verde: 6 passed.
