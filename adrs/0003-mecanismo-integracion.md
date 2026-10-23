# ADR 0003 — Mantener la integración síncrona entre contextos (REL-06 / REL-07) y no introducir broker de eventos ni PgBouncer en esta etapa

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán

**Estado:** Aceptada

**Fecha:** 2026-10-16

**Documentos relacionados:** [ADR 0001](./0001-decision-estilo.md) · [ADR 0002](./0002-aislamiento-persistencia.md) · [decision-integracion.md](../docs/integracion/decision-integracion.md) · [contrato-api.md](../docs/integracion/contrato-api.md) · [context-map.md](../docs/dominio/context-map.md) · [04-escenarios-calidad.md](../docs/04-escenarios-calidad.md)

---

## Contexto

**La pregunta.** ¿Cómo se integran los contextos del backend? El caso más exigente es REL-06 / REL-07 del Context Map: Gestión de Reportes necesita mostrar el respaldo comunitario (apoyos y denuncias) que produce Validación Ciudadana, y Validación solo puede actuar sobre un reporte que existe. Es la única relación del mapa en la que dos contextos se necesitan mutuamente y en la que el negocio podría tolerar un dato ligeramente desactualizado.

**Cómo funciona hoy (hecho del repositorio).** No hay un servicio de Validación al que Reportes consulte. Al armar la respuesta de un reporte, `Reporte.to_dict()` cuenta directamente las filas de la tabla `apoyos` con dos consultas (likes y dislikes) y una tercera si conoce al actor (`app/models.py:59-83`). Al listar, eso se repite por cada reporte. Todos los contextos viven en el mismo proceso y la misma base de datos ([ADR 0001](./0001-decision-estilo.md)).

**Drivers.** Críticos: Seguridad y Disponibilidad. Altos: Rendimiento y Desplegabilidad. Medios: Mantenibilidad y Escalabilidad ([02 §2.2](../docs/02-stakeholders-drivers.md)). El proyecto parte con un solo contenedor, sin pruebas automatizadas ni monitoreo ([01](../docs/01-contexto-sistema.md)).

**Línea base (ESC-07).** `POST /login` con rampa hasta 800 usuarios virtuales, en un laptop local con el servidor de desarrollo de Werkzeug (no en producción): p95 mediano de 31,06 s y 11,11 % de error en la medición previa ([04 §5](../docs/04-escenarios-calidad.md)).

**La premisa que había que comprobar.** Los documentos anteriores atribuían esa degradación al agotamiento del pool de 15 conexiones ([ADR 0002](./0002-aislamiento-persistencia.md), [decision-integracion §3](../docs/integracion/decision-integracion.md)). Sobre esa premisa se había propuesto reforzar el camino síncrono con repositorios y PgBouncer (30 h de ingeniería estimadas). Antes de invertirlas se ejecutó el **Spike 01**, con hipótesis y criterios registrados antes de tocar código.

### Evidencia del Spike 01

Hipótesis pre-registrada: *con PgBouncer (`transaction`, 15 conexiones, igual capacidad que el pool actual) y el pool de SQLAlchemy desactivado, el p95 de `/login` baja al menos 30 % y el error queda en 5 % o menos*. Mismo equipo, mismo día, mismo k6 y mismo código en las corridas válidas; 4 corridas por brazo, se descarta la primera, se comparan las medianas de las 3 restantes.

| Métrica (mediana de 3 corridas válidas) | Línea base | Con PgBouncer |
|---|---|---|
| p95 de `http_req_duration` | 41,44 s | 40,80 s (**−1,5 %**; el criterio exigía −30 %) |
| Tasa de error | 17,94 % | 0,00 % |
| Respuestas 5xx | 254 | 0 |
| Throughput | 15,41 req/s | 12,96 req/s |
| CPU máxima del backend (100 % = 1 núcleo) | ≈ 970 % | ≈ 1.117 % |
| Conexiones máximas a Postgres | 16 | 16 |

