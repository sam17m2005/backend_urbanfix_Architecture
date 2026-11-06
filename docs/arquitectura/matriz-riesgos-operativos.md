# Matriz de riesgos operativos — Backend UrbanFix (Resumido)

**Entregable:** Módulo 7 · Matriz de riesgos operativos (Acompaña al [ADR 0005](../adr/0005_security_and_observability_policy.md))  
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán  
**Fecha:** 2026-11-06  

---

## 1. Propósito y alcance

Responde **qué puede salir mal al operar el sistema**: caídas, saturación, pérdida de datos, errores invisibles y los riesgos derivados de la infraestructura y herramientas del ADR 0005.

**Sistema analizado:** Monolito en Docker Compose local y despliegue objetivo del ADR 0005 (EC2 única / alternativa B del ADR 0004 con paquete P1).

---

## 2. Criterios de Evaluación

Matriz de evaluación de riesgos ($3 \times 3$):

* **Probabilidad (P):** 1 (Improbable/Requiere mala config) · 2 (Plausible en piloto / ya ocurrió) · 3 (Frecuente / fácil de reproducir).
* **Impacto (I):** 1 (Bajo/Recuperable) · 2 (Degrada servicio para varios usuarios) · 3 (Caída total del servicio / pérdida de datos).
* **Nivel de Riesgo ($R = P \times I$):** $9$ Crítico · $6$ Alto · $3\text{--}4$ Medio · $1\text{--}2$ Bajo.

---

## 3. Matriz de Riesgos Operativos

| ID | Riesgo Operativo | Componente | P | I | Nivel | Mitigación Principal | Estado | Residual |
|---|---|---|---|---|---|---|---|---|
| **OPR-01** | Caída total de la instancia o proceso (un solo contenedor). | EC2 / Docker | 2 | 3 | **6 Alto** | `restart: always` (R-14), Gunicorn workers (R-15), evaluar escalado a réplicas (Alt. C). | Implementada sin probar | 3 |
| **OPR-02** | Saturación de CPU en `/login` por cálculo de `scrypt`. | API / Auth | 2 | 3 | **6 Alto** | Límite de tasa en Nginx (S-4 / R-04) previo al hash; escalado horizontal. | Propuesta | 3 |
| **OPR-03** | Agotamiento del pool de conexiones de base de datos (`500`). | SQLAlchemy | 2 | 2 | **4 Medio** | `pool_timeout` ajustado con respuesta `503` (R-02); uso de PgBouncer. | Propuesta | 2 |
| **OPR-04** | BD caída sin detección (`GET /` responde `200` falso). | PostgreSQL | 2 | 3 | **6 Alto** | `/health` ejecutando `SELECT 1` + Docker `healthcheck`. | `/health` en PoC | 3 |
| **OPR-05** | **Pérdida irreversibilidad de datos** por falta de respaldos probados. | PostgreSQL | 2 | 3 | **6 Alto** | Automatización de `pg_dump` externo con pruebas periódicas de restauración. | Propuesta | 2 |
| **OPR-06** | Falsos positivos en S3 (reporte guardado sin la imagen). | Utils S3 | 2 | 3 | **6 Alto** | Validar respuesta de S3 antes de responder `201` (R-07); evento de fallo de subida. | PoC parcial | 2 |
| **OPR-07** | Captura silenciosa de errores usando `print` sin logging centralizado. | API Flask | 3 | 2 | **6 Alto** | Reemplazar `print` por `log.exception` en JSON con `request_id` (O-1) + CI rules. | Propuesta | 2 |
| **OPR-08** | Monitoreo inefectivo (alertas sin recepción ni guardia asignada). | Operación | 3 | 2 | **6 Alto** | Stack Prometheus + Grafana (O-6) con rol de guardia rotativo y simulacros. | Propuesta | 3 |
| **OPR-09** | Degradación del rendimiento por sobrecarga del SDK de OpenTelemetry. | OpenTelemetry | 2 | 2 | **4 Medio** | Telemetría inactiva por defecto hasta evaluar su costo de CPU/memoria (O-5). | Propuesta | 2 |
| **OPR-10** | Despliegue defectuoso en producción desde `main`. | CI/CD | 1 | 3 | **3 Medio** | PR obligatorio con CI en verde, versión fija de imágenes y estrategia de rollback. | Propuesta | 2 |
| **OPR-11** | Expiración del certificado TLS de Let's Encrypt. | Nginx | 1 | 3 | **3 Medio** | Renovación automática vía certbot (`--dry-run`) y alertas preventivas. | Propuesta | 2 |
| **OPR-12** | Compromiso o pérdida de secretos (`JWT_SECRET`, BD). | SSM / API | 1 | 3 | **3 Medio** | Gestión centralizada en SSM Parameter Store, escaneo de credenciales con Gitleaks. | Propuesta | 2 |
| **OPR-13** | Dependencia del conocimiento en 1 o 2 integrantes del equipo. | Operación | 2 | 2 | **4 Medio** | Runbooks operativos documentados (OP-01 a OP-05) y accesos compartidos. | Parcial | 2 |
| **OPR-14** | Exposición involuntaria de datos personales en logs/trazas (Ley 1581). | Observabilidad | 2 | 2 | **4 Medio** | Seudonimización de cuentas, sanitización de parámetros de URLs y política de retención. | Propuesta | 1 |
| **OPR-15** | Saturación de disco o memoria por acumulación de logs. | Host EC2 | 2 | 2 | **4 Medio** | Configuración de límites de tamaño (`max-size`) en driver de Docker y Prometheus. | Parcial | 1 |
| **OPR-16** | Límites y arranques en frío en el tier gratuito de Neon DB. | PostgreSQL | 2 | 2 | **4 Medio** | Migrar a plan comercial de Neon al iniciar pruebas masivas con usuarios. | Aceptado | 1 |
| **OPR-17** | Incremento inoportuno de costos en AWS por servicios gestionados. | AWS | 1 | 2 | **2 Bajo** | Alertas de presupuesto AWS y justificación estricta de cambios de arquitectura. | Propuesta | 1 |

---

## 4. Prioridades de Mitigación

1. **OPR-05 (Respaldos):** Implementar script de respaldo y prueba de restauración inmediata.
2. **OPR-07 y OPR-04 (Visibilidad):** Reemplazar `print` por logs estructurados en JSON y desplegar endpoint `/health`.
3. **OPR-09 (Telemetría):** Medir la penalización de rendimiento del SDK antes de activar telemetría en producción.
4. **OPR-08 (Alertas):** Desplegar Prometheus + Grafana y coordinar turnos de soporte.