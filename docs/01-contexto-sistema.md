# UrbanFix — Contexto del Sistema

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura de referencia:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Fuente:** Elaboración propia a partir de "UrbanFix - Arquitectura", informes EPI 1 y 2, y READMEs técnicos del repositorio.
**Documentación original de referencia:** <https://drive.google.com/drive/folders/11YCe5JwALD1xJedVkCGfl2IMHHcSY7Er?usp=sharing>

---

## 1. Contexto del sistema

UrbanFix es una aplicación móvil nativa Android (Kotlin + Jetpack Compose) que permite a los
ciudadanos reportar problemáticas de infraestructura urbana (huecos, alumbrado público, basuras,
semáforos, hidrantes, alcantarillas, etc.) mediante fotografía, geolocalización automática y
descripción generada por inteligencia artificial (Gemini AI).

El sistema centraliza estos reportes en un backend propio (Python/Flask) que expone una API REST,
persiste la información en PostgreSQL (Neon) y almacena las imágenes en AWS S3. Las entidades
responsables del mantenimiento urbano (IDU, UAESP, Alcaldía Local, EAB) consumen esta información
geolocalizada para priorizar sus intervenciones, sin que UrbanFix reemplace sus funciones legales.

El objetivo del sistema es reducir la fricción actual de los canales institucionales (PQR, líneas
telefónicas, redes sociales) — percibidos como lentos, burocráticos y con nula trazabilidad — mediante
un flujo de reporte de máximo 6 pasos y menos de 90 segundos, con seguimiento del estado del reporte
(Nuevo → En proceso → Resuelto).

### 1.1 Vista de alto nivel (tres capas)

| Capa | Tecnología | Responsabilidad |
|---|---|---|
| **Cliente móvil** | Kotlin + Jetpack Compose (MVVM) | Captura de imagen, geolocalización, UI de reporte y seguimiento |
| **Backend / API** | Python 3.10+ / Flask (Blueprints) + SQLAlchemy | Lógica de negocio, autenticación, enrutamiento de reportes |
| **Infraestructura** | AWS EC2 (Gunicorn + systemd), AWS S3, PostgreSQL (Neon), GitHub Actions | Cómputo, almacenamiento de imágenes, persistencia, CI/CD |

### 1.2 Entorno de operación

- **Servidor de aplicación:** instancia AWS EC2 (t2.micro, Ubuntu), IP elástica fija, servicio `systemd`
  (`urbanfix.service`) corriendo bajo **Gunicorn** como servidor WSGI de producción.
- **Base de datos:** PostgreSQL gestionado como servicio en la nube por **Neon**.
- **Almacenamiento de archivos:** dos buckets de **AWS S3** (`urbanfiximagenesbucket` para imágenes de
  reportes, `urbanfixperfilimagenesbucket` para fotos de perfil).
- **Despliegue continuo:** GitHub Actions ejecuta `push → main` → conexión SSH a EC2 → `git pull` →
  `sudo systemctl restart urbanfix`.
- **Cliente:** dispositivos Android de usuarios finales (SDK 36, AGP 8.11.1), sin publicación en Google
  Play — distribución mediante *releases* del repositorio.
- **Servicios externos consumidos:** Gemini AI (`gemini-2.0-flash:generateContent`) para generación de
  descripciones, Mapbox para visualización de mapas.

---

## 2. Restricciones

- **Restricción de infraestructura:** el backend corre sobre una única instancia EC2 `t2.micro` (1 vCPU,
  1 GB RAM) sin balanceo de carga ni instancia de respaldo — constituye un punto único de falla y limita
  el escalamiento a vertical únicamente.
- **Restricción presupuestal:** inversión inicial estimada de $35.034.640 COP y costo operativo mensual
  de ~$1.016.400–$930.000 COP; el proyecto debe apoyarse en recursos gratuitos o de bajo costo (planes
  free de Neon, Figma, GitHub) por ser un prototipo académico.
- **Restricción geográfica/funcional:** el sistema se plantea como un prototipo piloto de alcance
  limitado dentro de la ciudad; no incluye integración real con sistemas oficiales del Distrito.
- **Restricción de plataforma:** el cliente se desarrolla exclusivamente para **Android** (no hay
  versión iOS); no se publica en tiendas oficiales (Google Play / App Store).
- **Restricción de datos:** no contempla almacenamiento masivo de datos ciudadanos ni manejo de
  información sensible en entornos productivos reales.
