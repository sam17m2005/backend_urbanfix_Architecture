# 07 · Declaración de uso de IA

**Herramienta:** Claude (Anthropic).

## Qué generó la IA

| # | Aporte de la IA | Cómo lo verificamos |
|---|---|---|
| 1 | Revisión de `routes.py`, `models.py`, `utils.py`, `config.py`, `app.py`, `dockerfile`, `docker-compose.yml`, workflows y app Android, e identificación de los 14 riesgos | |
| 2 | Hallazgo de la carpeta `data/` versionada con hashes y correos | Repetir los comandos de `05/hallazgos-repositorio.md` |
| 3 | Hallazgo de la clave de Gemini en `AIService.kt` | Comprobar en Google AI Studio y rotarla |
| 4 | Escala de riesgo 3 × 3 y calificaciones P/I de cada riesgo | Discutir cada calificación en equipo |
| 5 | Diseño de los controles CTL-01 a CTL-14 | |
| 6 | Pruebas `tests/security/` (23 pruebas) y su ejecución de línea base | Ejecutar `pytest tests/security --runxfail --tb=line` y leer cada aserción |
| 7 | Diagrama de superficie de ataque (`02-*.dot` / `.png`)| Contrastar con el C4 de contenedores (`docs/06`) |

## Limitaciones conocidas del aporte de la IA

- No tuvo acceso a la cuenta AWS, a Neon ni a la instancia EC2: todo lo relativo a IAM y buckets es inferencia (SEG-12).
- `foto_perfil_url` es `NOT NULL` en el modelo y no aparece en la migración: conviene revisar que el esquema real coincida.
