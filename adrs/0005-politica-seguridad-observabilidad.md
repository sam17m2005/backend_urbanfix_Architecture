# ADR 0005 — Política de seguridad y observabilidad 

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

## Alternativas evaluadas

Los costos y las comparaciones salen de [08-diagrama-despliegue-y-costos.md](../docs/seguridad/08-diagrama-despliegue-y-costos.md), con la base de la alternativa B del ADR 0004 (≈ 19 USD/mes).

| Decisión | Elegida | Alternativas evaluadas | Por qué se eligió |
|---|---|---|---|
| Borde: TLS y límite de tasa | Nginx + Let's Encrypt en la misma EC2 (≈ 0 USD/mes adicionales) | ALB + ACM (≈ 22 USD/mes; no limita la tasa por sí solo) · ALB + ACM + WAF (≈ 31 USD/mes con 4 reglas y ~1 M de peticiones) | Aplica el límite antes de gastar CPU en `scrypt`, sin costo; la operación del certificado recae en el equipo (08 §3.1) |
| Secretos | SSM Parameter Store (≈ 0) | `.env` en el servidor (actual) · Secrets Manager (≈ 1,6 USD/mes con 4 secretos) | Cifrado con KMS y auditoría sin costo; la rotación es manual (08 §3.2) |
| Autenticación | JWT propio en Flask (0 USD; ~10 h de desarrollo) | Amazon Cognito (0 hasta 10.000 MAU; exige restablecer o migrar contraseñas y acopla el backend a AWS) | Reutiliza los hashes `scrypt` actuales y no añade un límite de confianza (08 §3.3) |
| Credenciales a S3 | Rol IAM de instancia + URLs prefirmadas (0) | Claves IAM estáticas con URLs públicas (actual) · CloudFront con OAC (no cuantificado) | Credenciales temporales y objetos privados (08 §3.4) |
| Observabilidad | OpenTelemetry (OTLP/HTTP) + Collector + Prometheus + Grafana autoalojados | Solo logs JSON por `stdout` (ya implementado en la prueba de concepto; sin alertas ni métricas almacenadas) · Servicio gestionado de AWS (**no evaluado con costos**) | Estándar abierto con alertas sin costo por servicio. **Su consumo de memoria no está medido** (ver supuestos) |

**Paquetes de costo** (08 §4.2): el conjunto elegido es el paquete P1 (≈ 19 USD/mes, índice 1,0×); P2 (ALB + ACM + Secrets Manager) ≈ 43 USD/mes (≈ 2,3×); P3 (ALB + WAF + Cognito + CloudFront) ≈ 52 USD/mes o más (≈ 2,8×).

## Reglas Obligatorias de la Política

1. **S-1:** Validación de JWT en todas las rutas a excepción de endpoints públicos (`/login`, catálogo, `/health`).
2. **S-2 / S-3:** Control estricto de propiedad sobre recursos y respuestas filtradas mediante DTOs.
3. **S-4 / S-5:** Entrada exclusiva vía HTTPS 443 con Nginx y consumo de secretos desde SSM en tiempo de arranque.
4. **O-1:** Prohibición absoluta del uso de `print`; uso obligatorio de `log.exception` con `request_id`.
5. **O-3:** Verificación activa de conectividad con la BD en el endpoint `/health` (`SELECT 1`).
6. **O-4 / O-7:** Registro seudonimizado de eventos de seguridad (Ley 1581) y retención acotada de logs/métricas.

---

## Fitness Functions Incorporadas

Se definen tres pruebas automatizadas de arquitectura en `tests/architecture/test_fitness_seguridad_observabilidad.py`, junto a FF-01 y FF-02 (ADR 0001 y ADR 0003), y se ejecutan en el mismo workflow de CI.

**Estado a 2026-11-06: pendientes.** Hoy detectan violaciones reales del código de `main`, así que están marcadas como fallo esperado (`xfail` estricto) y el CI sigue en verde. Cuando el control correspondiente se implemente, la prueba pasa a cumplirse, `strict=True` la convierte en error y el PR del control debe quitar la marca. Así el historial de Git deja registrado cuándo cada regla empezó a cumplirse. Los **detectores** se verifican siempre con código sintético, sin marca.

| Regla | Qué verifica | Qué detecta hoy en `main` |
|---|---|---|
| **FF-03** | Toda función de ruta fuera de la lista blanca (`/login`, `POST /usuarios`, `GET /categorias`, `GET /estados-reporte`, `/health` y `/`) lleva el decorador `@requiere_auth` | 34 combinaciones método + ruta sin protección |
| **FF-04** | No hay `print(` en `app/` | 18 `print(` (16 en `routes.py` y 2 en `utils.py`) |
| **FF-05** | `debug=True` desactivado en `app.py`, y `data/` ni versionada ni sin ignorar | `debug=True` activo y `data/` versionada (1.314 archivos) |

