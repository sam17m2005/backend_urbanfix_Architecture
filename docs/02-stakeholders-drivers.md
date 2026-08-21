# UrbanFix — Stakeholders y Drivers de Calidad

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura de referencia:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Fuente:** Elaboración propia a partir de "UrbanFix - Arquitectura", informes EPI 1 y 2, y READMEs técnicos del repositorio.
**Documentación original de referencia:** <https://drive.google.com/drive/folders/11YCe5JwALD1xJedVkCGfl2IMHHcSY7Er?usp=sharing>

> Ver también [01-contexto-sistema.md](./01-contexto-sistema.md) para el contexto general, las
> restricciones, las tecnologías utilizadas y los riesgos iniciales clasificados.

---

## 1. Mapa de stakeholders

Identificados a partir del análisis de arquitectura, integraciones del sistema y entorno operativo.

| Stakeholder | Tipo | Rol en el proyecto |
|---|---|---|
| **Ciudadanos residentes o visitantes de la ciudad** | Primario — usuario directo | Reportan problemáticas urbanas mediante imágenes y geolocalización; hacen seguimiento al estado de sus reportes. |
| **Instituto de Desarrollo Urbano (IDU)** | Secundario — institucional | Atiende reportes de vías principales (p. ej. Av. Caracas, Cra. 24); debe resolver peticiones dentro de los términos de ley. |
| **UAESP y Empresa de Acueducto y Alcantarillado de Bogotá (EAB)** | Secundario — institucional | Gestión de residuos sólidos, alcantarillado y servicios públicos básicos reportados. |
| **Policía Metropolitana e inspectores de policía locales** | Secundario — regulador | Actúan frente a infracciones al espacio público identificadas vía reportes. |
| **Juntas de Acción Comunal (JAC)** | Secundario — comunitario | Canal tradicional de gestión barrial; fuente de datos de notificación (VEBC); aliado de cercanía. |
| **Alcaldías Locales (Fondos de Desarrollo Local)** | Secundario — institucional | Responsables de malla vial local y parques de bolsillo en cada localidad; priorizan inversión con datos del sistema. |
| **Ciudadanos como titulares de datos personales** | Primario — regulatorio | Sus datos de geolocalización e imágenes deben tratarse bajo libertad y finalidad, con autorización previa e informada. |
| **Proveedores de infraestructura y servicios en la nube** (AWS EC2/S3, Neon, Gemini AI, Mapbox, GitHub) | Externo — técnico/operativo | Sostienen la disponibilidad, el cómputo, el almacenamiento y las integraciones de IA/mapas del sistema. |
| **Equipo de desarrollo** (estudiantes de Ingeniería de Sistemas) | Interno | Investigación, diseño, desarrollo, documentación y pruebas del prototipo funcional. |
| **Docentes / evaluadores académicos** (Arquitectura de Software, Evaluación de Proyectos de Ingeniería) | Interno — evaluador | Validan la calidad técnica, la viabilidad y el cumplimiento de objetivos académicos del proyecto. |

---

## 2. Drivers / Atributos de calidad (ISO/IEC 25010 + PASS MADE)

