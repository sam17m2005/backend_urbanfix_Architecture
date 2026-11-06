# 04 · Criterios de evaluación del riesgo

El sílabo no impone escala; adoptamos una matriz cualitativa **3 × 3** (probabilidad × impacto) porque el equipo no tiene
datos históricos de incidentes que justifiquen una escala más fina. Cada calificación en la matriz lleva su justificación
textual: el número resume, la justificación es lo que se evalúa.

## 1. Probabilidad (P)

| Valor | Nivel | Criterio para UrbanFix |
|---|---|---|
| 1 | Baja | Requiere acceso privilegiado previo (cuenta de AWS, máquina del equipo) o una condición que hoy no se da (despliegue inactivo) |
| 2 | Media | Requiere una condición adicional plausible: red Wi-Fi compartida, que el host esté expuesto, conocimiento técnico intermedio |
| 3 | Alta | Lo puede ejecutar cualquiera con `curl` o leyendo el repositorio público; o ya ocurrió (la exposición existe hoy) |

## 2. Impacto (I)

| Valor | Nivel | Criterio para UrbanFix |
|---|---|---|
| 1 | Bajo | Afecta a un usuario, es reversible y no involucra datos personales |
| 2 | Medio | Afecta a varios usuarios o a la operación del piloto, o expone datos de bajo riesgo; recuperable |
| 3 | Alto | Expone datos personales de forma masiva (Ley 1581/2012), permite actuar como otro usuario o funcionario, compromete credenciales, o tumba todo el servicio (un solo proceso, ADR 0001) |

## 3. Nivel de riesgo (R = P × I)

| P \ I | 1 Bajo | 2 Medio | 3 Alto |
|---|---|---|---|
| **3 Alta** | 3 Medio | 6 Alto | **9 Crítico** |
| **2 Media** | 2 Bajo | 4 Medio | 6 Alto |
| **1 Baja** | 1 Bajo | 2 Bajo | 3 Medio |

| Nivel | Tratamiento |
|---|---|
| Crítico (9) | Mitigar antes de cualquier despliegue con usuarios reales; bloquea el piloto |
| Alto (6) | Mitigar en la siguiente iteración; documentar aceptación temporal |
| Medio (3–4) | Planificar; aceptable en prototipo con justificación |
| Bajo (1–2) | Aceptar y monitorear |

## 4. Clasificación de amenazas

Cada riesgo se etiqueta con:

- **STRIDE** (origen del tipo de amenaza): **S**uplantación, **T**ampering (manipulación), **R**epudio, **I**nformación
  expuesta, **D**enegación de servicio, **E**levación de privilegios.
- **OWASP Top Ten 2021** (A01 Control de acceso roto … A10 SSRF) y, donde aplica, **OWASP API Security Top 10 2023**
  (API1 BOLA, API2 Autenticación rota, API3 Exposición de propiedades, API4 Consumo sin límites, API5 BFLA).

## 5. Estado de cada control

| Estado | Significado | Evidencia exigida |
|---|---|---|
| **Propuesto** | Diseñado en este entregable, sin código | Descripción, ubicación y prueba de verificación escrita |
| **Implementado** | Existe en el código en un commit identificable | Commit / PR |
| **Verificado** | Implementado y la prueba asociada pasa en CI | Salida de `pytest tests/security` en verde, sin marca `xfail` |

Las pruebas de `tests/security/` usan `xfail(strict=True)`: mientras el control no exista la prueba falla «esperadamente»
(evidencia del riesgo); cuando se implementa, la prueba pasa, `strict` la convierte en error y obliga a quitar la marca.
Ese cambio queda en el historial de Git como la transición **Propuesto → Verificado**.
