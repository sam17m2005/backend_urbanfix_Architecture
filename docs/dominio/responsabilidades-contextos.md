# UrbanFix — Responsabilidades de los Contextos

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Módulo:** 5 — Semana 9 · Dominio y fronteras
**Documentos previos:** [01](../01-contexto-sistema.md) · [02](../02-stakeholders-drivers.md) · [03](../03-atributos-calidad.md) · [04](../04-escenarios-calidad.md) · [05](../05-c4-contexto.md) · [06](../06-c4-contenedores.md) · [07](../07-c4-componentes.md) · [ADR 0001](../../adrs/0001-decision-estilo.md) · [ADR 0002](../../adrs/0002-aislamiento-persistencia.md)
**Fuente:** Elaboración propia a partir del código del backend (`backend_urbanfix_Architecture`), del cliente Android (`UrbanFix_Architecture`), de los documentos 01–07 y de los ADR 0001–0002.

> Ver también [subdominios.md](./subdominios.md) para los subdominios y las decisiones del equipo
> sobre el dominio, y [context-map.puml](./context-map.puml) para el Context Map.

---

## 1. Propósito del documento

[subdominios.md](./subdominios.md) describe el **problema**: qué necesita el negocio. Este documento
describe la **solución**: qué contexto del backend se hace cargo de cada necesidad, qué responsabilidad
protege y dónde termina su frontera.

Cada contexto se presenta con la misma estructura:

| Campo | Qué responde |
|---|---|
| **Subdominio que sirve** | Qué necesidad del negocio cubre (SD-x de [subdominios.md](./subdominios.md)). |
| **Responsabilidad que protege** | La regla o el significado que solo este contexto puede cambiar. |
| **Responsabilidades** | Qué hace el contexto, en verbos de negocio. |
| **Posee** | Conceptos y datos de los que es dueño. |
| **No posee** | Conceptos que usa o referencia, pero que pertenecen a otro contexto. |
| **Por qué no pertenece al vecino** | La razón de la frontera con cada contexto cercano. |
| **Evidencia** | Dónde aparece hoy en el código. |
| **Tensión abierta** | Lo que el código actual contradice o lo que falta decidir. |

**Sobre el estado actual (HECHO DEL REPOSITORIO):** todo el backend corre en un único proceso Flask
con una base de datos PostgreSQL compartida ([ADR 0001](../../adrs/0001-decision-estilo.md)). Por eso
estas fronteras son hoy **lógicas**: no hay servicios separados, eventos ni APIs internas, y varios
contextos leen directamente tablas de otros. El [ADR 0002](../../adrs/0002-aislamiento-persistencia.md)
propone materializar parte de estas fronteras con repositorios por dominio.

Las rutas del cliente Android se citan con el prefijo `android:` y son relativas a
`app/src/main/java/com/example/urbanfix/` del repositorio `UrbanFix_Architecture`.

---

## 2. Vista general

| Contexto | Tipo | Subdominio que sirve | Responsabilidad que protege |
|---|---|---|---|
| **BC-1 · Identidad y Acceso** | Genérico | SD-7 | Saber quién es el actor y con qué rol actúa. |
| **BC-2 · Gestión de Reportes** | Núcleo | SD-1, SD-2 | El reporte y su ciclo de vida: cómo se crea, qué estado tiene y quién lo atiende. |
| **BC-3 · Validación Ciudadana** | Soporte | SD-4 | La señal comunitaria sobre si un reporte es real. |
| **BC-4 · Gestión Institucional** | Soporte | SD-5 | Qué entidades existen y qué funcionarios actúan en nombre de cada una. |
| **BC-5 · Catálogos de Clasificación** | Soporte | SD-6 | Qué categorías y estados son válidos. |

No son contextos:

| Elemento | Por qué no es un contexto |
|---|---|
| Almacenamiento de evidencia (S3, `app/utils.py`) — SD-8 | No tiene lenguaje de negocio propio. Es un adaptador técnico que usan BC-1 (fotos de perfil) y BC-2 (fotos del reporte). |
| Mapbox y Gemini — SD-9, SD-10 | Los consume el cliente Android directamente, no el backend (`android:services/AIService.kt`; [07 §5](../07-c4-componentes.md)). |
| Integración con sistemas de las entidades | Fuera de alcance por decisión del equipo ([subdominios.md, D-1](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)). |
| Canalización y gestión del personal de las entidades | UrbanFix es un medio de reporte y visualización. Decidir qué entidad atiende un reporte, a qué funcionario se dirige o cómo se registra internamente la gestión corresponde al sistema interno de cada entidad. |

