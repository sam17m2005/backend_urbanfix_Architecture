# UrbanFix — Subdominios (espacio del problema)

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Módulo:** 5 — Semana 9 · Dominio y fronteras
**Documentos previos:** [01](../01-contexto-sistema.md) · [02](../02-stakeholders-drivers.md) · [03](../03-atributos-calidad.md) · [04](../04-escenarios-calidad.md) · [05](../05-c4-contexto.md) · [06](../06-c4-contenedores.md) · [07](../07-c4-componentes.md)
**Fuente:** Elaboración propia a partir del código del backend (`backend_urbanfix_Architecture`), del cliente Android (`UrbanFix_Architecture`), de los documentos 01–07 y de los ADR 0001–0002.

> Ver también [responsabilidades-contextos.md](./responsabilidades-contextos.md) para las
> responsabilidades, los contextos candidatos y la matriz de relaciones, y
> [context-map.puml](./context-map.puml) para el Context Map.

---

## 0. Cómo leer este documento

Un **subdominio** es una parte del *problema de negocio*, no del código. Por eso este documento
describe qué hace la ciudad, el ciudadano y la entidad pública, y solo después señala dónde aparece
(o no aparece) cada subdominio en el repositorio. Las fronteras de la *solución* (bounded contexts /
módulos funcionales) están en [responsabilidades-contextos.md](./responsabilidades-contextos.md).

Cada afirmación se etiqueta según su origen:

| Etiqueta | Significado |
|---|---|
| **HECHO DEL REPOSITORIO** | Verificable leyendo un archivo concreto del repositorio (se cita archivo y línea). |
| **INFERENCIA** | Conclusión razonable a partir de la evidencia, pero no escrita explícitamente en ella. |
| **INFORMACIÓN FALTANTE** | Algo que el dominio necesita y que no aparece ni en el código ni en los documentos. |

Además de esas tres etiquetas, se usa una cuarta para lo que no sale de la evidencia sino del criterio
de negocio del equipo:

| Etiqueta | Significado |
|---|---|
| **DECISIÓN DEL EQUIPO** | Definición de negocio tomada por el equipo. Se resume en la sección 5 con su consecuencia. |

> Este documento fue elaborado con apoyo de IA actuando como *analista de evidencia*. Las
> definiciones de alcance y la separación entre subdominios son **decisiones del equipo** (sección 5).

---

## 1. Dominio

**Gestión ciudadana de incidencias del espacio público urbano.**

Un ciudadano observa un daño (hueco, alumbrado, basuras, alcantarillas, etc.), lo reporta con
evidencia fotográfica y ubicación, otros ciudadanos lo respaldan o comentan, y una entidad pública
competente lo atiende y comunica su avance (`Nuevo → En proceso → Resuelto`).
Fuente: [01-contexto-sistema.md §1](../01-contexto-sistema.md) (HECHO DEL REPOSITORIO, documental).

**Alcance (DECISIÓN DEL EQUIPO):** UrbanFix es un **espacio de recopilación** de incidencias al que
las entidades públicas tienen acceso. **No** se integra con los sistemas internos de las entidades ni
gestiona sus procesos de atención. Cómo reacciona cada organización ante un reporte es un proceso
interno de esa organización; UrbanFix solo registra el estado que el funcionario declara.