- **Restricción de gestión de reportes:** el sistema no automatiza la clasificación ni la toma de
  decisiones administrativas; la IA solo apoya la generación de descripciones, sin reemplazar la
  intervención humana ni la competencia legal de las entidades.
- **Restricción de continuidad:** no existe ambiente de *staging* separado de producción; los cambios se
  validan directamente sobre el entorno usado por los usuarios finales.
- **Restricción de pruebas:** no hay pruebas automatizadas (unitarias/integración) implementadas ni en
  el cliente ni en el backend, lo que limita la confiabilidad de cada despliegue.
- **Restricciones regulatorias:** ver sección 3.4 (marco legal aplicable).

---

## 3. Tecnologías utilizadas

### 3.1 Backend / API

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| Framework | Flask (con Blueprints) |
| ORM / migraciones | SQLAlchemy + Flask-Migrate |
| Servidor de aplicación (producción) | Gunicorn |
| Base de datos | PostgreSQL (gestionado en Neon) |
| Almacenamiento de archivos | AWS S3 |
| Cómputo | AWS EC2 (t2.micro, Ubuntu, servicio `systemd`) |
| CI/CD | GitHub Actions |
| **Contenerización** | **Docker** (backend contenerizado) |

### 3.2 Cliente móvil (Android Studio)

| Componente | Tecnología |
|---|---|
| Lenguaje | Kotlin |
| Framework UI | Jetpack Compose |
| Gestión de estado | ViewModel + State Hoisting |
| Navegación | Navigation Compose |
| Arquitectura | MVVM |
| Librerías | Coil (imágenes), Retrofit (API REST) |
| AGP / SDK | 8.11.1 / SDK 36 |
| Integraciones externas | Mapbox (mapas), Gemini AI (`gemini-2.0-flash:generateContent`) |

### 3.3 Docker en la arquitectura

El backend (Flask + Gunicorn) **ya se encuentra contenerizado con Docker**, lo que permite empaquetar la
aplicación y sus dependencias de forma reproducible e independiente del entorno del host. Esto mejora la
consistencia entre los entornos de desarrollo y producción y facilita el versionado de imágenes. Como
siguientes pasos para aprovechar mejor esta base se recomienda:

- Integrar la construcción y publicación de las imágenes Docker dentro del pipeline de GitHub Actions,
  habilitando *rollback* mediante versionado de tags de imagen.
- Usar `docker-compose` (o un orquestador ligero) para levantar entornos reproducibles de *staging*,
  aprovechando el *branching* de bases de datos de Neon.
- Aprovechar la contenerización como base para migrar de una única instancia EC2 hacia un Auto Scaling
  Group con balanceador de carga (ECS/EKS o instancias detrás de un Application Load Balancer),
  facilitando el escalamiento horizontal del backend.

### 3.4 Marco regulatorio y normativo (Colombia)

El diseño técnico y de datos de UrbanFix está condicionado por el siguiente marco legal:

| Norma | Objeto | Relevancia para UrbanFix |
|---|---|---|
| **Ley 1581 de 2012** | Régimen general de protección de datos personales | El tratamiento de geolocalización e imágenes requiere autorización previa, expresa e informada del titular; obliga a proteger credenciales y datos sensibles (cifrado, gestión de secretos). |
| **Ley 1755 de 2015** | Derecho fundamental de petición | Sustenta que los reportes generados en la app tengan respuesta obligatoria por parte de las autoridades públicas (IDU, UAESP) dentro de los términos de ley. |
| **Ley 1801 de 2016** (Código Nacional de Seguridad y Convivencia Ciudadana) | Comportamientos que afectan el espacio público | Habilita a Policía Metropolitana e inspectores a actuar frente a infracciones identificadas mediante los reportes ciudadanos. |
| **Ley 2116 de 2021** | Estatuto orgánico de Bogotá / descentralización administrativa | Delimita competencias entre la Alcaldía Local y el IDU sobre la malla vial, base del enrutamiento automático de reportes por categoría/ubicación. |
| **Ley 23 de 1982** | Derechos de autor sobre software | Protege el código (Kotlin/Python) como obra; sustenta el registro ante la DNDA. |

Estas normas, junto con las restricciones de infraestructura, determinan requisitos no funcionales
concretos: cifrado de credenciales (`EncryptedSharedPreferences`/Android Keystore, AWS Secrets Manager),
comunicación exclusivamente por HTTPS, y trazabilidad del estado del reporte para sustentar el derecho
de petición.

---

## 4. Riesgos iniciales identificados y clasificación