---

## 3. Fichas de contexto

### BC-1 · Identidad y Acceso — *genérico*

**Subdominio que sirve:** SD-7 Identidad y acceso.

**Responsabilidad que protege:** saber **quién es el actor y con qué rol actúa** (ciudadano o
funcionario). Es el único contexto que conoce credenciales.

**Responsabilidades:**
- Registrar la cuenta de un ciudadano.
- Autenticar a un actor y devolver su rol.
- Consultar, actualizar y eliminar el perfil propio, incluida la foto de perfil.
- Autorizar acciones según el rol del actor.

**Posee:** cuenta, credencial (`email`, `contrasena_hash`), rol, perfil y foto de perfil.

**No posee:** reportes, reacciones ni comentarios; la adscripción del funcionario a una entidad
(cargo, legajo, entidad).

**Por qué no pertenece al vecino:**
- *Frente a BC-4:* BC-1 responde "¿esta persona es quien dice ser?"; BC-4 responde "¿a qué entidad
  representa?". Un cambio en la forma de iniciar sesión no debería tocar el catálogo de entidades, y
  una reorganización de entidades no debería tocar las credenciales.
- *Frente a BC-2 y BC-3:* esos contextos necesitan saber **quién** actúa, pero no **cómo** se
  autenticó. Solo reciben un identificador y un rol.

**Evidencia:**
- `Usuario` y `Funcionario` con `email` y `contrasena_hash` (`app/models.py:6-35`, `154-192`).
- `POST /usuarios` (`app/routes.py:16-35`); `POST /login` busca en ambas tablas y devuelve `role` (`app/routes.py:41-74`).
- Perfil y foto: `app/routes.py:77-80`, `370-427`, `621-671`, `756-811`.

**Tensión abierta:**
- No hay tokens. El rol y el id del actor los declara el cliente en el cuerpo o en encabezados (`app/routes.py:177-182`, `729-731`), así que BC-1 no protege realmente su responsabilidad: cualquier contexto confía en lo que dice el cliente.
- `Funcionario` mezcla credenciales (BC-1) con adscripción (BC-4) en una misma tabla. El ADR 0002 lo asigna a dos repositorios distintos (`auth_repository` y `entidades_repository`).
- `Usuario.foto_perfil_url` es obligatoria (`app/models.py:15`) pero `POST /usuarios` no la envía. Falta verificar si el registro falla.

---

### BC-2 · Gestión de Reportes — *núcleo*

**Subdominios que sirve:** SD-1 Registro de incidencias y SD-2 Seguimiento y atención institucional.

**Responsabilidad que protege:** el **reporte y su ciclo de vida visible**: con qué datos se crea,
en qué estado está y qué funcionario lo tomó. El estado lo cambia la organización responsable, a
través de su funcionario; ningún otro contexto puede cambiarlo.

**Responsabilidades:**
- *Registro (SD-1):* crear el reporte con categoría, subtipo (texto descriptivo), descripción, dirección, referencia, coordenadas y una o dos fotografías; permitir al autor editarlo o retirarlo.
- *Seguimiento (SD-2):* listar reportes, mostrar su detalle, mostrar "mis reportes" y el mapa.
- *Atención (SD-2):* permitir que la organización, a través de su funcionario, cambie el estado a `En proceso` y `Resuelto`, y registrar a ese funcionario como responsable.
- Aplicar las reglas del ciclo de vida: todo reporte nace `Nuevo`; un reporte `En proceso` no se puede eliminar.

**Posee:** Reporte, ubicación, evidencia (URLs de las fotos), descripción, subtipo (texto
descriptivo), estado actual, funcionario asignado (como referencia).

**No posee:** datos personales del ciudadano (solo su id), conteo de reacciones y comentarios
(BC-3), definición de categorías y estados válidos (BC-5), datos de la entidad (BC-4), el registro
interno de la gestión que hace cada entidad.

**Por qué no pertenece al vecino:**
- *Frente a BC-3:* un like o un comentario no cambia el reporte. Por decisión del equipo, la
  validación ciudadana es una señal informativa, no una regla sobre el reporte
  ([subdominios.md, D-3](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)). Si
  estuvieran juntos, cambiar cómo se cuentan las reacciones obligaría a tocar el núcleo.
