# UrbanFix — Atributos de Calidad

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Documentos previos:** [01-contexto-sistema.md](./01-contexto-sistema.md) · [02-stakeholders-drivers.md](./02-stakeholders-drivers.md)

Este documento formaliza los atributos de calidad del sistema, los prioriza con justificación
trazable a los drivers identificados en el análisis de contexto, y declara explícitamente qué
afirmaciones están verificadas y cuáles siguen siendo supuestos. Los escenarios y las mediciones
correspondientes se desarrollan en [04-escenarios-calidad.md](./04-escenarios-calidad.md).

Los escenarios no se formulan desde cero: se derivan de los requerimientos no funcionales ya
verificados del proyecto —RNF #1, que fija un tope de 90 segundos para crear un reporte, y RNF #2,
que exige el enrutamiento automático a la entidad competente— reescritos en formato de escenario
verificable.

---

## 1. Marco de referencia

Se combinan dos marcos: **ISO/IEC 25010**, modelo estándar de calidad del producto software, y
**PASS MADE**, usado en el análisis técnico previo del proyecto. Para evitar ambigüedad
terminológica se declara la correspondencia entre ambos.

| PASS MADE | ISO/IEC 25010 (característica) |
|---|---|
| Desempeño | Eficiencia de desempeño |
| Disponibilidad | Fiabilidad → Disponibilidad |
| Escalabilidad | Eficiencia de desempeño → Capacidad |
| Seguridad | Seguridad |
| Mantenibilidad | Mantenibilidad |
| Accesibilidad | Usabilidad → Accesibilidad |
| Desplegabilidad | Mantenibilidad → Capacidad de ser instalado |

---

## 2. Estado de verificación de las afirmaciones

Esta es la sección más importante del documento. El curso evalúa la distinción rigurosa entre lo
verificado y lo supuesto, y todo lo que hasta ahora proviene de documentación previa o de análisis
asistido por IA es un supuesto hasta que se confirme por inspección del repositorio o por
ejecución.

Los estados posibles son: *por verificar*, *verificado* (con evidencia enlazada), *refutado* y
*parcial*. Cada afirmación que cambie de estado debe enlazar el archivo, la captura o la corrida
que lo demuestra, dentro de `/experimentos` o como referencia a un commit específico.

| # | Afirmación sobre el sistema | Estado | Cómo se verifica | Resultado |
|---|---|---|---|---|
| 1 | El backend está contenerizado con Docker | **Verificado** | Existencia de `Dockerfile` en el repo backend y su uso efectivo en el despliegue | Confirmado mediante el uso de `docker-compose` y ejecución local exitosa. |
| 2 | El backend corre sobre EC2 `t2.micro` (1 vCPU / 1 GB) | **Refutado** | Consola de AWS; `lscpu` y `free -h` en la instancia | La instancia EC2 existió, pero la versión actual se trasladó a contenedores Docker en entorno local. |
| 3 | No existen pruebas automatizadas en backend ni cliente | **Verificado** | Búsqueda de `tests/`, `pytest.ini`, `androidTest/`, `test/` en ambos repos | Confirmada la ausencia total de pruebas unitarias o de integración. Solo existen pruebas de carga (k6). |
| 4 | Las credenciales se manejan en `.env` sin gestor de secretos | **Verificado** | Inspección del repo y del workflow de GitHub Actions | Comprobado en entorno local: las variables críticas se inyectan mediante archivo `.env`. |
| 5 | El bucket S3 no permite listado ni escritura pública | **Verificado** | Configuración de permisos del bucket; intento de acceso anónimo | Confirmado. Permite subida controlada desde la app pero bloquea listado y escritura pública. |
| 6 | La app se comunica con la API exclusivamente por HTTPS | **Refutado** | Inspección de la URL base en el cliente; prueba de rechazo de HTTP | El equipo de Android confirmó que la URL base de conexión utiliza HTTP plano, sin cifrado. |
| 7 | Las credenciales de "Recordarme" se almacenan cifradas | **Verificado** | Revisión del código: `EncryptedSharedPreferences` frente a `SharedPreferences` | Confirmado según la revisión del código en el cliente. |
| 8 | Se usa `contentDescription` en los elementos interactivos | **Verificado** | Búsqueda en el código Compose; Accessibility Scanner | Confirmado por el equipo de Android en los componentes de Jetpack Compose. |
| 9 | El backend es el cuello de botella de desempeño | **Refutado** | Prueba de carga — ver documento 04 | Pruebas con k6 (15 VUs) arrojaron 100% de éxito con p(95) < 530ms; el backend soporta la carga sin ahogarse. |
| 10 | No existe ambiente de staging | **Verificado** | Revisión de workflows y ramas en GitHub Actions | Confirmado. El repositorio actual carece de workflows de CI/CD para despliegue en staging. |