**Veredicto: hipótesis refutada.** Lectura de los datos (observación, no prueba): PgBouncer eliminó los errores, pero no redujo la latencia, y la CPU del backend estuvo saturada en ambos brazos. El hash de la contraseña del usuario de prueba es `scrypt:32768:8:1`, costoso en CPU por cada login. El pool explicaba los errores, no la latencia.

### Alcance de la evidencia

- El spike midió `POST /login`, **no** el camino de REL-06 / REL-07 (`GET /reportes`). **No comparó integración síncrona contra asíncrona.** Su aporte es refutar la premisa del pool y mostrar que añadir infraestructura (PgBouncer, repositorios) no mejora la latencia medida.
- Medición local, un usuario de prueba, un endpoint, 3 corridas válidas por brazo (el mínimo). k6 compartió la CPU con el sistema y no se midió. Las desviaciones respecto al pre-registro están declaradas en `exp/spike-01/cambios.md` de la rama del spike.
- El throughput de esta sesión (~15 req/s) es la mitad de la medición previa (~30 req/s), por lo que solo vale la comparación entre brazos medidos hoy, no contra la medición vieja.

---

## Alternativas consideradas

### A. Integración síncrona directa (estado actual)
Reportes consulta el respaldo comunitario en el momento, dentro del mismo proceso y la misma base de datos.

### B. Integración asíncrona por eventos
Validación publica `ReaccionRegistrada` por un broker y Reportes mantiene su propia copia del conteo.

### C. Síncrona reforzada con aislamiento de persistencia (ADR 0002)
Igual que A, pero con una capa de repositorios como único acceso a datos y PgBouncer con un pool lógico por dominio. Es la alternativa cuya premisa puso a prueba el Spike 01.

### Comparación

| Criterio | A · Síncrona directa | B · Eventos asíncronos | C · Síncrona + PgBouncer y repositorios |
|---|---|---|---|
| Dependencia temporal | Alta: la tabla `apoyos` debe responder en ese instante | Baja: Reportes muestra su copia aunque Validación esté atrasada | Alta, igual que A |
| Acoplamiento | Alto: `to_dict()` conoce la tabla `Apoyo`; ciclo REL-06 / REL-07 | Bajo: solo se conoce el formato del evento | Medio: el repositorio oculta las tablas, pero el ciclo persiste |
| Consistencia | Inmediata | Eventual (segundos); el negocio lo tolera por ser señal informativa ([D-3](../docs/dominio/subdominios.md)) | Inmediata |
| Disponibilidad | Una falla al contar falla la respuesta completa; hoy comparten proceso y pool | Mostrar reportes no depende de Validación, pero suma el broker como nuevo punto de falla | Aísla fallos por pool, pero suma PgBouncer como punto de falla |
| Complejidad | Ninguna adicional | Alta: broker, consumidor, idempotencia, reintentos; sin pruebas automatizadas que los cubran | Media-alta: ~30 h estimadas ([ADR 0002](./0002-aislamiento-persistencia.md)) |
| Observabilidad | Un error se ve en la misma respuesta | Peor: un evento perdido o duplicado no genera error visible | Peor que A: un componente más sin monitoreo |
| Evidencia medida | Sin medición de `GET /reportes` | Ninguna | **Spike 01:** p95 −1,5 %; errores 17,9 % → 0 % |
| Reversibilidad | Alta: es el estado actual | Media: exige retirar broker, consumidor y copia del conteo | Media: PgBouncer en minutos; repositorios ~16 h ([ADR 0002](./0002-aislamiento-persistencia.md)) |

---

## Decisión

Se **mantiene la integración síncrona directa (alternativa A)** para todas las relaciones entre contextos, incluidas REL-06 y REL-07. **No** se introduce un broker de eventos y **no** se adopta PgBouncer ni la capa de repositorios del ADR 0002 como parte del mecanismo de integración en esta etapa.

