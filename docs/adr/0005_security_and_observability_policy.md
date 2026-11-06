# ADR 0005 — Política de seguridad y observabilidad (Resumido)

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán  
**Estado:** Propuesta  
**Fecha:** 2026-11-06  

---

## Contexto

El sistema funciona como un monolito en una sola instancia EC2 (Alternativa B del ADR 0004). Se requiere establecer las herramientas para mitigar las vulnerabilidades críticas detectadas (falta de autenticación/autorización centralizada, filtrado de datos personales, uso de `print` para errores y credenciales expuestas) sin elevar sustancialmente los costos de infraestructura ($O(1)$).

---

## Decisiones Seleccionadas

### 1. Seguridad

* **Borde y Transporte (HTTPS/Rate Limit):** Uso de **Nginx + Let's Encrypt** en el mismo EC2 para TLS y throttling en `/login` antes de consumir CPU en `scrypt`. Se descarta ALB/WAF para mantener costos en 0 USD adicionales.
* **Autenticación y Autorización:** Implementación de **JWT propio** validado centralmente en la API (`before_request`). Se rechaza Cognito para evitar redefinir contraseñas y acoplar el backend a AWS.
* **Secretos:** Almacenamiento seguro en **AWS SSM Parameter Store** (SecureString), descartando variables `.env` expuestas.
* **Credenciales de AWS:** Asignación de Roles IAM a la instancia EC2 e imágenes S3 con URLs prefirmadas.

### 2. Observabilidad

* **Logging:** Reemplazo de `print` por la librería nativa `logging` en formato **JSON** estándar exportado por `stdout`.
* **Métricas y Trazas:** Adopción del SDK de **OpenTelemetry** (OTLP/HTTP) instrumentado hacia un Collector centralizado.
* **Almacenamiento y Alertas:** Stack autoalojado de **Prometheus + Grafana**.
* **Condición de Activación de Telemetría (O-5):** La telemetría permanecerá desactivada (`OTEL_ENABLED` sin definir) hasta evaluar en pruebas de carga que el consumo de recursos no reduzca la capacidad de la API en más de un 10%.

---

## Reglas Obligatorias de la Política

1. **S-1:** Validación de JWT en todas las rutas a excepción de endpoints públicos (`/login`, catálogo, `/health`).
2. **S-2 / S-3:** Control estricto de propiedad sobre recursos y respuestas filtradas mediante DTOs.
3. **S-4 / S-5:** Entrada exclusiva vía HTTPS 443 con Nginx y consumo de secretos desde SSM en tiempo de arranque.
4. **O-1:** Prohibición absoluta del uso de `print`; uso obligatorio de `log.exception` con `request_id`.
5. **O-3:** Verificación activa de conectividad con la BD en el endpoint `/health` (`SELECT 1`).
6. **O-4 / O-7:** Registro seudonimizado de eventos de seguridad (Ley 1581) y retención acotada de logs/métricas.

---

## Fitness Functions Incorporadas

Se agregan pruebas automatizadas de arquitectura en `tests/architecture/`:

* **FF-03:** Verifica que toda ruta fuera de la lista blanca tenga el decorador de autenticación.
* **FF-04:** Asegura que no existan sentencias `print(` dentro del directorio `app/`.
* **FF-05:** Valida que `debug=True` esté deshabilitado en producción y que la base de datos local esté ignorada en Git.

---

## Consecuencias y Riesgos Aceptados

* **Positivas:** Reducción de riesgos de seguridad críticos de nivel 9 a niveles aceptables ($2\text{--}3$) manteniendo costos adicionales de infraestructura cercanos a 0 USD/mes.
* **Negativas:** La administración del certificado TLS y Nginx recae totalmente en el equipo. La revocación anticipada de JWT no está implementada (depende del tiempo de expiración). El contrato de la API requiere actualización simultánea con la app móvil.