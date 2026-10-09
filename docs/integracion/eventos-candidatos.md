# UrbanFix — Eventos Candidatos

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Módulo:** 5 — Semana 10 · Diseño mediante eventos
**Documentos previos:** [subdominios.md](./subdominios.md) · [responsabilidades-contextos.md](./responsabilidades-contextos.md) · [context-map.md](./context-map.md) · [decision-integracion.md](./decision-integracion.md) · [contrato-api.md](./contrato-api.md)
**Fuente:** Elaboración propia a partir de las responsabilidades de dominio, el Context Map, las decisiones del equipo (D-1 a D-5) y el código del backend (`backend_urbanfix_Architecture`) y del cliente Android (`UrbanFix_Architecture`).

> Este documento es un **análisis**: lista hechos del dominio que podrían comunicarse como eventos y
> deja la clasificación final al equipo. Puede coexistir con la decisión de integrar por API
> ([decision-integracion.md](./decision-integracion.md)); no implica adoptar eventos.

---

## 1. Método

**Insumos usados:** responsabilidades de cada contexto, flujos reales de la app, Context Map,
operaciones que cambian el estado del dominio en `app/routes.py` y el modelo en `app/models.py`.

**Reglas aplicadas al generar candidatos:**
- Un evento es un **hecho que ya ocurrió**, con significado para el negocio, nombrado en pasado.
- No se convierten automáticamente en eventos las operaciones CRUD, los clics de la interfaz ni los
  detalles técnicos. Los que se descartaron por esa razón están en la sección 4.
- Se respetan las decisiones del equipo: UrbanFix no canaliza reportes ni se integra con los
  sistemas de las entidades (D-1, D-4), y el respaldo comunitario es una señal informativa (D-3).

**Nivel de confianza de la IA:**

| Nivel | Significado |
|---|---|
| **A** | Respaldado directamente por evidencia: existe una operación o regla en el código o en los documentos que produce ese hecho. |
| **B** | Inferencia plausible: el hecho ocurre en el sistema, pero no está claro que otro contexto necesite conocerlo. |
| **C** | Especulativo: el hecho no existe hoy en el código o contradice una decisión del equipo. |


---

## 2. API frente a evento en UrbanFix

| | API (pregunta en tiempo real) | Evento (hecho ya ocurrido) |
|---|---|---|
| **Ejemplo** | "Gestión de Reportes, dame los reportes para el mapa." | "El reporte 42 fue marcado como Resuelto." |
| **Quién toma la iniciativa** | El consumidor, que espera la respuesta. | El productor, que avisa; los interesados reaccionan cuando pueden. |
| **Hoy en UrbanFix** | Todas las integraciones ([contrato-api.md](./contrato-api.md)). | Ninguna: no hay broker ni publicación de eventos. |

---

## 3. Eventos candidatos

### 3.1 Ciclo de vida del reporte (productor: Gestión de Reportes)

| ID | Evento | Hecho que representa | Evidencia | Posibles interesados | Información mínima | Confianza |
|---|---|---|---|---|---|---|
| EV-01 | `ReporteCreado` | Un ciudadano registró un daño con su foto, ubicación y clasificación. | `POST /reportes` crea el reporte con estado `Nuevo` (`app/routes.py:83-153`, línea 131). | Validación Ciudadana (habilita apoyos y comentarios); mapa; funcionarios que consultan reportes. | reporteId, categoría, subtipo, coordenadas, fecha, creadorId | **A** |
| EV-02 | `ReporteTomadoEnAtencion` | La entidad, a través de su funcionario, marcó el reporte como `En proceso`. | `PUT /reportes/{id}/estado` con `En proceso`, solo rol funcionario (`app/routes.py:721-753`). | Ciudadano creador (seguimiento); ciudadanos que lo apoyaron. | reporteId, funcionarioId, entidadId, fecha | **A** |
| EV-03 | `ReporteResuelto` | La entidad declaró resuelto el daño. | Mismo endpoint con `Resuelto` (`app/routes.py:737`). | Ciudadano creador; ciudadanos que lo apoyaron o denunciaron. | reporteId, funcionarioId, entidadId, fecha | **A** |
| EV-04 | `FuncionarioAsignadoAReporte` | Un funcionario quedó registrado como responsable del reporte. | El primer funcionario que cambia el estado queda en `funcionario_asignado_id` (`app/routes.py:743-744`). | Ciudadano creador. | reporteId, funcionarioId, entidadId | **A** |
| EV-05 | `ReporteDevueltoANuevo` | Un reporte en proceso o resuelto volvió al estado `Nuevo`. | El endpoint acepta `Nuevo` como estado destino sin restricción de origen (`app/routes.py:737`). No hay regla de negocio documentada sobre esa transición. | Ciudadano creador. | reporteId, estado anterior, funcionarioId, fecha | **B** |
| EV-06 | `ReporteCorregidoPorCiudadano` | El autor cambió la descripción, la ubicación o las fotos de su reporte. | `PUT /reportes/{id}` (`app/routes.py:868-914`); la app lo usa en "editar reporte". | Funcionario que lo atiende, si ya está `En proceso`. | reporteId, campos cambiados, fecha | **B** |
| EV-07 | `ReporteRetiradoPorCiudadano` | El autor retiró su reporte. | `DELETE /reportes/{id}`, solo en `Nuevo` o `Resuelto` (`app/routes.py:489-507`). | Validación Ciudadana (sus apoyos y comentarios quedarían sin reporte). | reporteId, estado al retirarlo, fecha | **B** |

