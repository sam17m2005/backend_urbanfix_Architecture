# UrbanFix — Registro Crítico de Uso de IA (Módulo 5)

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Módulo:** 5 — Semanas 9–10 · Dominio, integración y eventos
**Documentos previos:** [subdominios.md](./subdominios.md) · [responsabilidades-contextos.md](./responsabilidades-contextos.md) · [context-map.md](./context-map.md) · [decision-integracion.md](./decision-integracion.md) · [contrato-api.md](./contrato-api.md) · [eventos-candidatos.md](./eventos-candidatos.md)

> Este registro cubre el uso de IA en todos los entregables del Módulo 5. Sigue el mismo formato de
> declaración usado en [03-atributos-calidad.md](../03-atributos-calidad.md) y
> [04-escenarios-calidad.md](../04-escenarios-calidad.md).

---

## Declaración de uso de IA

| Pregunta | Respuesta |
|---|---|
| ¿Qué herramienta se usó? | Claude y Chat GPT (Afgente de arquitectura de software) |
| ¿Para qué se usó? | **Revisión del repositorio y del estado actual del sistema:** lectura del código del backend (`app/models.py`, `app/routes.py`, `app/utils.py`, `config.py`, `docker-compose.yml`) y del cliente Android (`network/`, `viewmodel/`, `screens/`) para extraer responsabilidades, relaciones y operaciones reales. **Revisión de los contratos utilizados en el sistema:** contraste entre los endpoints del backend y su uso en `ApiService.kt`, y formalización de las operaciones de mapa de reportes e inicio de sesión. **Revisión de los documentos de contexto anteriores:** contexto general de negocio y restricciones (01), stakeholders y drivers (02), atributos y escenarios de calidad (03, 04), diagramas C4 (05–07) y ADR 0001–0002, para verificar su coherencia con el código. A partir de esa revisión, la IA propuso borradores de subdominios, contextos, Context Map, comparativo de integración, contratos y eventos candidatos. |
| ¿Qué se aceptó? | La extracción de responsabilidades y relaciones con su evidencia en el código; la estructura de fichas por contexto (qué protege, qué posee, qué no posee y por qué no pertenece al vecino); el comparativo síncrono/asíncrono por criterios; la formalización en OpenAPI de las operaciones ya existentes; y la lista de eventos candidatos como insumo para auditar. |
| ¿Qué se modificó? | El equipo ajustó las propuestas al alcance real del sistema: el registro del reporte se separó del seguimiento y la atención; el subtipo del daño se mantuvo como texto descriptivo dentro del reporte; el estado del reporte lo cambia la organización a través de su funcionario; el Context Map se rehízo para mostrar responsabilidades de negocio en lugar de detalle técnico; y el contrato API se rehízo sobre operaciones reales (mapa de reportes e inicio de sesión) en lugar de un endpoint propuesto que no existía. |
| ¿Qué se rechazó? | Toda propuesta que se saliera de la lógica de negocio de UrbanFix o que agregara funcionalidades más allá de lo que abarca el sistema planteado: la canalización de reportes hacia la entidad competente; la integración con los sistemas internos de las entidades; el manejo y redireccionamiento del personal de las entidades; el historial interno de la atención; la gestión de subtipos como catálogo en el backend; reglas automáticas basadas en el conteo de denuncias; y los eventos derivados de esas funcionalidades (`ReporteCanalizadoAEntidad`, `ReporteConMayoriaDeDenuncias`). |
| ¿Qué supuesto de IA fue problemático? | La IA tomó conclusiones basadas solo en el código, sin el contexto de la aplicación. Por ejemplo, interpretó el modelo `Zona` y el RNF #2 como una responsabilidad de canalización que el sistema debía cumplir, cuando UrbanFix es un medio de reporte y visualización. También describió como "consulta de Reportes a Validación" lo que en el código es una lectura directa de la tabla `apoyos`, y propuso inicialmente un contrato para un endpoint inexistente. |
| ¿Cómo se verificó? | Contraste de cada afirmación con el archivo y la línea del código citados, en el backend y en el cliente Android; validación de la especificación OpenAPI con un validador; renderizado de los diagramas Mermaid; y revisión de cada propuesta por el equipo frente al conocimiento del negocio y del sistema. |
| ¿Cuál fue la decisión humana final? | Las decisiones de dominio, alcance y fronteras las tomó el equipo desarrollador con base en su conocimiento general del negocio y del sistema (decisiones D-1 a D-5 de [subdominios.md](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)). La IA se usó como analista de evidencia: sus propuestas se aceptaron solo cuando eran coherentes con esa lógica de negocio. |
| ¿Qué riesgo permanece? | Que alguna afirmación tomada del código no refleje el comportamiento en ejecución, porque varias no se ejecutaron: por ejemplo, si el registro de usuarios falla por `foto_perfil_url` o si eliminar un reporte con reacciones falla por la llave foránea. |

---