**Por qué:**

1. **B no se justifica con la evidencia actual.** Todos los contextos comparten proceso y base de datos ([ADR 0001](./0001-decision-estilo.md)). B exige un broker cuyos costos (complejidad, observabilidad, desplegabilidad) recaen en los puntos más débiles del proyecto, y no existe ninguna medición que muestre que el acoplamiento entre Reportes y Validación cause un problema ([decision-integracion §3](../docs/integracion/decision-integracion.md)). Que el negocio tolere la consistencia eventual hace a B *posible*, no *necesaria*.
2. **C quedó sin su premisa.** El Spike 01 refutó que el agotamiento del pool sea la causa de la latencia de ESC-07: el p95 casi no cambió (−1,5 % frente a −30 % exigido). Con esa evidencia no se justifica invertir ~30 h en repositorios y PgBouncer para mejorar la latencia.
3. **El mecanismo de integración no es la causa observada del problema de capacidad.** La CPU del backend se saturó en ambos brazos; el costo por login (scrypt) es una causa candidata. Cambiar la forma de integrar los contextos no la ataca.

**Qué NO decide este ADR.** No resuelve ESC-07 (el p95 sigue en ~41 s bajo 800 VUs en el entorno medido). No descarta PgBouncer como mitigación de errores bajo carga, solo no lo adopta ahora (ver Consecuencias). No demuestra que la integración síncrona sea mejor que la asíncrona: la decisión se apoya en el análisis del repositorio y en la ausencia de evidencia a favor de B.

---

## Consecuencias

**Positivas**
- Sin cambios de código ni infraestructura nuevos: sigue un solo proceso, un solo contenedor y un solo punto de despliegue.
- Un error de integración se ve en la misma petición; no hay colas ni eventos que perder, duplicar o monitorear.
- Se evita invertir ~30 h en una solución cuya premisa quedó refutada.
- La decisión es reversible sin pérdida de datos: el conteo de reacciones siempre se puede recalcular desde `apoyos`.

**Negativas**
- **El acoplamiento persiste:** `Reporte.to_dict()` sigue conociendo la tabla `Apoyo` y el ciclo REL-06 / REL-07 no se rompe.
- **Rendimiento del listado sin medir:** cada reporte cuenta apoyos con 2 o 3 consultas (patrón N+1) y no hay medición de `GET /reportes`.
- **ESC-07 sigue sin resolverse.** La degradación bajo 800 VUs permanece.
- **Se renuncia, por ahora, a la eliminación de errores** que mostró PgBouncer (5xx 254 → 0; error 17,9 % → 0 %). No se interpreta como mejora de capacidad (el p95 no cambió), pero reduciría fallos visibles para el usuario.
- Un fallo al contar reacciones sigue haciendo fallar la respuesta completa del reporte.

---

## Supuestos y condiciones de revisión

| Supuesto | Condición de revisión | Qué pasa si no se cumple |
|---|---|---|
| Contar reacciones por reporte no degrada el listado (no hay medición de `GET /reportes`) | Una medición de `GET /reportes` bajo carga muestra degradación atribuible al conteo | Se reconsidera B para REL-06, o un conteo desnormalizado dentro del mismo proceso |
| Validación Ciudadana permanece en el mismo proceso y la misma base de datos | Validación se despliega por separado del resto del backend | Se reconsidera B; la integración síncrona entre procesos agregaría latencia y acoplamiento temporal |
| La degradación de ESC-07 no depende del mecanismo de integración (evidencia: Spike 01, local) | Una medición en el entorno real (EC2 + Neon) o un spike posterior muestra otra causa | Se reabre la evaluación de C o de otras alternativas con la evidencia nueva |
| Los errores bajo carga son aceptables para el piloto sin PgBouncer | La tasa de error en producción supera el umbral definido en ESC-07 (≤ 5 %) | Se reevalúa PgBouncer como mitigación de errores, ya sin la premisa de latencia |