A partir de la evaluación técnica del sistema (sección "Evaluación del sistema actual en aspectos PASS
MADE") se identifican los siguientes *drivers* arquitectónicos que condicionan las decisiones de diseño:

1. **Rendimiento (Desempeño):** latencia y throughput al crear reportes con imágenes, limitados por una
   instancia EC2 de un solo núcleo.
2. **Disponibilidad:** el backend es un punto único de falla; no hay redundancia ni modo offline en el
   cliente.
3. **Escalabilidad:** el sistema solo escala verticalmente en el backend; S3 y Neon son elásticos por
   diseño.
4. **Seguridad:** manejo de credenciales en `.env` sin gestor de secretos, necesidad de cifrado en
   tránsito y en reposo, y cumplimiento de la Ley 1581 de 2012.
5. **Mantenibilidad:** buena organización modular (MVVM / Blueprints) pero sin pruebas automatizadas.
6. **Accesibilidad:** uso de `contentDescription` de Jetpack Compose en elementos interactivos como base
   de soporte de accesibilidad; población objetivo incluye adultos mayores con menor alfabetización
   digital.
7. **Desplegabilidad:** CI/CD funcional y backend contenerizado con Docker, pero aún sin *staging* ni
   *rollback* automático integrado al pipeline.

### 2.1 Matriz comparativa de atributos de calidad

| Atributo | Estímulo / escenario típico | Estado actual del sistema | Riesgo (Alto/Medio/Bajo) | Recomendación de mejora | Forma de verificación |
|---|---|---|---|---|---|
| **Rendimiento** | Múltiples usuarios crean reportes con imágenes de forma concurrente | Gunicorn con pocos *workers* posibles sobre EC2 t2.micro (1 vCPU/1GB); Compose y Coil optimizan el cliente | **Alto** — el backend es el cuello de botella del sistema | Servir imágenes directo desde S3/CloudFront; ajustar *workers* de Gunicorn `(2×núcleos)+1`; aumentar tamaño de instancia | Pruebas de carga (Locust/k6); CloudWatch (servidor); Android Studio Profiler (cliente) |
| **Disponibilidad** | El servidor EC2 falla o se reinicia | Instancia única sin respaldo; sin modo offline en el cliente; BD en Neon con mayor disponibilidad que el backend | **Alto** — punto único de falla | Auto Scaling Group + Application Load Balancer con ≥2 instancias; caché local (Room) en el cliente | *Health checks* automatizados (UptimeRobot/CloudWatch Synthetics); pruebas manuales con backend caído |
| **Escalabilidad** | Crecimiento de usuarios más allá del alcance piloto inicial | S3 y Neon elásticos por diseño; backend limitado a escalabilidad vertical; cliente escalable en funcionalidades gracias a MVVM modular | **Medio-Alto** en backend / **Bajo** en cliente | Introducir ALB + Auto Scaling Group; Neon ya soporta múltiples conexiones concurrentes sin cambios adicionales | Pruebas de carga incrementales hasta punto de saturación de EC2 |
| **Seguridad** | Acceso no autorizado a la instancia o a credenciales | Credenciales en `.env` sin cifrar en el servidor; falta confirmar cifrado de "Recordarme" en cliente; HTTPS y Security Group por verificar | **Alto** — impacta cumplimiento de Ley 1581/2012 | Migrar secretos a AWS Secrets Manager; proxy inverso con TLS (Nginx + Let's Encrypt); permisos IAM mínimos por bucket; cifrado en cliente (Keystore) | AWS Trusted Advisor; revisión de Security Group; pruebas de rechazo de tráfico HTTP |
| **Mantenibilidad** | Incorporación de nuevas funcionalidades o corrección de errores | Organización modular consistente (MVVM / Blueprints + migraciones versionadas); sin pruebas automatizadas | **Medio** — buena estructura, baja cobertura de pruebas | JUnit + Compose Testing (cliente); pytest (backend); integrarlas como *gate* obligatorio en CI | Análisis estático (ktlint/detekt, flake8/black); verificación de migraciones documentadas |
| **Accesibilidad** | Uso por población con menor alfabetización digital (adultos mayores) | Se usa `contentDescription` (Jetpack Compose) en elementos interactivos como mecanismo de accesibilidad nativa; API con CORS y códigos HTTP consistentes | **Medio** | Extender `contentDescription` a la totalidad de elementos interactivos; verificar contraste de color según WCAG; documentar API con OpenAPI/Swagger | Accessibility Scanner + TalkBack (cliente); pruebas con Postman (backend) |
| **Desplegabilidad** | Publicación de una nueva versión de app o backend | CI/CD funcional (GitHub Actions) y backend contenerizado con **Docker**, pero sin *staging*, sin *rollback* automático integrado al pipeline ni *zero-downtime* | **Medio** | Integrar construcción/publicación de imágenes Docker versionadas en GitHub Actions con *rollback* por tag; ambiente de *staging* vía `docker-compose` y *branching* de Neon; distribución controlada (Google Play Internal Testing) | Revisión del historial de *workflows* en GitHub Actions; verificación post-despliegue por capa |

### 2.2 Priorización de atributos de calidad (drivers priorizados)

| Prioridad | Atributos críticos | Justificación |
|---|---|---|
| **Crítica** | Seguridad, Disponibilidad | Impactan directamente el cumplimiento legal (Ley 1581/2012) y la continuidad del servicio ante el punto único de falla identificado. |
| **Alta** | Rendimiento, Desplegabilidad | El backend es el cuello de botella del sistema y, aunque ya está contenerizado con Docker, aún falta *staging* y *rollback* automatizado para un despliegue plenamente seguro/reversible. |
| **Media** | Mantenibilidad, Escalabilidad | La base de código está bien organizada, pero falta cobertura de pruebas y capacidad de crecer más allá del alcance piloto inicial. |
| **Media-Baja** | Accesibilidad | Relevante para la inclusión de la población objetivo, pero no bloquea la operación técnica del sistema. |

---

*Documento generado a partir de "UrbanFix - Arquitectura.docx", "Informe 1" y "Informe 2" del proyecto
semestral, y los README técnicos del repositorio backend y frontend.*