- *Frente a BC-4:* BC-2 sabe **qué** funcionario tomó el reporte; BC-4 sabe **a qué entidad**
  pertenece ese funcionario. El proceso interno de atención de cada entidad, incluido el historial
  de su gestión, queda en el sistema interno de la entidad y fuera de UrbanFix
  ([D-4](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)).
- *Frente a BC-5:* BC-2 **usa** una categoría y un estado; BC-5 **define** cuáles existen. Agregar
  una categoría nueva no debería requerir cambiar la lógica del reporte.

**Evidencia:**
- `Reporte` (`app/models.py:37-56`).
- Creación con estado `'Nuevo'` (`app/routes.py:83-153`, línea 131); edición (`app/routes.py:868-914`); eliminación solo en `Nuevo` o `Resuelto` (`app/routes.py:489-507`, línea 496).
- Consultas: `app/routes.py:155-164`, `429-518`, `816-859`.
- Cambio de estado con rol `funcionario` y asignación del primer funcionario (`app/routes.py:721-753`).

**Tensión abierta:**
- **Registro y seguimiento en un mismo contexto.** El equipo decidió que en el problema son subdominios distintos ([D-2](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)). Aquí se mantienen en un solo contexto porque ambos operan sobre el mismo `Reporte` y el estado es la frontera entre los dos (el registro no puede eliminar un reporte que el seguimiento puso `En proceso`). Separarlos exigiría decidir quién es dueño del estado.
- Los estados válidos están escritos en código (`app/routes.py:737`) y no salen de BC-5.
- `Reporte.to_dict()` lee reacciones, creador y categoría de otros contextos (`app/models.py:59-117`). La vista del reporte depende de BC-1, BC-3 y BC-5.

---

### BC-3 · Validación Ciudadana — *soporte*

**Subdominio que sirve:** SD-4 Validación ciudadana.

**Responsabilidad que protege:** la **señal comunitaria** sobre si un reporte es real, construida
con reacciones (like/dislike) y comentarios. Protege la regla "un actor, una reacción por reporte".

**Responsabilidades:**
- Registrar, cambiar o retirar la reacción de un actor sobre un reporte.
- Listar los reportes que un actor apoyó (like) o denunció (dislike).
- Publicar, editar y borrar comentarios sobre un reporte.

**Posee:** reacción (`Apoyo`, con tipo `like`/`dislike`), comentario, la regla de unicidad de la
reacción.

**No posee:** el reporte (solo su id), la identidad del autor (solo id y rol), el estado del reporte.

**Por qué no pertenece al vecino:**
- *Frente a BC-2:* la señal se lee junto al reporte, pero no lo modifica. Un reporte puede
  atenderse aunque tenga muchos dislikes, y reaccionar a un reporte no cambia su estado.
- *Frente a BC-1:* BC-3 necesita saber quién reacciona para evitar reacciones duplicadas, pero no
  cómo se autenticó.

**Evidencia:**
- `Apoyo` con restricción `uq_usuario_reporte` y `uq_funcionario_reporte` (`app/models.py:234-259`); `Comentario` (`app/models.py:120-151`).
- Reacciones: `app/routes.py:168-280`; listas por actor: `app/routes.py:284-366`; comentarios: `app/routes.py:541-562`, `674-719`.
- En la app, "Mis denuncias" son los reportes con dislike (`android res/values/strings.xml:499-501`).

**Tensión abierta:**
- La señal es tan confiable como el actor que reacciona, y hoy el actor lo declara el cliente sin autenticación.
- Editar y borrar comentarios no verifica que lo haga el autor (`app/routes.py:705`, `715`).

---

### BC-4 · Gestión Institucional — *soporte*

**Subdominio que sirve:** SD-5 Organización institucional.

**Responsabilidad que protege:** **qué entidades existen y qué funcionarios actúan en nombre de
cada una.** UrbanFix es un medio de reporte y visualización: BC-4 no canaliza reportes, no se conecta
con los sistemas de las entidades ni gestiona o redirige a su personal
([D-1, D-4](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)).

**Responsabilidades:**
- Mantener el catálogo de entidades públicas.
- Inscribir funcionarios y su adscripción (entidad, cargo, legajo). La inscripción la hace el propio funcionario.
- Mostrar a qué entidad pertenece un funcionario (por ejemplo, en su perfil).