### 3.2 Respaldo comunitario (productor: Validación Ciudadana)

| ID | Evento | Hecho que representa | Evidencia | Posibles interesados | Información mínima | Confianza |
|---|---|---|---|---|---|---|
| EV-08 | `ReporteApoyado` | Un actor respaldó un reporte (like). | `POST /reportes/{id}/reaccion` con `like` (`app/routes.py:168-246`). | Gestión de Reportes (conteo que muestra, REL-06). | reporteId, actorId, rol, fecha | **A** |
| EV-09 | `ReporteDenunciado` | Un actor cuestionó un reporte (dislike). | Mismo endpoint con `dislike`. | Gestión de Reportes (conteo, REL-06). | reporteId, actorId, rol, fecha | **A** |
| EV-10 | `ReaccionRetirada` | Un actor quitó su apoyo o su denuncia. | `DELETE /reportes/{id}/reaccion` (`app/routes.py:248-280`). | Gestión de Reportes (conteo). | reporteId, actorId, rol, tipo retirado | **A** |
| EV-11 | `ReaccionCambiada` | Un actor cambió su apoyo por una denuncia o al revés. | El mismo `POST` actualiza la reacción existente (`app/routes.py:214-218`). | Gestión de Reportes (conteo). | reporteId, actorId, tipo anterior, tipo nuevo | **B** |
| EV-12 | `ReporteComentado` | Alguien dejó un comentario sobre un reporte. | `POST /reportes/{id}/comentarios` (`app/routes.py:541-562`). | Ciudadano creador; funcionario que lo atiende. | reporteId, comentarioId, autorId, fecha | **A** |
| EV-13 | `FuncionarioComentoReporte` | Un funcionario respondió públicamente en un reporte. | La insignia "verificado" distingue comentarios de funcionarios (`app/models.py:138`). | Ciudadano creador. | reporteId, comentarioId, funcionarioId, entidadId | **B** |
| EV-14 | `ReporteConMayoriaDeDenuncias` | Un reporte superó un umbral de denuncias frente a apoyos. | Ninguna: no existe umbral ni regla que use el conteo. Contradice D-3 (la señal es informativa). | Funcionarios. | reporteId, apoyos, denuncias | **C** |

### 3.3 Identidad y organización institucional (productores: Identidad y Acceso en EV-15 y EV-18; Gestión Institucional en EV-16, EV-17 y EV-19; Catálogos de Clasificación en EV-20)

| ID | Evento | Hecho que representa | Evidencia | Posibles interesados | Información mínima | Confianza |
|---|---|---|---|---|---|---|
| EV-15 | `CiudadanoRegistrado` | Un ciudadano creó su cuenta. | `POST /usuarios` (`app/routes.py:16-35`). | Ningún otro contexto lo usa hoy. | usuarioId, fecha | **B** |
| EV-16 | `FuncionarioInscritoEnEntidad` | Un funcionario se inscribió declarando su entidad. | `POST /funcionarios` con `entidad_id` (`app/routes.py:587-610`); auto-inscripción (D-4). | Identidad y Acceso (rol funcionario). | funcionarioId, entidadId, fecha | **B** |
| EV-17 | `EntidadPublicaRegistrada` | Se agregó una entidad al catálogo. | `POST /entidades` (`app/routes.py:565-583`). La app usa una lista fija y no la consulta. | Pantalla de inscripción de funcionarios. | entidadId, nombre | **B** |
| EV-18 | `CuentaEliminada` | Un ciudadano o funcionario eliminó su cuenta. | `DELETE /usuarios/{id}` y `DELETE /funcionarios/{id}` (`app/routes.py:658-671`). | Gestión de Reportes (reportes de ese creador); Validación (sus reacciones y comentarios). | actorId, rol, fecha | **B** |
| EV-19 | `FuncionarioCambioDeEntidad` | Un funcionario pasó a representar otra entidad. | Ninguna: `PUT /funcionarios/{id}` solo cambia nombre y contraseña. | Gestión de Reportes (reportes asignados). | funcionarioId, entidad anterior, entidad nueva | **C** |
| EV-20 | `CategoriaAgregada` | Se habilitó una nueva categoría de daño. | Ninguna: no hay operación para crear categorías; la app las tiene fijas. | Gestión de Reportes; app. | categoriaId, nombre | **C** |