---

## 3. Matriz de atributos de calidad

Para cada atributo se define qué significa en este sistema concreto —no en abstracto—, qué lo
condiciona y qué evidencia lo respalda.

| Atributo | Significado en UrbanFix | Condicionantes actuales | Riesgo | Evidencia |
|---|---|---|---|---|
| **Seguridad** | Protección de imágenes y geolocalización de ciudadanos identificables | Ley 1581/2012; credenciales en `.env`; buckets S3; falta de HTTPS | **Alto** | Verificado (§2, filas 4–7). Riesgo elevado por tráfico HTTP plano y secretos en `.env`. |
| **Disponibilidad** | Que el ciudadano pueda enviar y consultar reportes cuando lo necesita | Ejecución local en contenedores; dependencia de BD gestionada en Neon | **Alto** | Verificado (§2, fila 2). Ausencia de alta disponibilidad al correr en entorno local/único nodo. |
| **Rendimiento** | Cumplir el RNF #1: crear un reporte en menos de 90 s de punta a punta | Capacidad de cómputo del backend; subida de imágenes a S3; latencia de Gemini | **Bajo** | Medido (doc 04). k6 demostró respuesta p(95) < 530ms bajo carga concurrente, superando el RNF #1. |
| **Desplegabilidad** | Publicar cambios sin romper el servicio de los usuarios | Despliegue manual; sin pipeline CI/CD activo ni staging automático | **Medio** | Verificado (§2, filas 1 y 10). La ausencia de staging incrementa el riesgo de fallos en producción. |
| **Mantenibilidad** | Poder cambiar el sistema con confianza | MVVM y Blueprints consistentes; migraciones versionadas; sin pruebas unitarias | **Medio** | Verificado (§2, fila 3). Las pruebas k6 evalúan carga, pero falta cobertura de unitarias para validar lógica. |
| **Escalabilidad** | Crecer más allá de la localidad piloto | Backend local contenerizado (preparado para orquestación); S3 y Neon elásticos | **Medio** | Medido (doc 04). La contenerización actual facilita un futuro escalamiento horizontal si se despliega en nube. |
| **Accesibilidad** | Uso por adultos mayores con menor alfabetización digital | Soporte nativo de Compose; atributos etiquetados correctamente | **Bajo** | Verificado (§2, fila 8). Inclusión de `contentDescription` confirmada en los elementos de UI. |

---

## 4. Priorización

Priorizar significa que algo queda abajo. Si todos los atributos resultan críticos, no se priorizó.