**Posee:** entidad pública, adscripción del funcionario.

**No posee:** credenciales del funcionario (BC-1), reportes (BC-2), categorías (BC-5).

**Por qué no pertenece al vecino:**
- *Frente a BC-1:* que un funcionario cambie de entidad o de cargo es un hecho institucional, no un
  cambio de credenciales.
- *Frente a BC-2:* el reporte solo necesita saber qué funcionario lo tomó. Que una entidad
  cambie de nombre o que un funcionario cambie de entidad no debería cambiar la lógica del reporte.

**Evidencia:**
- `EntidadPublica` (`app/models.py:206-216`); `Funcionario.entidad_id` (`app/models.py:167`).
- `GET/POST /entidades` (`app/routes.py:565-583`); `POST/GET /funcionarios`, `PUT/DELETE /funcionarios/<id>` (`app/routes.py:587-671`).
- Registro de funcionarios en la app como "registro de empresa" (`android:screens/RegEmpresaScreen.kt:51-61`).

**Tensión abierta:**
- El modelo `Zona` (`app/models.py:218-232`) existe pero ninguna ruta lo usa. No cumple ninguna función en el alcance actual.
- Con la auto-inscripción, nada verifica que quien se registra como funcionario pertenezca a la entidad que declara.
- La app tiene la lista de entidades fija en código (UAESP, EAAB, UMV, IDU, Bomberos) y no consulta `GET /entidades` (`android:screens/RegEmpresaScreen.kt:56-61`).

---

### BC-5 · Catálogos de Clasificación — *soporte*

**Subdominio que sirve:** SD-6 Clasificación de incidencias.

**Responsabilidad que protege:** **qué categorías y estados son válidos.** El subtipo del daño no
se gestiona aquí: se guarda en el reporte como texto plano que el ciudadano y el funcionario
entienden, lo que es suficiente para la lógica actual
([D-5](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)).

**Responsabilidades:**
- Publicar las categorías de daño.
- Publicar los estados válidos de un reporte.

**Posee:** categoría, estado de reporte (`EstadoReporte`).

**No posee:** los reportes concretos (BC-2), el subtipo de cada reporte (BC-2), las reglas de
transición de estado (BC-2).

**Por qué no pertenece al vecino:**
- *Frente a BC-2:* el catálogo cambia por razones distintas al reporte (por ejemplo, agregar una
  categoría nueva no cambia cómo se crea ni se atiende un reporte).

**Evidencia:**
- `Categoria` y `GET /categorias` (`app/models.py:261-273`; `app/routes.py:523-530`).
- `EstadoReporte` y `GET /estados-reporte` (`app/models.py:194-204`; `app/routes.py:532-539`).
- El subtipo lo elige el ciudadano en la app (`android:screens/ReportardosScreen.kt:196-232`) y llega como texto en `Reporte.tipo_evento` (`app/models.py:47`).

**Tensión abierta:**
- La app no consulta `GET /categorias`: tiene los ids 1–6 escritos en código (`android:viewmodel/ReportViewModel.kt:277-288`).
- BC-2 no usa la tabla `estados_reporte`: valida los estados con una lista en código (`app/routes.py:737`).
- Alternativa a considerar: absorber BC-5 dentro de BC-2, ya que hoy solo tiene dos consultas de lectura y su único consumidor en el backend es BC-2.

---

## 4. Relaciones entre contextos

Cada relación justifica una flecha del [Context Map](./context-map.puml). *Downstream* es el
contexto que depende; *upstream* es el que provee.