### 3.4 Candidatos que contradicen el alcance (productores: Gestión Institucional en EV-21; Gestión de Reportes en EV-22)

| ID | Evento | Hecho que representa | Por qué se lista | Confianza |
|---|---|---|---|---|
| EV-21 | `ReporteCanalizadoAEntidad` | El reporte se asignó a la entidad competente. | Aparece en RNF #2 y ESC-06, pero la canalización está fuera de alcance (D-1). | **C** |
| EV-22 | `ReporteDuplicadoDetectado` | Se identificó que un reporte repite otro. | El riesgo de reportes repetidos está en el Informe 1 ([01 §4.1](../01-contexto-sistema.md)), pero no existe ninguna detección. | **C** |

---

## 4. Descartados antes de proponer (no son eventos de dominio)

Se listan para dejar constancia del filtro aplicado; no entran en la tabla de candidatos.

| Propuesta descartada | Tipo | Por qué no es un evento de dominio |
|---|---|---|
| `BotonReportarPresionado`, `MapaAbierto`, `FiltroDeMapaAplicado` | Interfaz | Describen interacciones de pantalla; ningún contexto necesita conocerlas. |
| `SesionIniciada` | Técnico | Autenticarse no cambia nada del dominio; es una consulta (contrato B de [contrato-api.md](./contrato-api.md)). |
| `ImagenSubidaAS3` | Técnico | Es un paso interno de la creación del reporte; el hecho de negocio es `ReporteCreado`. |
| `DescripcionGeneradaPorIA` | Técnico | Ocurre en la app antes de enviar el reporte; el backend no se entera. |
| `PerfilActualizado`, `FotoDePerfilCambiada` | CRUD | Cambios de datos personales sin efecto en otros contextos. |
| `ComentarioEditado`, `ComentarioEliminado` | CRUD | Correcciones de texto sin consecuencias para otros contextos. |
| `ReportesConsultados`, `MapaSolicitado` | Consulta | Leer datos no produce un hecho nuevo. |

---

## 5. Observaciones para la auditoría

La IA no decide qué eventos adoptar. Estas observaciones son insumo para la clasificación del equipo.

- **Posibles redundancias:**
  - EV-04 (`FuncionarioAsignadoAReporte`) ocurre en el mismo momento que EV-02 (`ReporteTomadoEnAtencion`) cuando es el primer cambio de estado; puede ser un dato de EV-02 y no un evento propio.
  - EV-11 (`ReaccionCambiada`) puede expresarse como EV-10 seguido de EV-08 o EV-09.
  - EV-13 (`FuncionarioComentoReporte`) es un caso particular de EV-12 (`ReporteComentado`).
- **Eventos sin interesado claro:** EV-15, EV-17 y, en menor medida, EV-06 ocurren en el sistema, pero ningún otro contexto necesita reaccionar a ellos hoy.
- **Contradicción en el código relacionada con EV-07 y EV-18:** el modelo no define borrado en cascada (`app/models.py`) y la migración no crea restricciones propias. Si un reporte tiene apoyos o comentarios, eliminarlo podría fallar por la llave foránea. Falta verificarlo ejecutando el borrado.
- **Eventos que dependen de decisiones del equipo:** EV-14 contradice D-3 y EV-21 contradice D-1. Se listan solo para que su rechazo quede registrado.
- **Coherencia con la integración elegida:** ningún candidato obliga a cambiar la decisión síncrona de [decision-integracion.md](./decision-integracion.md). Los de la sección 3.2 son los que corresponden a la relación REL-06 analizada allí.

---