La regla S-1 describe la validación del token en `before_request`; FF-03 exige además el decorador explícito en cada ruta, como segunda barrera visible en el código (**criterio a ratificar por el equipo**). Una función que mezcle un método público y otro protegido, como `/usuarios` (`GET` y `POST`), obliga a separarse: coincide con el control CTL-04, que elimina `GET /usuarios`.

## Consecuencias y Riesgos Aceptados

* **Positivas:** Reducción de riesgos de seguridad críticos de nivel 9 a niveles aceptables ($2\text{--}3$) manteniendo costos adicionales de infraestructura cercanos a 0 USD/mes.
* **Negativas:** La administración del certificado TLS y Nginx recae totalmente en el equipo. La revocación anticipada de JWT no está implementada (depende del tiempo de expiración). El contrato de la API requiere actualización simultánea con la app móvil.

---

## Reversibilidad

| Decisión | ¿Reversible? | Cómo se revierte y qué cuesta | Base |
|---|---|---|---|
| Nginx + Let's Encrypt | Alta | Retirar el contenedor y volver a publicar el puerto del backend; si el cliente móvil ya migró a HTTPS, debe volver a HTTP | Análisis |
| JWT propio | Media | Volver a leer la identidad del cuerpo reabre SEG-01 a SEG-03; exige actualizar la app móvil a la vez (consecuencia ya declarada) | Análisis |
| SSM Parameter Store | Alta | `config.py` ya lee todas las credenciales con `os.getenv`: basta volver a inyectarlas desde un `.env` | Inspección de `config.py` |
| Rol IAM + URLs prefirmadas | Media | Las imágenes existentes se guardan como URL pública de S3; pasar a prefirmadas exige regenerar las URLs | Inspección de `app/utils.py` |
| OpenTelemetry | Alta | Sin `OTEL_ENABLED` la aplicación se comporta igual que antes | **Comprobado** (incluso sin las librerías instaladas; ver el PR de observabilidad) |
| Prometheus + Grafana | Alta | Son contenedores aparte: se retiran sin tocar la aplicación | Análisis |

## Supuestos y condiciones de revisión

| Supuesto | Condición de revisión | Qué pasa si no se cumple |
|---|---|---|
| La telemetría no reduce la capacidad de la API en más de un 10 % (regla O-5) | Medir con el protocolo del experimento de crecimiento (`experimentos/crecimiento.md`), con y sin `OTEL_ENABLED=1`; la capacidad de referencia de `/login` es ≈ 16 logins/s | Se mantiene desactivada, se reduce el muestreo o se descartan las trazas |
| Nginx, Prometheus y Grafana caben en la instancia (`t3.small`) sin cambiar de tipo, por lo que el costo adicional es ≈ 0 | Medir la memoria con `docker stats` bajo carga | Subir el tipo de instancia o mover las métricas a un servicio gestionado; cambia la estimación de costo |
| Los riesgos críticos (9) bajan a 2–3 al implementar CTL-01 a CTL-05. **Es una estimación** con la escala de `docs/seguridad/04-criterios-evaluacion.md` | Las pruebas de SEG-01 a SEG-05 en `tests/security` pasan de `xfail` a pasar | Si alguna sigue en `xfail`, su riesgo no baja y la consecuencia positiva no se sostiene |
| La app móvil puede actualizarse a la vez que el backend | Calendario de publicación de la app | Hay que sostener un periodo de transición, que reabre SEG-01 a SEG-03 mientras dure |
| El equipo puede operar el certificado TLS y Nginx | Falla o vence la renovación del certificado | Migrar el borde a ALB + ACM (paquete P2) |

## Trazabilidad

| Elemento | Ubicación |
|---|---|
| Riesgos SEG-01 a SEG-14 y controles CTL-01 a CTL-14 | [03-matriz-riesgos-controles.md](../docs/seguridad/03-matriz-riesgos-controles.md) |
| Pruebas de los controles (línea base: 3 pasan y 20 `xfail`) | `tests/security/` y [05-evidencias-verificacion](../docs/seguridad/05-evidencias-verificacion/README.md) |
| Alternativas y costo relativo | [08-diagrama-despliegue-y-costos.md](../docs/seguridad/08-diagrama-despliegue-y-costos.md) · [ADR 0004](./0004-decision-distribucion.md) |
| Fitness functions FF-03 a FF-05 | `tests/architecture/test_fitness_seguridad_observabilidad.py` · [fitness-function.md](../docs/arquitectura/fitness-function.md) |
| Documento de seguridad consolidado | [10-seguridad.md](../docs/10-seguridad.md) |
| Plan de observabilidad y su prueba de concepto | `docs/arquitectura/plan-observabilidad.md` y `observabilidad/` (pull request de observabilidad, pendiente de mezcla) |
| Capacidad medida de `/login` | [crecimiento.md](../experimentos/crecimiento.md) |