| ID | Downstream → Upstream | Qué se intercambia | Por qué existe | Estado |
|---|---|---|---|---|
| REL-01 | BC-2 → BC-1 | id y nombre del creador del reporte | El reporte necesita saber quién lo creó; la identidad es de BC-1 (`app/models.py:54`, `92-94`). | Confirmada |
| REL-02 | BC-2 → BC-1 | rol e id del actor que cambia el estado | Solo un funcionario puede cambiar el estado (`app/routes.py:730-734`). El rol llega en encabezados sin verificar. | Confirmada, sin autenticación real |
| REL-03 | BC-2 → BC-4 | id del funcionario asignado | El reporte registra quién lo tomó (`app/models.py:56`; `app/routes.py:743-744`). | Confirmada |
| REL-04 | BC-2 → BC-5 | id y nombre de la categoría | El reporte se clasifica con el catálogo (`app/models.py:55`, `87-88`). | Confirmada |
| REL-06 | BC-2 → BC-3 | conteo de likes/dislikes y reacción del actor | La vista del reporte muestra la señal ciudadana (`app/models.py:61-82`). | Confirmada; el núcleo depende de un contexto de soporte |
| REL-07 | BC-3 → BC-2 | id del reporte | Una reacción o comentario siempre es sobre un reporte (`app/models.py:129`, `245`). | Confirmada; forma un ciclo con REL-06 |
| REL-08 | BC-3 → BC-1 | id y rol del actor; nombre del autor | Para aplicar "una reacción por actor" y mostrar el autor (`app/routes.py:193-201`; `app/models.py:133`). | Confirmada |
| REL-09 | BC-3 → BC-4 | ¿el autor es funcionario? | Para la insignia "verificado" (`app/models.py:138`). | Confirmada |
| REL-10 | BC-1 ↔ BC-4 | modelo `Funcionario` compartido | Credencial y adscripción viven en la misma tabla (`app/routes.py:51`, `66-74`). | Confirmada; modelo compartido |
| REL-15 | Cliente → Backend | todas las operaciones | API REST síncrona sobre HTTP plano, sin contrato publicado (`android:network/ApiService.kt`, `RetrofitInstance.kt:8`). | Confirmada |
| REL-16 | Cliente → Gemini / Mapbox | descripción por IA (solo texto); mapas | Los servicios externos se llaman desde el dispositivo (`android:services/AIService.kt`). | Confirmada |
| REL-17 | Cliente → BC-5 / BC-4 | ids de categorías y entidades | La app tiene los catálogos escritos en código en lugar de consultarlos (`android:viewmodel/ReportViewModel.kt:277-288`; `android:screens/RegEmpresaScreen.kt:56-61`). | Confirmada; catálogo duplicado |

**Lectura de las relaciones:**
- Todas las relaciones confirmadas son hoy **llamadas en memoria sobre una base de datos compartida**. Las flechas indican dependencia de significado, no llamadas por red.
- **BC-2 depende de todos los demás.** Es esperable en el núcleo, pero la dependencia hacia BC-3 (REL-06) es inversa a lo que sugiere el dominio: la señal ciudadana no debería ser necesaria para que el reporte exista.
- **El ciclo REL-06 / REL-07** entre BC-2 y BC-3 es la relación que más dificulta evolucionar ambos contextos por separado.

---

## 5. Registro de uso de IA

| Pregunta | Respuesta |
|---|---|
| ¿Qué se pidió a la IA? | Extraer responsabilidades con evidencia, construir la matriz de relaciones y auditar el diseño modular previo, sin decidir los contextos definitivos (dos prompts del curso). |
| ¿Qué propuso? | Cinco contextos candidatos, un adaptador técnico y las relaciones de la sección 4. |
| ¿Qué decidió el equipo? | El alcance y la separación de subdominios (decisiones D-1 a D-5 de [subdominios.md](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)), que se usaron para justificar las fronteras de este documento. |
| ¿Se contrastó con otro análisis? | Sí, con un análisis generado por otra sesión de IA a partir de la documentación y de `routes.py`. Las diferencias se resolvieron leyendo el código del backend y del cliente. |
| ¿Qué debe verificar el equipo? | Ejecutar `POST /usuarios` para confirmar si falla por `foto_perfil_url`. |
| ¿Qué se aceptó / rechazó / modificó? | Se rechazó cualquier conclusión basada solamente en el código que ignorara el contexto de la aplicación, como asignar al sistema responsabilidades de manejo y redireccionamiento del personal de las entidades públicas (canalización de reportes a la entidad competente, historial interno de la gestión). Ese no es el foco del sistema: UrbanFix es un medio de reporte y visualización, y cada entidad gestiona la atención en su propio sistema interno. |

---

*Documento elaborado a partir del código fuente de los repositorios backend (`backend_urbanfix_Architecture`)
y frontend (`UrbanFix_Architecture`), los documentos 01–07 y los ADR 0001–0002 del proyecto, con apoyo
de IA como analista de evidencia y decisiones de dominio tomadas por el equipo.*
