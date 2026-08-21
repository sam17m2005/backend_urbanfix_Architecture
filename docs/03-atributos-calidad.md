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
| 1 | El backend está contenerizado con Docker | Por verificar | Existencia de `Dockerfile` en el repo backend y su uso efectivo en el despliegue | |
| 2 | El backend corre sobre EC2 `t2.micro` (1 vCPU / 1 GB) | Por verificar | Consola de AWS; `lscpu` y `free -h` en la instancia | |
| 3 | No existen pruebas automatizadas en backend ni cliente | Por verificar | Búsqueda de `tests/`, `pytest.ini`, `androidTest/`, `test/` en ambos repos | |
| 4 | Las credenciales se manejan en `.env` sin gestor de secretos | Por verificar | Inspección del repo y del workflow de GitHub Actions | |
| 5 | El bucket S3 no permite listado ni escritura pública | Por verificar | Configuración de permisos del bucket; intento de acceso anónimo | |
| 6 | La app se comunica con la API exclusivamente por HTTPS | Por verificar | Inspección de la URL base en el cliente; prueba de rechazo de HTTP | |
| 7 | Las credenciales de "Recordarme" se almacenan cifradas | Por verificar | Revisión del código: `EncryptedSharedPreferences` frente a `SharedPreferences` | |
| 8 | Se usa `contentDescription` en los elementos interactivos | Por verificar | Búsqueda en el código Compose; Accessibility Scanner | |
| 9 | El backend es el cuello de botella de desempeño | Por medir | Prueba de carga — ver documento 04 | |
| 10 | No existe ambiente de staging | Por verificar | Revisión de workflows y ramas en GitHub Actions | |

---

## 3. Matriz de atributos de calidad

Para cada atributo se define qué significa en este sistema concreto —no en abstracto—, qué lo
condiciona y qué evidencia lo respalda.

| Atributo | Significado en UrbanFix | Condicionantes actuales | Riesgo | Evidencia |
|---|---|---|---|---|
| **Seguridad** | Protección de imágenes y geolocalización de ciudadanos identificables | Ley 1581/2012; credenciales en `.env`; buckets S3 | Alto | Por verificar (§2, filas 4–7) |
| **Disponibilidad** | Que el ciudadano pueda enviar y consultar reportes cuando lo necesita | Instancia EC2 única sin respaldo; BD gestionada en Neon | Alto | Por verificar (§2, fila 2) |
| **Rendimiento** | Cumplir el RNF #1: crear un reporte en menos de 90 s de punta a punta | Capacidad de cómputo del backend; subida de imágenes a S3; latencia de Gemini | Alto | Por medir (doc 04) |
| **Desplegabilidad** | Publicar cambios sin romper el servicio de los usuarios | CI/CD funcional; sin staging ni rollback automático | Medio | Por verificar (§2, filas 1 y 10) |
| **Mantenibilidad** | Poder cambiar el sistema con confianza | MVVM y Blueprints consistentes; migraciones versionadas; sin pruebas | Medio | Por verificar (§2, fila 3) |
| **Escalabilidad** | Crecer más allá de la localidad piloto | Escalamiento solo vertical en backend; S3 y Neon elásticos | Medio | Por medir (doc 04) |
| **Accesibilidad** | Uso por adultos mayores con menor alfabetización digital | Soporte nativo de Compose, implementación por confirmar | Medio | Por verificar (§2, fila 8) |

---

## 4. Priorización

Priorizar significa que algo queda abajo. Si todos los atributos resultan críticos, no se priorizó.

| Prioridad | Atributos | Justificación desde los drivers de RA1 |
|---|---|---|
| **Crítica** | Seguridad, Disponibilidad | |
| **Alta** | Rendimiento, Desplegabilidad | |
| **Media** | Mantenibilidad, Escalabilidad | |
| **Baja** | Accesibilidad | |

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
| Ley 1581/2012 obliga a proteger datos personales de ciudadanos | Seguridad | | ESC-04 | ADR-00_ |
| El backend es punto único de falla y los reportes sustentan un derecho de petición | Disponibilidad | | ESC-02 | ADR-00_ |
| RNF #1 fija un tope de 90 s para crear un reporte | Rendimiento | | ESC-01 | ADR-00_ |
| RNF #2 exige enrutar cada reporte a la entidad competente | Interoperabilidad / Mantenibilidad | | ESC-06 | ADR-00_ |
| No hay pruebas: cada despliegue va directo a producción | Mantenibilidad / Desplegabilidad | | ESC-05 | ADR-00_ |

Ningún atributo de prioridad Crítica o Alta puede quedar sin al menos una fila. Si alguno no tiene
decisión asociada, o la prioridad estaba mal puesta, o falta una decisión por tomar; ambas cosas
deben decirse explícitamente.

---

## 6. Inconsistencias detectadas en la documentación previa

Registro de las contradicciones encontradas al consolidar los documentos 01 y 02. Resolverlas es
parte del trabajo de adopción del sistema base.

| # | Inconsistencia | Dónde aparece | Resolución |
|---|---|---|---|
| 1 | Docker: el análisis PASS MADE original lo lista como recomendación; los documentos 01 y 02 lo dan por implementado | `UrbanFix - Arquitectura.docx` §10 frente a `01` §3.3 y `02` §2.1 | |
| 2 | Modo offline: `01` §4.3 lo descarta como riesgo; `02` §2.1 lo recomienda como mejora de disponibilidad | `01` §4.3 frente a `02` §2.1 | |
| 3 | Ubicación de PostgreSQL: "gestionado en Neon" frente a "alojado en AWS" | `UrbanFix - Arquitectura.docx` §9 | |
| 4 | `contentDescription`: originalmente "no confirmado"; en `02` §2.1 se afirma como estado actual | `UrbanFix - Arquitectura.docx` §10 frente a `02` §2.1 | |

---

## 7. Declaración de uso de IA

| Pregunta | Respuesta |
|---|---|
| ¿Qué herramienta se usó? | |
| ¿Para qué se usó? | |
| ¿Qué se aceptó? | |
| ¿Qué se modificó? | |
| ¿Qué se rechazó? | |
| ¿Qué supuesto de IA fue problemático? | |
| ¿Cómo se verificó? | |
| ¿Cuál fue la decisión humana final? | |
| ¿Qué riesgo permanece? | |