El problema de negocio que se quiere resolver es la **falta de trazabilidad y la fricción** de los
canales institucionales (PQR, líneas telefónicas), en un flujo de reporte de menos de 90 s (RNF #1).

---

## 2. Mapa de subdominios

| # | Subdominio | Tipo | Pregunta de negocio que responde |
|---|---|---|---|
| SD-1 | Registro de incidencias urbanas | **Núcleo** | ¿Qué está dañado, de qué tipo y subtipo, dónde, con qué evidencia y quién lo reportó? |
| SD-2 | Seguimiento y atención institucional | **Núcleo** | ¿Qué reportes hay, dónde están, en qué estado van y qué funcionario los tomó? |
| SD-3 | Canalización a la entidad competente | **Soporte (no implementado)** | ¿Qué entidad debería ver este reporte como suyo dentro de UrbanFix? |
| SD-4 | Validación ciudadana | **Soporte** | ¿Qué tan creíble parece el reporte según la comunidad? |
| SD-5 | Organización institucional (entidades y funcionarios) | **Soporte** | ¿Qué entidades existen y qué funcionarios actúan en nombre de cada una? |
| SD-6 | Clasificación de incidencias (categoría, subtipo y estado) | **Soporte** | ¿Qué tipos y subtipos de daño y qué estados son válidos? |
| SD-7 | Identidad y acceso | **Genérico** | ¿Quién es el actor y qué rol tiene (ciudadano o funcionario)? |
| SD-8 | Almacenamiento de evidencia multimedia | **Genérico** | ¿Dónde se guardan las fotografías de reportes y perfiles? |
| SD-9 | Geolocalización y mapas | **Genérico (externo)** | ¿Dónde está el daño en el mapa? |
| SD-10 | Descripción asistida por IA | **Genérico (externo)** | ¿Cómo se redacta automáticamente la descripción del daño? |
| — | Integración con sistemas de las entidades | **Fuera de alcance** | — (DECISIÓN DEL EQUIPO, D-1) |
| — | Gestión interna de la atención en cada entidad | **Fuera de alcance** | — (DECISIÓN DEL EQUIPO, D-4) |

**Criterio de clasificación:**
- *Núcleo:* es la razón por la que UrbanFix existe frente a una PQR: recopilar incidencias de forma simple (SD-1) y hacer visible su avance (SD-2).
- *Soporte:* necesario y específico del negocio, pero no diferencial por sí mismo.
- *Genérico:* problema resuelto en cualquier sistema; conviene comprarlo o delegarlo (S3, Mapbox, Gemini, autenticación).

---

## 3. Descripción de cada subdominio

### SD-1 · Registro de incidencias urbanas — Núcleo

**Qué cubre en el negocio (DECISIÓN DEL EQUIPO, D-2):** **solo la creación** del reporte: categoría,
subtipo del daño, descripción, dirección, referencia, coordenadas y una o dos fotografías. No incluye
la visualización de reportes ni la respuesta de la entidad; eso pertenece a SD-2.

**Evidencia:**
- HECHO DEL REPOSITORIO — Entidad `Reporte` con `descripcion`, `direccion`, `referencia`, `latitud`, `longitud`, `tipo_evento`, `img_prueba_1`, `img_prueba_2`, `estado` (`app/models.py:37-56`).
- HECHO DEL REPOSITORIO — Creación con estado inicial fijo `'Nuevo'` (`app/routes.py:131`).
- HECHO DEL REPOSITORIO — RNF #1 (reporte en menos de 90 s) y escenario ESC-01 ([04-escenarios-calidad.md](../04-escenarios-calidad.md)).
- HECHO DEL REPOSITORIO — El autor también puede editar (`app/routes.py:868-914`) y eliminar su reporte, esto último solo en estado `Nuevo` o `Resuelto` (`app/routes.py:496`).
- INFERENCIA — La edición y la eliminación por el autor se ubican en SD-1 porque corrigen o retiran lo que el ciudadano registró, no responden al reporte. La regla de no eliminar un reporte `En proceso` es el punto donde SD-1 depende del estado que gestiona SD-2.

**Por qué es núcleo:** es el flujo que el producto promete simplificar frente a los canales oficiales.

### SD-2 · Seguimiento y atención institucional — Núcleo

**Qué cubre en el negocio (DECISIÓN DEL EQUIPO, D-2):** es un subdominio **separado** del registro.
Incluye todo lo que ocurre después de crear el reporte:
- **visualización:** lista general, detalle, "mis reportes" y mapa;
- **respuesta institucional:** un funcionario toma el reporte, cambia su estado y queda como responsable;
- **seguimiento ciudadano:** el ciudadano consulta el avance.

**Evidencia:**
- HECHO DEL REPOSITORIO — Consultas: `GET /reportes`, `GET /reportes/<id>`, `GET /misreportes`, `GET /reportes/geojson` (`app/routes.py:155-164, 429-518, 816-859`).
- HECHO DEL REPOSITORIO — `PUT /reportes/<id>/estado` solo acepta `Nuevo`, `En proceso`, `Resuelto` y exige el encabezado `User-Role: funcionario` (`app/routes.py:721-753`).
- HECHO DEL REPOSITORIO — El primer funcionario que cambia el estado queda en `funcionario_asignado_id` (`app/routes.py:743-744`).
- HECHO DEL REPOSITORIO — Ley 1755 de 2015 (derecho de petición) exige trazabilidad de la respuesta ([01-contexto-sistema.md §3.4](../01-contexto-sistema.md)).
- INFORMACIÓN FALTANTE — No existe historial de cambios de estado (quién, cuándo, de qué estado a cuál). Solo se guarda el estado actual.

**Límite (DECISIÓN DEL EQUIPO, D-4):** SD-2 registra el estado que declara el funcionario; **no**
modela cómo la entidad organiza internamente la atención (cuadrillas, priorización, contratación).

### SD-3 · Canalización a la entidad competente — Soporte, **no implementado**

**Qué cubre en el negocio (DECISIÓN DEL EQUIPO, D-1):** que, **dentro de UrbanFix**, cada reporte
quede visible o asociado a la entidad que debería atenderlo, según categoría, subtipo y ubicación.
**No** significa enviar el reporte a los sistemas de la entidad: el objetivo de la aplicación es ser
un espacio de recopilación al que las entidades acceden, no conectarse con sus plataformas.

**Evidencia:**
- HECHO DEL REPOSITORIO — RNF #2 y ESC-06 describen este enrutamiento como hipótesis sin medir ([04-escenarios-calidad.md ESC-06](../04-escenarios-calidad.md)).
- HECHO DEL REPOSITORIO — Existe la entidad `Zona` con `entidad_id` (`app/models.py:218-232`), pero **ninguna ruta la usa** (se importa en `app/routes.py:3` y no se referencia después).
- HECHO DEL REPOSITORIO — `Categoria` no tiene relación con `EntidadPublica` (`app/models.py:261-273`) y `Reporte` no tiene columna de entidad ni de zona (`app/models.py:37-56`).
- INFERENCIA — Hoy cualquier funcionario ve todos los reportes, y el reporte queda vinculado a una entidad solo de forma indirecta, a través del funcionario que primero cambia su estado (`Funcionario.entidad_id`).
- INFORMACIÓN FALTANTE — Reglas de correspondencia (categoría/subtipo × zona → entidad) y definición geográfica de una zona (polígono, localidad, barrio).

**Por qué soporte y no núcleo:** con la decisión D-1, el diferencial del producto es la recopilación
(SD-1) y la visibilidad del avance (SD-2). La canalización facilita que cada entidad encuentre lo
suyo, pero UrbanFix sigue cumpliendo su objetivo aunque las entidades consulten todos los reportes.

### SD-4 · Validación ciudadana — Soporte

**Qué cubre en el negocio (DECISIÓN DEL EQUIPO, D-3):** las reacciones (like/dislike) y los
comentarios de la comunidad funcionan como una **señal indirecta** de si el reporte es real.
Es una señal **informativa**: quien la lee (otros ciudadanos, el funcionario) la interpreta, pero no
dispara reglas automáticas sobre el reporte (no lo oculta, no lo prioriza, no cambia su estado).

**Evidencia:**
- HECHO DEL REPOSITORIO — `Apoyo` con `tipo` `like`/`dislike` y restricción de una reacción por actor y reporte (`app/models.py:234-251`); `Comentario` (`app/models.py:120-151`).
- HECHO DEL REPOSITORIO — Riesgo #3 del Informe 1: reportes falsos o repetidos, mitigado con votos ([01-contexto-sistema.md §4.1](../01-contexto-sistema.md)).
- HECHO DEL REPOSITORIO — El conteo de likes/dislikes solo se muestra junto al reporte (`app/models.py:61-69`); ninguna regla lo consume. Esto es **coherente** con D-3.
- INFERENCIA — Como la señal se calcula a partir de reacciones, su calidad depende de que cada reacción venga de un actor real. Hoy el `actor_id` y el `role` los declara el cliente sin autenticación (`app/routes.py:177-182`), lo que debilita la señal.

### SD-5 · Organización institucional — Soporte

**Qué cubre en el negocio (DECISIÓN DEL EQUIPO, D-4):** el catálogo de entidades públicas y la
**auto-inscripción** de sus funcionarios en la aplicación. Son los funcionarios quienes se registran
y declaran a qué entidad pertenecen. La forma en que cada organización reacciona ante un reporte es
un proceso interno suyo y queda fuera de UrbanFix.

**Evidencia:**
- HECHO DEL REPOSITORIO — `EntidadPublica` (`app/models.py:206-216`), `Funcionario.entidad_id` obligatorio (`app/models.py:167`), `Zona.entidad_id` (`app/models.py:225`).
- HECHO DEL REPOSITORIO — `POST /funcionarios` no exige ningún rol (`app/routes.py:587-610`), lo que es coherente con la auto-inscripción. La app lo expone como "registro de empresa" con una lista fija de entidades (`RegEmpresaScreen.kt:56-61` del repositorio `UrbanFix_Architecture`).
- INFERENCIA — Con la auto-inscripción, nada verifica que quien se registra como funcionario pertenezca realmente a la entidad. Como el rol `funcionario` es el único que puede cambiar el estado de un reporte (SD-2) y reacciona con la misma señal que un ciudadano (SD-4), esto afecta la confianza de ambos subdominios.
- INFORMACIÓN FALTANTE — Quién mantiene el catálogo de entidades (hoy se cargan por base de datos o por `POST /entidades`, sin control de rol).

### SD-6 · Clasificación de incidencias — Soporte

**Qué cubre en el negocio (DECISIÓN DEL EQUIPO, D-5):** la clasificación tiene **dos niveles:
categoría y subtipo**, y además los estados válidos del reporte. El subtipo es parte del negocio,
no un detalle de la app, porque **la forma de contingencia depende de él**: no se atiende igual un
hueco profundo que uno superficial.

**Evidencia:**
- HECHO DEL REPOSITORIO — `Categoria` con solo lectura expuesta (`GET /categorias`, `app/routes.py:523-530`); `EstadoReporte` con `GET /estados-reporte` (`app/routes.py:532-539`).
- HECHO DEL REPOSITORIO — Hoy el subtipo existe **solo en el cliente**: 4 subtipos por cada una de las 6 categorías, como lista fija (`ReportardosScreen.kt:196-232` del repositorio `UrbanFix_Architecture`). Llega al backend como texto libre en `tipo_evento` (`ReportViewModel.kt:245`; `app/models.py:47`).
- HECHO DEL REPOSITORIO — El cliente no consulta `GET /categorias`: tiene los ids 1–6 escritos en código (`ReportViewModel.kt:277-288`).
- HECHO DEL REPOSITORIO — Contradicción: `Reporte.estado` es un `String(50)` libre (`app/models.py:50`) y las rutas validan contra una lista fija en código (`app/routes.py:737`), en lugar de usar la tabla `estados_reporte`.
- INFERENCIA — Con D-5, el código actual queda por detrás del modelo de negocio: el backend no tiene un catálogo de subtipos ni valida que el subtipo enviado corresponda a la categoría. Un subtipo con error de escritura o en otro idioma (los textos salen de `strings.xml`) sería indistinguible de uno válido.

### SD-7 · Identidad y acceso — Genérico

**Evidencia:**
- HECHO DEL REPOSITORIO — Dos tipos de cuenta con credenciales propias: `Usuario` y `Funcionario`, cada uno con `email` y `contrasena_hash` (`app/models.py:6-35`, `154-192`).
- HECHO DEL REPOSITORIO — `POST /login` busca en ambas tablas y devuelve el rol (`app/routes.py:41-74`).
- HECHO DEL REPOSITORIO — No hay tokens: el rol y el id del actor viajan en el cuerpo o en encabezados enviados por el cliente (`app/routes.py:683-684`, `729-731`).
- INFERENCIA — Es genérico porque la autenticación no es diferencial para UrbanFix; podría delegarse a un proveedor externo.

### SD-8 · Almacenamiento de evidencia multimedia — Genérico

- HECHO DEL REPOSITORIO — Dos buckets S3 (`S3_REPORTES`, `S3_PERFILES`) y dos funciones de subida (`app/utils.py:12-73`).
- HECHO DEL REPOSITORIO — Si la subida de imagen de reporte falla, `upload_base64_to_s3` igual devuelve una URL (`app/utils.py:39-42`), lo que puede dejar reportes apuntando a imágenes inexistentes.

### SD-9 y SD-10 · Geolocalización (Mapbox) y descripción con IA (Gemini) — Genéricos externos

- HECHO DEL REPOSITORIO — Ambos se consumen desde el **cliente Android**, no desde el backend ([07-c4-componentes.md §5, corrección #3](../07-c4-componentes.md); `services/AIService.kt` del repositorio `UrbanFix_Architecture`).
- HECHO DEL REPOSITORIO — Gemini recibe **solo texto** (dirección, referencia, tipo y subtipo), no la fotografía, aunque el documento 01 diga "a partir de imágenes". Si falla, el texto del error se coloca como descripción del reporte (`ReportardosScreen.kt:245-249`).
- INFERENCIA — Quedan fuera de las fronteras del backend; se muestran en el Context Map solo como sistemas externos del cliente.

---

## 4. Relación subdominio → código actual

| Subdominio | ¿Existe en el código? | Modelos | Rutas principales |
|---|---|---|---|
| SD-1 Registro de incidencias | Sí | `Reporte` | `POST /reportes`, `PUT /reportes/<id>`, `DELETE /reportes/<id>` |
| SD-2 Seguimiento y atención | Parcial (sin historial) | `Reporte.estado`, `Reporte.funcionario_asignado_id` | `GET /reportes`, `GET /reportes/<id>`, `GET /misreportes`, `GET /reportes/geojson`, `PUT /reportes/<id>/estado` |
| SD-3 Canalización | **No** | `Zona` (sin uso) | — |
| SD-4 Validación ciudadana | Sí | `Apoyo`, `Comentario` | `/reportes/<id>/reaccion`, `/reportes/<id>/comentarios`, `/comentarios/<id>`, `/usuarios/<id>/apoyos`, `/usuarios/<id>/denuncias`, `/funcionarios/<id>/apoyos`, `/funcionarios/<id>/denuncias` |
| SD-5 Organización institucional | Sí | `EntidadPublica`, `Funcionario`, `Zona` | `/entidades`, `/funcionarios`, `/funcionarios/<id>` |
| SD-6 Clasificación | Parcial: el subtipo solo existe en el cliente | `Categoria`, `EstadoReporte`, `Reporte.tipo_evento` (texto libre) | `GET /categorias`, `GET /estados-reporte` |
| SD-7 Identidad y acceso | Sí (sin tokens) | `Usuario`, `Funcionario` | `POST /login`, `/usuarios`, `/usuarios/<id>`, `/usuarios/<id>/perfil`, `/funcionarios/<id>/perfil`, `/…/foto_perfil` |
| SD-8 Evidencia multimedia | Sí | — (`app/utils.py`) | Invocado desde reportes y foto de perfil |
| SD-9 / SD-10 Externos | Solo en el cliente | — | — |

---

## 5. Decisiones del equipo sobre el dominio

| ID | Decisión | Subdominios afectados | Consecuencia en este documento |
|---|---|---|---|
| D-1 | UrbanFix es un espacio de recopilación al que las entidades acceden. No se conecta con los sistemas de las entidades. | SD-3 | La canalización se mantiene como subdominio, pero significa asociar el reporte a la entidad **dentro de UrbanFix**. Pasa de núcleo a **soporte**. La integración con sistemas externos queda **fuera de alcance**. |
| D-2 | El registro solo crea el reporte. Seguimiento y atención es un subdominio separado. | SD-1, SD-2 | La visualización (lista, detalle, mis reportes, mapa) se movió de SD-1 a SD-2. |
| D-3 | La validación ciudadana es una señal indirecta de que el reporte es real. | SD-4 | SD-4 se mantiene como soporte. Que ninguna regla consuma el conteo deja de ser información faltante: es coherente con una señal informativa. |
| D-4 | Los funcionarios se inscriben por sí mismos. Cómo reacciona cada entidad es un proceso interno suyo. | SD-2, SD-5 | SD-2 solo registra el estado declarado. La gestión interna de la atención queda **fuera de alcance**. Queda visible el riesgo de que nada verifique la pertenencia del funcionario a la entidad. |
| D-5 | El subtipo es parte de la clasificación, porque la contingencia depende de él. | SD-6, SD-3 | SD-6 pasa a tener dos niveles (categoría → subtipo). El código actual queda por detrás: el subtipo solo existe en el cliente como texto libre. |

---