| Prioridad | Atributos | Justificación desde los drivers de RA1 |
|---|---|---|
| **Crítica** | Seguridad, Disponibilidad | La seguridad es obligatoria para cumplir la Ley 1581/2012 sobre protección de datos personales. La disponibilidad es vital porque los reportes sustentan un derecho de petición; si el backend cae, se bloquea el proceso legal. |
| **Alta** | Rendimiento, Desplegabilidad | El rendimiento está condicionado por el RNF #1 (tope de 90s para crear un reporte de punta a punta). La desplegabilidad es urgente para mitigar el riesgo de hacer despliegues manuales sin un ambiente de staging o pruebas automatizadas unitarias. |
| **Media** | Mantenibilidad, Escalabilidad | La mantenibilidad es necesaria para soportar el RNF #2 (enrutar dinámicamente cada reporte a la entidad competente a futuro). La escalabilidad prepara al sistema para soportar picos de concurrencia ciudadana más allá de la localidad piloto. |
| **Baja** | Accesibilidad | Aunque es una buena práctica y ya cuenta con `contentDescription`, actualmente no hay un requerimiento explícito en los drivers principales que lo posicione por encima de la estabilidad core de la arquitectura actual. |

La columna de justificación se completa con argumento propio. Cada justificación debe apuntar a un
stakeholder, una restricción o una norma concreta del documento 02, no a una preferencia técnica
del equipo.

Queda pendiente documentar el trade-off explícito: qué se sacrifica al poner Seguridad y
Disponibilidad por encima de Rendimiento. Nombrarlo evita que en la defensa parezca que no se
consideró.

---

## 5. Mapa atributo–decisión

Entregable exigido por la rúbrica. Cada fila debe poder leerse en una sola línea: qué decisión
arquitectónica responde a qué atributo, y de qué driver proviene. Cada una anticipa un ADR.

| Driver (RA1) | Atributo priorizado | Decisión arquitectónica que lo atiende | Escenario que lo verifica | ADR |
|---|---|---|---|---|
| Ley 1581/2012 obliga a proteger datos personales de ciudadanos | Seguridad | Migrar la gestión de secretos (del archivo `.env`) a un gestor seguro (ej. AWS Secrets Manager) y forzar HTTPS en toda la comunicación cliente-API. | ESC-04 | ADR-001 |
| El backend es punto único de falla y los reportes sustentan un derecho de petición | Disponibilidad | Desplegar los contenedores Docker del backend detrás de un balanceador de carga, distribuidos en múltiples zonas de disponibilidad (Multi-AZ). | ESC-02 | ADR-002 |
| RNF #1 fija un tope de 90 s para crear un reporte | Rendimiento | Descargar la carga del backend implementando la subida directa y asíncrona de imágenes al bucket S3 utilizando URLs prefirmadas (*Presigned URLs*). | ESC-01 | ADR-003 |
| RNF #2 exige enrutar cada reporte a la entidad competente | Interoperabilidad / Mantenibilidad | Implementar un modelo orientado a eventos (pub/sub) o un patrón *Strategy* para desacoplar la lógica de enrutamiento del controlador base. | ESC-06 | ADR-004 |
| No hay pruebas: cada despliegue va directo a producción | Mantenibilidad / Desplegabilidad | Implementar un pipeline de CI/CD (ej. GitHub Actions) que bloquee pases sin pruebas exitosas y automatice el despliegue inicial hacia un ambiente de *staging*. | ESC-05 | ADR-005 |

Ningún atributo de prioridad Crítica o Alta puede quedar sin al menos una fila. Si alguno no tiene
decisión asociada, o la prioridad estaba mal puesta, o falta una decisión por tomar; ambas cosas
deben decirse explícitamente.

---

## 6. Inconsistencias detectadas en la documentación previa

Registro de las contradicciones encontradas al consolidar los documentos 01 y 02. Resolverlas es
parte del trabajo de adopción del sistema base.

