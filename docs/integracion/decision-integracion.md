# UrbanFix — Decisión de Integración: Síncrono vs. Asíncrono

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Módulo:** 5 — Semana 9 · Dominio y fronteras
**Documentos previos:** [subdominios.md](./subdominios.md) · [responsabilidades-contextos.md](./responsabilidades-contextos.md) · [context-map.md](./context-map.md) · [ADR 0001](../../adrs/0001-decision-estilo.md) · [ADR 0002](../../adrs/0002-aislamiento-persistencia.md)
**Fuente:** Elaboración propia a partir del Context Map, del código del backend (`backend_urbanfix_Architecture`) y del cliente Android (`UrbanFix_Architecture`), y de los ADR 0001–0002.

> Ver también [context-map.md](./context-map.md) para las relaciones entre contextos que se
> discuten aquí (identificadores `REL-xx`).

---

## 1. Pregunta de integración

**¿Cómo se entera Gestión de Reportes del respaldo comunitario (apoyos y denuncias) que produce
Validación Ciudadana?**

**Cómo funciona hoy (HECHO DEL REPOSITORIO).** No existe un módulo de Validación al que Reportes
le pregunte. Cada vez que el backend arma la respuesta de un reporte, el propio modelo `Reporte`
cuenta directamente las filas de la tabla `apoyos` con dos consultas SQL (likes y dislikes) y, si
recibe el id y el rol del actor, hace una tercera para saber cómo reaccionó
(`Reporte.to_dict()`, `app/models.py:59-83`). Al listar reportes eso se repite por cada uno. Es
síncrono, pero como lectura directa de la tabla de otro contexto sobre la base compartida, no como
una consulta entre contextos.

En la app, cuando el ciudadano reacciona desde la lista, el contador se actualiza en pantalla de
inmediato sin esperar al backend, y solo se revierte si la petición falla
(`android:viewmodel/VerReportesViewModel.kt:59-95`). Desde el detalle, en cambio, la app vuelve a
pedir el reporte para obtener los contadores nuevos (`android:viewmodel/EditarReporteViewModel.kt:110-128`).

Se elige esta relación (REL-06 / REL-07) porque es la única del mapa en la que dos contextos se
necesitan mutuamente, y la única en la que el negocio podría aceptar un dato ligeramente
desactualizado. Las demás relaciones (quién creó el reporte, si el actor es funcionario, qué
categoría es válida) son consultas que deben responderse en el momento: sin ellas no se puede crear
ni mostrar el reporte.

---

## 2. Comparativo

Cada criterio se analiza solo con evidencia del repositorio (código, documentos 01–07 y ADR 0001–0002).

| Criterio | A — Síncrono (consulta en el momento) | B — Asíncrono (eventos) |
|---|---|---|
| **Mecanismo** | Al armar cada reporte se cuentan sus apoyos y denuncias. Es lo que existe hoy, como lectura directa de la tabla `apoyos`. | Validación publica `ReaccionRegistrada` y Reportes mantiene su propia copia del conteo. |
| **Dependencia temporal** | Alta: para mostrar un reporte, la tabla `apoyos` tiene que responder en ese instante. Si esa consulta se demora, se demora todo el listado. | Baja: Reportes muestra su copia aunque Validación esté caída o atrasada. |
| **Acoplamiento** | Alto: `Reporte.to_dict()` conoce la tabla y los campos de `Apoyo` (`app/models.py:61-82`), y Validación necesita el reporte (REL-07). Ciclo entre ambos. | Bajo: Reportes solo conoce el formato del evento. Se rompe el ciclo REL-06 / REL-07. |
| **Consistencia** | Inmediata: el conteo del backend siempre coincide con las reacciones guardadas. | Eventual: durante unos segundos el conteo puede no incluir la última reacción. El negocio lo tolera porque es una señal informativa ([D-3](./subdominios.md#5-decisiones-del-equipo-sobre-el-dominio)), y la app ya muestra un conteo local antes de confirmar. |
| **Disponibilidad** | Una falla al contar hace fallar la respuesta del reporte completo. Hoy ambos comparten el mismo proceso y el mismo pool de 15 conexiones ([ADR 0002](../../adrs/0002-aislamiento-persistencia.md)), así que fallan juntos de todos modos. | Mostrar reportes no depende de Validación. Pero se agrega el broker como nuevo punto de falla en un backend que ya es punto único de falla ([01 §4.2](../01-contexto-sistema.md)). |
| **Complejidad** | Ninguna adicional: es el código actual. | Alta para el equipo y el piloto: broker, nueva tabla o campo de conteo, consumidor, idempotencia ante eventos duplicados y reintentos. Sin pruebas automatizadas para cubrirlo ([01 §2](../01-contexto-sistema.md)). |
| **Observabilidad** | Todo ocurre en una petición: un error se ve en la misma respuesta. Hoy los errores solo se registran con `print()` (`app/routes.py`). | Peor con las herramientas actuales: un evento perdido o duplicado no produce ningún error visible y no hay trazas ni monitoreo de colas. |
| **Impacto en atributos registrados** | *Rendimiento:* tres consultas por reporte al listar (N+1); no está medido. *Mantenibilidad:* sin cambios. *Desplegabilidad:* sin cambios. | *Rendimiento:* listar sería más barato (se lee un campo). *Disponibilidad:* mejora el aislamiento, pero suma un componente. *Desplegabilidad* y *mantenibilidad:* empeoran (un servicio más que desplegar y probar). |
| **Reversibilidad** | Alta: es el estado actual, y pasar a B después no pierde datos porque el conteo siempre se puede recalcular desde `apoyos`. | Media: quitar el broker es posible y el conteo se recalcula desde `apoyos`, pero exige retirar consumidor, eventos y la copia del conteo. |
| **Supuestos no verificados** | Que contar reacciones por cada reporte no degrada el listado: **no hay medición** de `GET /reportes`. | Que el broker cabe en la infraestructura y el presupuesto del piloto; que el retraso real sería de segundos; que el equipo puede operarlo. **Nada de esto está probado.** |

---

## 3. Decisión del equipo

**Integración síncrona (alternativa A)** para todas las relaciones entre contextos, incluida
REL-06 / REL-07.

**Por qué:**
- Todos los contextos viven en el mismo proceso y la misma base de datos ([ADR 0001](../../adrs/0001-decision-estilo.md)). Integrarlos por eventos obligaría a introducir un broker cuyo costo de operación no se justifica para un piloto.
- El único beneficio real de la alternativa B es desacoplar Reportes de Validación, y hoy no hay ninguna medición que muestre que ese acoplamiento cause un problema.
- B mejora la dependencia temporal, el acoplamiento y la disponibilidad de esta relación, pero a costa de complejidad, observabilidad y desplegabilidad, que hoy son los puntos débiles del proyecto (sin pruebas automatizadas, sin monitoreo, un solo contenedor).
- La medición de línea base (ESC-07) atribuye la degradación al agotamiento del pool de conexiones, no al conteo de reacciones. Eso lo aborda el [ADR 0002](../../adrs/0002-aislamiento-persistencia.md), no un cambio de integración.
- Que el negocio tolere la consistencia eventual en esta relación hace que B sea **posible**, no **necesaria**. "Asíncrono es mejor" no es una regla universal.

**Condición de revisión:** reconsiderar la alternativa B para REL-06 si una medición muestra que
listar reportes se degrada por el conteo de reacciones, o si Validación Ciudadana llega a desplegarse
por separado del resto del backend.

---