Se presentan dos conjuntos de riesgos iniciales: (4.1) los riesgos declarados originalmente por el
equipo en el "Informe 1 - Proyecto Semestral", y (4.2) los riesgos adicionales que emergen al observar
la arquitectura y el entorno de operación del sistema descritos en la sección 1. Ambos conjuntos se
clasifican según su tipo de valor para la arquitectura, siguiendo la siguiente definición:

- **Válido:** el riesgo aplica y es relevante para el sistema específico que se está operando.
- **Irrelevante:** el riesgo no aplica al contexto del sistema base adoptado.
- **Genérico:** el riesgo aplica a cualquier sistema de software, por lo que no aporta valor específico
  ni utilidad concreta para el proyecto.
- **Falso:** ocurre cuando se comete un error factual o de inferencia en su planteamiento.

### 4.1 Riesgos declarados en el Informe 1 (validación de mercado / gestión del proyecto)

| # | Riesgo original | Descripción | Clasificación | Justificación |
|---|---|---|---|---|
| 1 | Baja participación por parte de la ciudadanía | Los habitantes pueden no adoptar la app por desconocimiento del proyecto o falta de confianza en la propuesta. | **Válido** | Es un riesgo central para un sistema cuyo valor depende enteramente de la participación ciudadana activa (modelo de reporte crowdsourced); sin adopción, el sistema pierde su razón de ser. |
| 2 | Limitaciones técnicas en el modelo de inteligencia artificial | Depende de los datos suministrados por la ciudadanía; si son incompletos o imprecisos, se afecta la dinámica de la aplicación. | **Válido** | Aplica directamente al componente diferenciador del sistema (generación automática de descripciones vía Gemini AI a partir de imágenes de usuarios). |
| 3 | Falta de datos reales para validación | En desarrollo no hay datos prácticos de usuarios reales; existe riesgo de reportes falsos o repetidos. | **Válido** | Es específico al dominio del sistema: un canal abierto de reporte ciudadano está expuesto de forma concreta a duplicados y reportes falsos, lo cual condiciona el diseño de validación (p. ej. votos/apoyos positivos). |
| 4 | Falta de integración directa con entidades públicas | Riesgo de falta de respuesta por parte de entidades responsables (IDU, UAESP, Alcaldía) del manejo de daños reportados vía la app. | **Válido** | Relevante porque el valor del sistema depende de que el enrutamiento automático de reportes derive en una atención real por parte de terceros fuera del control técnico del equipo. |
| 5 | Fallos técnicos en la aplicación (geolocalización, tiempos de respuesta, incompatibilidad de dispositivos) | Puede provocar pérdida de información necesaria para reportes eficientes. | **Genérico** | Es un riesgo operativo común a cualquier aplicación móvil que dependa de sensores de hardware (GPS) y de red; no aporta una particularidad propia del dominio de UrbanFix más allá de "cualquier app puede fallar". |
| 6 | Limitaciones técnicas en herramientas (uso de recursos mayormente gratuitos) | Requiere más tiempo para tareas que podrían resolverse con funciones de pago, afectando el cronograma. | **Genérico** | Aplica a cualquier proyecto académico de software con presupuesto limitado; no es un riesgo propio de la arquitectura o el dominio de UrbanFix, sino de la gestión del proyecto. |

En este conjunto no se identificaron riesgos **Irrelevantes** ni **Falsos**, ya que todos corresponden a
preocupaciones reales del ciclo de vida temprano de un proyecto de este tipo.

### 4.2 Riesgos identificados al observar el sistema (arquitectura y entorno de operación)

Estos riesgos surgen directamente del análisis de la sección 1 (contexto del sistema, vista de capas y
entorno de operación) y de las tecnologías descritas en la sección 3, no del informe original.