---

## Reversibilidad

**Alta.** La decisión conserva el estado actual del sistema; no hay nada que deshacer para mantenerla. Migrar luego a B o a C no pierde datos. Pasar a B exigiría un broker, un consumidor, un campo o tabla de conteo, idempotencia ante eventos duplicados y retirar la lectura directa de `apoyos`. Pasar a C cuesta minutos para PgBouncer (cambiar `DATABASE_URL`) y unas 16 h para los repositorios, según el [ADR 0002](./0002-aislamiento-persistencia.md). El Spike 01 vive en su rama `spike/01-pgbouncer-login`, aislado y sin mezclar con `main`.

---

## Correcciones a documentos previos

Con la evidencia del Spike 01 conviene corregir, para que el repositorio no se contradiga:

1. **[ADR 0002](./0002-aislamiento-persistencia.md), Contexto:** afirma que el error y la latencia de ESC-07 se deben al agotamiento del pool. El Spike 01 solo respalda eso para los errores, no para la latencia.
2. **[decision-integracion.md §3](../docs/integracion/decision-integracion.md):** una de las razones de la decisión repite esa atribución al pool. La decisión se sostiene por las demás razones; esta debe matizarse.
3. **[04-escenarios-calidad.md §5](../docs/04-escenarios-calidad.md) y ADR 0002:** dicen que el servidor de desarrollo corre "sin `threaded=True`" y procesa de forma esencialmente secuencial. En Flask 3.1.2, `app.run()` activa `threaded=True` por defecto, por lo que esa explicación no se sostiene tal como está escrita.

---

## Trazabilidad

| Elemento | Ubicación en el repositorio |
|---|---|
| Pre-registro de hipótesis, criterios y alcance | `experimentos/00-preregistro.md` en `main` (commit `288837f`) |
| Rama del spike y registro de cambios | rama `spike/01-pgbouncer-login` · `exp/spike-01/cambios.md` (en la rama) (commits `93934f3`, `9df270c`) |
| Resultados crudos y resumen | rama del spike: `exp/spike-01/resultados/` · `exp/spike-01/resultados/resumen.md` (commit `f54b26b`) |
| Veredicto y decisión del spike | rama del spike: `exp/spike-01/veredicto.md` (commit `a53966c`) |
| Condiciones de medición | rama del spike: `exp/spike-01/resultados/condiciones-baseline.txt` · `condiciones-spike.txt` |
| Contexto del dominio y relaciones | `docs/dominio/context-map.md` (REL-06, REL-07) |
| Comparación síncrona vs. asíncrona | `docs/integracion/decision-integracion.md` |
| Contratos API (mapa de reportes, inicio de sesión) | `docs/integracion/contrato-api.md` |
| Eventos candidatos | `docs/integracion/eventos-candidatos.md` |
| Drivers y escenarios de calidad | `docs/02-stakeholders-drivers.md` · `docs/04-escenarios-calidad.md` (ESC-07) |
| Decisiones anteriores | `adrs/0001-decision-estilo.md` · `adrs/0002-aislamiento-persistencia.md` |

En `main` la carpeta de experimentos se llama `experimentos/`; la rama del spike conserva la ruta `exp/spike-01/` con la que se ejecutó (se creó antes del renombre).

---

## Registro crítico del borrador inicial

El borrador previo de este ADR se descartó y se rehízo por estas razones:

- Declaraba que el Spike 01 **respaldaba** la decisión y que la causa de la degradación era el pool y el servidor de desarrollo. El spike refutó la hipótesis del pool.
- Citaba una referencia de trazabilidad que no existe en el repositorio (un commit y una ruta `spike-01-integracion` inexistentes).
- Fijaba un umbral de revisión de 1.500 ms de p95 sin ningún dato que lo sustente.
- Se conserva de ese borrador la idea central (integración síncrona, sin broker) y la estructura de alternativas y consecuencias.