| # | Inconsistencia | Dónde aparece | Resolución |
|---|---|---|---|
| 1 | Docker: el análisis PASS MADE original lo lista como recomendación; los documentos 01 y 02 lo dan por implementado | `UrbanFix - Arquitectura.docx` §10 frente a `01` §3.3 y `02` §2.1 | Docker **ya está implementado**, siguiendo las indicaciones de desarrollo y la recomendación planteada inicialmente por la IA. La recomendación del diagnóstico original fue adoptada por el equipo entre la evaluación inicial y la documentación final, por lo que `01` y `02` reflejan correctamente el estado actual del sistema. |
| 2 | Modo offline: `01` §4.3 lo descarta como riesgo; `02` §2.1 lo recomienda como mejora de disponibilidad | `01` §4.3 frente a `02` §2.1 | El modo offline se descartó explícitamente como riesgo del alcance actual (§4.3), ya que no responde a la lógica de negocio del sistema. La mención en `02` §2.1 se mantiene como una **oportunidad futura de disponibilidad**, no como un requisito del alcance vigente: se deja registrada para una eventual evolución del sistema, pero no se considera pendiente ni riesgo dentro del proyecto actual. |
| 3 | Ubicación de PostgreSQL: "gestionado en Neon" frente a "alojado en AWS" | `UrbanFix - Arquitectura.docx` §9 | No es una inconsistencia real, sino una imprecisión de redacción del documento original. **Neon es el proveedor que aloja la base de datos** (PostgreSQL como servicio gestionado), mientras que la **instancia de AWS EC2 aloja la aplicación en general** (backend Flask/Gunicorn). Son dos componentes de infraestructura distintos y complementarios, no una contradicción. |
| 4 | `contentDescription`: originalmente "no confirmado"; en `02` §2.1 se afirma como estado actual | `UrbanFix - Arquitectura.docx` §10 frente a `02` §2.1 | El uso de `contentDescription` **no se había confirmado en el diagnóstico inicial** revisado por la IA, por falta de visibilidad sobre el código fuente del frontend en ese momento. Sin embargo, siempre formó parte del desarrollo del frontend como parte del atributo de accesibilidad. `02` §2.1 refleja el estado real una vez verificado con el equipo, no un cambio de comportamiento del sistema. |

---

## 7. Declaración de uso de IA

| Pregunta | Respuesta |
|---|---|
| ¿Qué herramienta se usó? | ChatGPT y Claude. |
| ¿Para qué se usó? | Revisión inicial y diagnóstico del sistema, verificación de cumplimiento semanal, sugerencias de atributos de calidad a partir de la revisión del repositorio original, y evaluación de escenarios y riesgos. |
| ¿Qué se aceptó? | Los supuestos relacionados con riesgos (en su mayoría) y con atributos de calidad. El diagnóstico inicial no requirió refutación, ya que en las siguientes etapas del proyecto se aportó mayor contexto que lo confirmó. |
| ¿Qué se modificó? | Los resultados relacionados con atributos e implementaciones, dado que en varios casos la IA no reconoció componentes ya existentes en el sistema (p. ej. Docker, `contentDescription`). Fue necesaria la intervención del equipo para agregar contexto al repositorio y a la documentación. |
| ¿Qué se rechazó? | El riesgo de compatibilidad con otros sistemas operativos, ya que no responde a la lógica de negocio original y se sale del alcance definido del proyecto. También se rechazó el riesgo por ausencia de un modo offline: aunque representa una oportunidad de crecimiento futuro del sistema, no responde a la lógica de negocio original, por lo que nunca se contempló como parte del alcance actual (se deja registrado para futuras implementaciones). |
| ¿Cuál fue la decisión humana final? | Los riesgos planteados responden al contexto real del problema, por lo que no se realizan cambios en la mayoría de los casos. Sin embargo, para la descripción del estado actual del sistema (ya documentado) fue necesaria la intervención directa del equipo de desarrollo sin uso exclusivo de IA, dado que esta no comprende el contexto en su totalidad, lo cual generaba incongruencias en las descripciones. Los componentes de estructura y composición del sistema no se han modificado con respecto a lo planteado inicialmente. |
| ¿Qué riesgo permanece? | Según el consenso entre la IA y el equipo de desarrollo, el riesgo que permanece es el del backend como posible punto único de ruptura (*single point of failure*) del sistema. |