| # | Riesgo observado en el sistema | Descripción | Clasificación | Justificación |
|---|---|---|---|---|
| 1 | Punto único de falla en el backend | El backend corre sobre una única instancia EC2 `t2.micro`, sin balanceo de carga ni instancia de respaldo (ver §1.2 y §2). | **Válido** | Observado directamente en la arquitectura descrita: si la instancia falla, toda funcionalidad dependiente de red se pierde. |
| 2 | Ausencia de ambiente de *staging* | Los cambios de backend y app se validan directamente en el entorno usado por los usuarios finales (ver §2). | **Válido** | Confirmado como restricción explícita del sistema; incrementa la probabilidad de introducir errores en producción. |
| 3 | Ausencia de pruebas automatizadas | No hay pruebas unitarias ni de integración en cliente ni backend (ver §2). | **Válido** | Verificado como restricción del sistema; reduce la confiabilidad de cada cambio desplegado vía GitHub Actions. |
| 4 | Gestión de credenciales sin cifrado centralizado | Credenciales de Neon, AWS, Gemini y Mapbox se manejan en variables de entorno (`.env`) sin un gestor de secretos. | **Válido** | Observado en el entorno de operación descrito; un acceso no autorizado a la instancia EC2 expondría todas las credenciales simultáneamente. |
| 5 | Ausencia de modo offline/caché en el cliente | El cliente móvil no tiene mecanismo de tolerancia a fallos de red ante una caída del backend. | **Válido** | Se deriva directamente de la arquitectura de tres capas: sin caché local, la app depende por completo de la disponibilidad del backend. |
| 6 | Dependencia de servicios de terceros sin *fallback* (Gemini AI, Mapbox) | Si estos servicios cambian su API, tienen indisponibilidad o alteran condiciones de uso, el sistema pierde funcionalidades clave (descripción automática, mapas). | **Válido** | Es una consecuencia directa de las integraciones declaradas en §3.2; no hay componente alterno documentado ante la falla de estos servicios. |
| 7 | Obsolescencia de dependencias/frameworks de terceros | Actualizaciones futuras de Flask, Jetpack Compose, SQLAlchemy, etc., podrían requerir refactorización. | **Genérico** | Es un riesgo de mantenimiento presente en prácticamente cualquier sistema de software con dependencias externas; no es exclusivo de la arquitectura de UrbanFix. |
| 8 | Riesgo de incompatibilidad con iOS o Windows | Posible pérdida de usuarios por no soportar otras plataformas móviles. | **Irrelevante** | No aplica al contexto del sistema base adoptado: el alcance del proyecto define explícitamente Android como única plataforma objetivo (ver §2, "Restricción de plataforma"); no es un riesgo real para el sistema tal como fue definido. |
| 9 | El sistema usa un orquestador de contenedores (Kubernetes) para el backend | Riesgo derivado de asumir que la contenerización implica orquestación automática de múltiples nodos. | **Falso** | Es un error factual: el sistema tiene el backend contenerizado con Docker, pero corre sobre una única instancia EC2 sin orquestador (Kubernetes/ECS); no existe tal componente en la arquitectura actual (ver §3.3). |

**Síntesis:** el análisis directo de la arquitectura aporta riesgos **válidos** más precisos y accionables
(#1 a #6 de la tabla 4.2) que los riesgos genéricos de gestión de proyecto ya identificados en el informe
original. Se incluyen también un ejemplo de riesgo **irrelevante** (#8) y uno **falso** (#9) para ilustrar
cómo depurar el backlog de riesgos: el primero por estar fuera del alcance definido del sistema, y el
segundo por partir de una premisa técnica incorrecta sobre la infraestructura real descrita en este
documento.

### 4.3 Riesgos descartados tras la revisión

Tras revisar los riesgos planteados en la sección 4.2, teniendo en cuenta el alcance definido del sistema, se
descartan los siguientes dos:

**Ausencia de modo offline.** Se descarta porque la lógica de negocio del sistema no contempla el
funcionamiento sin conexión: el objetivo de la aplicación es el envío y la recepción de respuestas en
tiempo real, por lo que la comunicación constante con el backend es un requisito necesario para su
funcionamiento esperado. Implementar un modo offline requeriría mecanismos adicionales de
almacenamiento local, sincronización y resolución de conflictos que no forman parte del alcance ni de
los requisitos actuales. Además, una de las funcionalidades principales del sistema (la generación de
reportes mediante inteligencia artificial) depende de la comunicación con servicios externos, por lo que
requiere conexión disponible para funcionar. La dependencia del backend es intencional y
necesaria, y la ausencia de modo offline no se considera un riesgo dentro del alcance definido para el
proyecto.

**Compatibilidad con otros sistemas operativos (iOS, Windows).** Se descarta porque el objetivo del
proyecto es desarrollar una aplicación específicamente para dispositivos Android. Desde la planificación
inicial no se contempló el desarrollo multiplataforma ni tecnologías orientadas a garantizar
compatibilidad con iOS o Windows: los requisitos, la arquitectura y las tecnologías seleccionadas están
orientados exclusivamente al ecosistema Android. En consecuencia, la incompatibilidad con estos sistemas
operativos no se considera un riesgo dentro del alcance definido para el proyecto.

---

*Documento generado a partir de "UrbanFix - Arquitectura.docx", "Informe 1" y "Informe 2" del proyecto
semestral, y los README técnicos del repositorio backend y frontend.*
