# ADR 0004 — No distribuir el backend: mantener el monolito por capas en un solo despliegue y crecer escalando el monolito, no partiéndolo

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán

**Estado:** Propuesta — pendiente del veredicto del Mini-comité Técnico 2 (ver la sección final)

**Fecha:** 2026-10-23

**Documentos relacionados:** [ADR 0001](./0001-decision-estilo.md) · [ADR 0002](./0002-aislamiento-persistencia.md) · [ADR 0003](./0003-mecanismo-integracion.md) · [crecimiento.md](../experimentos/crecimiento.md) · [tactica-resiliencia.md](../experimentos/tactica-resiliencia.md) · [matriz-fallos.md](../docs/arquitectura/matriz-fallos.md) · [matriz-resiliencia.md](../docs/arquitectura/matriz-resiliencia.md) · [fitness-function.md](../docs/arquitectura/fitness-function.md) · [context-map.md](../docs/dominio/context-map.md) · [01-contexto-sistema.md](../docs/01-contexto-sistema.md)

---

## Contexto

**La pregunta.** ¿Conviene separar el backend de UrbanFix en procesos o servicios independientes (distribuirlo), o mantener el monolito por capas del [ADR 0001](./0001-decision-estilo.md)? ¿Cuánto costaría cada opción, contando infraestructura, operación y coordinación del equipo?

**Cómo es el sistema hoy (hecho del repositorio).**

- Un solo proceso Flask con un único Blueprint (`app/routes.py`, 913 líneas y 30 rutas) y un único `app/models.py`. Las capas son lógicas, no físicas.
- Todos los contextos del [Context Map](../docs/dominio/context-map.md) (Reportes, Identidad, Validación, Institucional y Catálogos) comparten proceso, CPU, pool de 15 conexiones y base de datos.
- Las únicas fronteras de red son PostgreSQL y S3 ([matriz de fallos §1](../docs/arquitectura/matriz-fallos.md)).
- El backend **no guarda estado de sesión** en memoria: no hay `session`, JWT ni `flask_login` (comentarios en `routes.py:683` y `:729`). Eso permite, en principio, correr varias copias idénticas detrás de un balanceador.
- Montaje medido: Docker local con `python3 app.py` (Werkzeug, `debug=True`). Montaje de producción según `deploy.yml`: EC2 + Gunicorn + `systemd` + Neon. **Gunicorn no está en `requirements.txt`** y ese montaje no se ha medido.

**Drivers.** Críticos: Seguridad y Disponibilidad. Altos: Rendimiento y Desplegabilidad. Medios: Mantenibilidad y Escalabilidad ([02 §2.2](../docs/02-stakeholders-drivers.md)). Restricciones: prototipo académico con presupuesto que exige recursos gratuitos o de bajo costo, sin *staging* ni monitoreo, y un equipo de tres personas ([01 §2](../docs/01-contexto-sistema.md)).

### Evidencia empírica disponible

**1. Experimento de crecimiento S11** ([crecimiento.md](../experimentos/crecimiento.md)): `POST /login` en escalones de VUs constantes, 3 corridas válidas, plan pre-registrado en el commit `dc29ec9`.

| VUs | p95 | Error | Logins OK/s | CPU total del equipo |
|---|---|---|---|---|
| 1 | 309 ms | 0 % | 3,2 | 37 % |
| 10 | 731 ms | 0 % | 15,9 | 99 % |
| 25 | 1.984 ms | 0 % | 16,4 | 100 % |
| 100 | 15.078 ms | 0 % | 11,9 | 100 % |
| 200 | 29.128 ms | 2,79 % | 12,2 | 100 % |
| 400 | 38.052 ms | 23,83 % | 10,9 | 100 % |

- **Punto de degradación** (p95 > 1 s): 25 VUs.
- **Meseta de capacidad:** ≈ 16 logins/s desde 10–25 VUs.
- **Punto de quiebre** (error > 5 %): 400 VUs.
- k6 usó menos del 1 % de la CPU, así que **el instrumento no limitó la medición**.
- Ley de cola del sistema cerrado: la latencia medida coincide con *usuarios ÷ capacidad − pausa* (0,21 / 0,35 / 0,53 / 1,42 / 3,29 s calculados frente a 0,21 / 0,35 / 0,52 / 1,40 / 3,20 s medidos). Desde ~10 VUs el sistema no procesa más de ~16 logins/s y el resto espera en cola.

**2. Spike 01** ([tactica-resiliencia.md](../experimentos/tactica-resiliencia.md), [ADR 0003](./0003-mecanismo-integracion.md)). Con PgBouncer el error bajó de 17,94 % a 0 %, pero el p95 solo bajó un 1,5 % (41,44 s → 40,80 s), con la CPU saturada en ambos brazos. **El pool explicaba los errores, no la latencia.**

**3. Matriz de fallos.** Los fallos de mayor consecuencia (F-01 pool, F-02 CPU, F-03 BD y F-12 proceso) se propagan por **recursos compartidos**, no por la red. Los más graves por invisibles (F-05 y F-07, falsos verdes de S3) ocurren **dentro** de un contexto y no tienen relación con la topología.

**Lectura que sostiene este ADR** (inferencia, no demostración). El primer recurso que se agota es la **CPU que consume cada login** (hash `scrypt:32768:8:1`, unos 0,21 s de servicio por login con un usuario). Partir el sistema en servicios **no reduce el trabajo de CPU por login**; solo lo traslada a otro proceso. Lo que sube la capacidad es dar **más CPU** a ese trabajo, y eso se logra sin distribuir: más *workers*, una máquina más grande o más copias del mismo monolito.

### Alcance de la evidencia

- Todo lo medido es `POST /login` en un laptop local (4 núcleos físicos, servidor de desarrollo de Werkzeug). **No hay medición** en EC2 ni con Gunicorn, de `GET /reportes` bajo carga, ni de `POST /reportes` con S3.
- Los VUs no son usuarios reales: cada uno inicia sesión de forma continua. El resultado se lee como **capacidad en logins por segundo**, no como número de usuarios conectados.
- No hay datos de demanda real del piloto. La demanda que se usa abajo es un **supuesto ilustrativo** y queda como condición de revisión.

---

## Alternativas consideradas

| | Alternativa | Topología |
|---|---|---|
| **A** | Monolito por capas, una instancia (estado actual) | 1 proceso, 1 BD |
| **B** | Monolito con escalado vertical | El mismo monolito con Gunicorn (*workers* = núcleos), `debug=False` y una instancia con más vCPU |
| **C** | Monolito replicado horizontalmente | N copias idénticas de B detrás de un balanceador, con la misma BD |
| **D** | Extracción de un servicio (distribución parcial) | Identidad y Acceso pasa a un servicio propio con su propia BD (*database per service*); el resto sigue en el monolito y lo consulta por HTTP |
| **E** | Microservicios por contexto | 5 servicios (uno por contexto del Context Map), 5 BD, gateway y mensajería para el ciclo REL-06 / REL-07 |

**Por qué D extrae Identidad.** Es el contexto donde se mide el cuello de botella (`/login`) y el único con un argumento de escalado independiente: escalar solo el `scrypt`. Si la extracción no se justifica para Identidad, se justifica menos para cualquier otro contexto.

### Comparación técnica

| Criterio | A · Actual | B · Vertical | C · Réplicas | D · Extraer Identidad | E · Microservicios |
|---|---|---|---|---|---|
| ¿Ataca el recurso medido (CPU por login)? | No | **Sí**: más núcleos y *workers* | **Sí**: más núcleos en N nodos | Sí, pero igual que C: más núcleos para el servicio de auth | Igual que D |
| Latencia entre contextos | En memoria (~0 ms) | En memoria | En memoria | Saltos de red (ms) en REL-01, REL-02, REL-08 y REL-10, presentes en casi todas las operaciones | Saltos de red en las 9 relaciones |
| Consistencia | ACID | ACID | ACID | Eventual o sagas entre Identidad e Institucional: REL-10 comparte el modelo `Funcionario` y habría que partirlo | Eventual en REL-06 / REL-07; sagas para F-09 |
| Disponibilidad (ver cálculo abajo) | 1 punto único de falla (F-12) | Igual que A en el nodo; F-13 mitigado (el maestro de Gunicorn repone *workers*) | **Sube**: redundancia en la capa de aplicación | **Baja**: Identidad entra en serie en casi toda operación (A₁ × A₂) | Baja más: cadena de servicios en serie |
| Contención de fallos | Ninguna entre contextos | Entre *workers* | Entre nodos | Entre auth y el resto, por proceso | Por servicio, si se implementan timeouts, *circuit breakers* y *bulkheads* en cada frontera |
| Nuevos fallos que introduce | — | — | Balanceador; más conexiones simultáneas a la BD | Fallo parcial por red, timeouts, reintentos e idempotencia en cada llamada | Lo de D multiplicado por 9 relaciones, más el broker |
| Compatibilidad con decisiones vigentes | Total | Total | Total (FF-01 y FF-02 siguen pasando) | Exige partir `models.py` y `Funcionario` | **Contradice el ADR 0003**: exige un broker, que FF-01 bloquea |
| Reversibilidad | — | **Alta**: configuración y tamaño de instancia, en minutos | **Alta**: apagar nodos y el balanceador | Baja: reunir esquemas y código | Muy baja: reescritura (ADR 0001, Reversibilidad) |

### Disponibilidad compuesta (cálculo ilustrativo)

Con disponibilidad individual supuesta de 99 % por componente (sin medir; el valor solo sirve para comparar):

- **A / B:** aplicación × BD = 0,99 × 0,99 = **98,0 %**.
- **C con 2 nodos:** [1 − (1 − 0,99)²] × 0,99 = 0,9999 × 0,99 = **98,99 %**. La redundancia elimina el punto único de falla de la aplicación; la BD sigue siendo uno.
- **D:** una operación típica (crear un reporte, reaccionar) pasa por el monolito, Identidad y las dos BD en serie: 0,99⁴ = **96,1 %**.
- **E:** una consulta de reporte con respaldo comunitario atraviesa gateway, Reportes, Identidad, Validación y sus BD, unos 6 a 7 eslabones: 0,99⁶ a 0,99⁷ = **94,1 % a 93,2 %**.

Distribuir con dependencias síncronas **multiplica** la probabilidad de fallo. Replicar el mismo proceso la **reduce**.

---

## Costo en órdenes de magnitud

El costo se mide en tres dimensiones: infraestructura, complejidad operativa y coordinación del equipo (Ley de Conway). Se usa la convención O(1), O(10) y O(100) para comparar alternativas; no es notación Big-O de algoritmos. La factura de la nube se calcula para anclar la dimensión de infraestructura en números verificables, pero **no es el costo dominante**.

### Infraestructura (USD/mes aproximados, AWS us-east-1 *on-demand*, 730 h)

Precios de referencia consultados el 2026-10-23:

- EC2 `t3.micro` (2 vCPU, 1 GB): ≈ 0,0104 USD/h ≈ 7,6 USD/mes.
- EC2 `t3.small` (2 vCPU, 2 GB): 0,0208 USD/h ≈ 15,2 USD/mes.
- Application Load Balancer: ≈ 16,4 USD/mes de cargo fijo, más ≈ 5,8 USD por LCU-mes.
- IPv4 pública: ≈ 3,7 USD/mes.
- NAT Gateway: ≈ 32,9 USD/mes.
- Fargate (0,25 vCPU y 0,5 GB por tarea): ≈ 9 USD/mes.
- Neon: plan Free a 0 USD (100 CU-hora por proyecto, se suspende tras 5 min sin uso). Plan Launch: 0,106 USD por CU-hora, ≈ 19 USD/mes por una BD de 0,25 CU siempre encendida.

S3 se excluye porque es igual en todas las alternativas.

| Alt. | Componentes | ≈ USD/mes | Índice frente a A | Orden |
|---|---|---|---|---|
| A | 1 `t3.micro` + IPv4 + Neon Free | ≈ 11 | 1× | **O(1)** |
| B | 1 `t3.small` (o mayor) + IPv4 + Neon Free | ≈ 19 | ~2× | **O(1)** |
| C | 2 `t3.small` + ALB (1 LCU) + Neon Launch, siempre encendido para no sumar arranques en frío con más tráfico | ≈ 72 | ~7× | **O(10)** bajo |
| D | 2 `t3.small` (monolito + Identidad, sin redundancia) + ALB con enrutamiento por ruta + 2 BD Neon Launch | ≈ 91 (≈ 121 con 2 nodos por servicio) | ~8–11× | **O(10)** |
| E | 10 tareas Fargate (5 servicios × 2) + ALB + NAT + 5 BD Neon Launch + broker administrado + logs y trazas centralizados | ≈ 250–300 o más | ~25× | **O(10)–O(100)** |

**Nota honesta.** Con planes gratuitos (Neon permite varios proyectos sin costo), la factura de D o E podría bajar mucho. Por eso la dimensión de infraestructura no decide sola. Lo que separa a D y E de A–C son las otras dos dimensiones.

### Las tres dimensiones

| Alt. | Infraestructura | Complejidad operativa | Coordinación (Conway) | Lectura |
|---|---|---|---|---|
| A | O(1) | O(1): un contenedor, un despliegue | O(1): un repo, un artefacto, 3 personas | Barato, pero con un punto único de falla y techo de capacidad medido |
| B | O(1) | O(1): configurar Gunicorn y elegir instancia | O(1) | Ataca la causa medida sin cambiar la topología |
| C | O(10) bajo | O(1)–O(10): balanceador, *health check* (R-05), despliegue a N nodos, logs en N lugares | O(1): sigue siendo un solo artefacto | Capacidad y disponibilidad a cambio de operar el balanceador |
| D | O(10) | O(10): contrato HTTP versionado, timeouts, *circuit breaker* e idempotencia en cada llamada a Identidad, dos pipelines, dos esquemas | O(10): cada cambio de `Funcionario` o de roles exige coordinar dos despliegues | Paga la red sin ganar capacidad frente a C |
| E | O(10)–O(100) | O(100): 5 pipelines, 5 esquemas, broker, consumidores idempotentes, trazas distribuidas, sagas, sin pruebas automatizadas ni monitoreo hoy | O(100): 5 servicios para 3 personas; cada persona sostiene casi dos servicios y cualquier cambio de REL-06 / REL-07 cruza fronteras | "Monolito distribuido": todos los costos de la red con dependencias que obligan a coordinar siempre |

### Relación entre capacidad y demanda

**Capacidad medida:** ≈ 16 logins/s en un laptop de 4 núcleos físicos, es decir ≈ 4 logins/s por núcleo. Es inferencia: el costo de `scrypt` todavía no se ha aislado.

**Demanda del piloto (supuesto ilustrativo, a validar por el equipo).** Si 5.000 ciudadanos activos inician sesión una vez al día y la mitad de esos logins cae en una franja pico de 2 horas:

2.500 ÷ 7.200 s ≈ **0,35 logins/s**. Aun con un factor de ráfaga de 10×, son ≈ 3,5 logins/s.

**Lectura.** La demanda supuesta es **O(1) logins/s** y la capacidad medida es **O(10) logins/s**. El problema de crecimiento del piloto cabe en una sola máquina, y no hay evidencia de que la carga supere "la capacidad de un solo techo".

**Advertencia sobre la instancia.** `t2.micro` y `t3.micro` son *burstable*:

- Sostienen ~10 % de CPU por vCPU cuando agotan sus créditos; `t3.small` sostiene ~20 %.
- Con un trabajo intensivo en CPU como `scrypt`, la capacidad sostenida en producción puede ser **varias veces menor** que la del laptop.

Por eso B debe medirse en la instancia real antes de dimensionarla, y una instancia de CPU sostenida (familias `c`/`m`) es parte de la alternativa B, no de una distribución.

---

## Decisión

**No se distribuye el backend.** Se mantiene el monolito por capas del ADR 0001 como **un único artefacto desplegable**, con todos los contextos en el mismo proceso y la misma base de datos. Se descartan D y E en esta etapa.

**Vía de crecimiento registrada,** por orden, y cada paso condicionado a una medición:

1. **B:** servir con Gunicorn (*workers* según los núcleos, `debug=False`) y dimensionar la instancia según la capacidad medida en ella.
2. **C:** solo si la demanda medida supera la capacidad de B. Implica réplicas idénticas detrás de un balanceador con `/health` (R-05).

Este ADR **no implementa** B ni C: registra el orden en que se escalaría y qué dato lo dispara.

**Por qué:**

1. **La distribución no ataca el recurso que se agota.** El cuello de botella observado es CPU por login, no la comunicación entre contextos (S11; Spike 01). Extraer Identidad (D) solo daría más CPU a `/login`, lo mismo que B o C, pero con saltos de red en casi todas las operaciones.
2. **El costo de distribuir sube un orden de magnitud en cada dimensión** (D: O(10) en las tres; E: hasta O(100) en operación y coordinación) **sin un beneficio medido** que lo compense. Las alternativas B y C quedan en O(1) y O(10) bajo, con un solo artefacto.
3. **Distribuir baja la disponibilidad** con las dependencias síncronas actuales (98,0 % en A frente a 96,1 % en D y ~93–94 % en E, en el cálculo ilustrativo). C la sube (98,99 %).
4. **E contradice decisiones vigentes y protegidas.** El ciclo REL-06 / REL-07 exigiría un broker que el ADR 0003 descarta y que FF-01 bloquea en CI.
5. **Los fallos más graves no dependen de la topología.** Los falsos verdes de S3 (F-05, F-07), los timeouts por defecto (F-06) y la falta de límite de carga útil (F-08) se corrigen con tácticas locales (R-07, R-08 y R-11), que son más baratas que separar procesos.

**Qué NO decide este ADR.**

- No resuelve ESC-07: con la configuración actual, el p95 supera 1 s desde 25 VUs.
- No demuestra que B o C alcancen una capacidad concreta en EC2; eso queda por medir.
- No descarta la distribución para siempre: deja escritas las condiciones que la justificarían (ver Supuestos).

---

## Consecuencias esperadas

**Positivas**

- El costo se mantiene en O(1) (A/B) y solo sube a O(10) bajo si la demanda medida lo exige (C), siempre con un solo repositorio, artefacto y pipeline.
- La comunicación entre contextos sigue en memoria y con transacciones ACID: no aparecen sagas, consistencia eventual ni fallos parciales de red entre contextos.
- La vía de crecimiento es **reversible en minutos**: tamaño de instancia, número de *workers* y número de nodos.
- Las fitness functions vigentes (FF-01 y FF-02) siguen siendo válidas sin cambios.

**Negativas**

- **Mientras no se aplique C, el proceso sigue siendo un punto único de falla** (F-12). Una imagen enorme (F-08) o un fallo fatal tumban todos los contextos a la vez.
- **Los recursos siguen compartidos entre contextos:** la saturación de `/login` puede degradar `/reportes` (cascada por CPU y pool, F-01/F-02). Un *bulkhead* de conexiones (R-03) no aísla la CPU.
- Escalar en C replica **todo** el monolito, incluidas partes que no lo necesitan. Es un sobrecosto de memoria aceptable en O(1) por nodo.
- Con C, N nodos × 15 conexiones multiplican las conexiones a la BD; hay que verificar el límite del plan de Neon antes de añadir nodos (por ejemplo, con PgBouncer, ya medido en R-01).
- Ningún contexto puede desplegarse ni escalar de forma independiente. Se acepta porque hoy hay un solo equipo de 3 personas.

**Trabajo que deja este ADR** (a ratificar por el equipo):

- Medir B en la instancia real: escalones de S11 con Gunicorn en EC2 (o en una réplica local con los mismos núcleos), más la prueba negativa del instrumento.
- Aislar el costo de `scrypt`, para confirmar o refutar la inferencia de CPU (S11 §8).
- Aplicar R-07, R-08 y R-11: corrigen los fallos más graves sin depender de la topología.
- Si algún día se prepara una extracción, primero hay que aislar la persistencia **dentro** del monolito y protegerla con una fitness function, por ejemplo prohibiendo que el modelo de un contexto consulte tablas de otro. Hoy `Reporte.to_dict()` lee `Apoyo` directamente.

---

## Supuestos y condiciones de revisión

| Supuesto | Evidencia actual | Condición que reabre la decisión | Qué se haría |
|---|---|---|---|
| El cuello de botella es la CPU por login, no la comunicación entre contextos | S11 y Spike 01 (local; causa inferida, no aislada) | Un experimento que aísle `scrypt` o una medición en EC2 muestra que la latencia la causa otro recurso | Reevaluar las alternativas con la causa nueva |
| La demanda pico del piloto es O(1) logins/s | **Ninguna** (supuesto ilustrativo de este ADR) | La demanda medida en producción supera el 70 % de la capacidad medida de B en la instancia real | Aplicar C |
| Escalar el monolito basta | Ley de cola de S11; backend sin estado de sesión (inspección) | C con N nodos no mantiene el p95 objetivo porque el límite pasa a ser la BD u otro recurso compartido | Reconsiderar D para el contexto que concentre la carga, con evidencia de qué recurso compite |
| Un contexto no necesita un perfil de recursos, seguridad o disponibilidad distinto al del resto | Context Map: 5 contextos, un solo núcleo (Reportes) | Por ejemplo, Identidad debe cumplir un requisito de seguridad que exige aislarla, o el procesamiento de imágenes necesita más memoria que el resto | Reconsiderar D **solo** para ese contexto, con aislamiento de persistencia previo |
| Un solo equipo de 3 personas mantiene todo el backend | Equipo del proyecto | El equipo crece a varios equipos con ritmos de despliegue independientes (Ley de Conway) | Reconsiderar D o E por fronteras de equipo |
| La disponibilidad del piloto tolera un punto único de falla mientras no se aplique C | Doc 03 lo deja como riesgo remanente | Se fija un SLO de disponibilidad o se mide un tiempo de recuperación inaceptable con `restart: always` (R-14) | Aplicar C (2 nodos) aunque la capacidad no lo exija |

---

## Reversibilidad

**Alta para la decisión; asimétrica entre alternativas.**

- Mantener el monolito no exige deshacer nada.
- Pasar de A a B o a C, y volver, cuesta minutos u horas: configuración de Gunicorn, tamaño de instancia, número de nodos y balanceador. No hay migración de datos.
- Si las condiciones de revisión se cumplen, D sigue siendo posible. El costo de llegar a D baja si antes se aísla la persistencia dentro del monolito.
- Al revés, distribuir ahora y luego volver al monolito tendría reversibilidad **baja**: reunir esquemas, contratos y pipelines ([ADR 0001, Reversibilidad](./0001-decision-estilo.md)).

---

## Auditoría de propuestas típicas de IA (Ciclo EDAV 2)

Propuestas habituales de un asistente de IA al pedirle "una arquitectura de microservicios e infraestructura elástica" para UrbanFix, contrastadas con la evidencia del proyecto. *El equipo debe reemplazar esta tabla por las propuestas que obtenga al ejecutar la actividad con su propio asistente.*

| Propuesta | Veredicto | Evidencia |
|---|---|---|
| Separar en microservicios por dominio con Kubernetes | **Rechazada** | Costo O(100) en operación y coordinación para 3 personas. No ataca la CPU por login (S11). Baja la disponibilidad compuesta |
| Broker (Kafka/RabbitMQ) para las reacciones | **Rechazada** | ADR 0003 y FF-01. No hay medición de que REL-06 cause un problema |
| Autoescalado horizontal con balanceador | **Modificada** | Se adopta como paso C, condicionado a una demanda medida y precedido por B, que cuesta O(1) |
| Caché (Redis) para el listado de reportes | **Modificada** | Primero R-13 (conteo agregado y paginación) y medir `GET /reportes`: no hay evidencia de que haga falta un componente nuevo |
| Gunicorn con varios *workers* y `debug=False` | **Aceptada** (pendiente de medición) | Ataca F-02 y F-13 sin cambiar la topología; es el paso B |

---

## Correcciones a documentos previos

1. **[ADR 0001](./0001-decision-estilo.md), Supuestos:** el umbral de revisión "100 peticiones concurrentes por segundo" no tiene respaldo y es unas 6 veces la capacidad medida (≈ 16 logins/s). Se reemplaza por las condiciones de revisión de este ADR.
2. **ADR 0001, Contexto y Consecuencias:** atribuye la degradación a la base de datos ("agota sus conexiones"). El Spike 01 solo lo respalda para los errores, no para la latencia (ver también ADR 0003, Correcciones).
3. **[01-contexto-sistema.md](../docs/01-contexto-sistema.md):** describe producción como EC2 `t2.micro` + Gunicorn, pero [03](../docs/03-atributos-calidad.md) marca esa instancia como refutada para la versión actual, y `requirements.txt` no incluye Gunicorn aunque `deploy.yml` lo reinicia. Hay que dejar un único montaje de referencia.

---

## Trazabilidad

| Elemento | Ubicación |
|---|---|
| Curva de degradación, punto de quiebre y límite del instrumento | `experimentos/crecimiento.md` · `experimentos/crecimiento-S11/` (plan `dc29ec9`, resultados `d7cbbcd`) |
| Evidencia de que el pool no explica la latencia | `experimentos/tactica-resiliencia.md` · rama `spike/01-pgbouncer-login` |
| Fallos por recurso compartido (F-01, F-02, F-12) y fallos independientes de la topología (F-05 a F-08) | `docs/arquitectura/matriz-fallos.md` |
| Tácticas R-03 (*bulkhead*), R-05 (`/health`), R-07, R-08, R-11 y R-15 (separación en procesos) | `docs/arquitectura/matriz-resiliencia.md` |
| Relaciones entre contextos (REL-01 a REL-10) | `docs/dominio/context-map.md` |
| Reglas en CI que protegen las decisiones vigentes | `tests/architecture/test_fitness_function.py` · `docs/arquitectura/fitness-function.md` |
| Restricciones de presupuesto y equipo | `docs/01-contexto-sistema.md` §2 |
| Precios de referencia (consultados el 2026-10-23) | AWS EC2 `t3.small` us-east-1 (calculator.holori.com) · ELB (cloudchipr.com, aws.amazon.com/elasticloadbalancing) · Neon (neon.com/pricing) |

---

## Veredicto del Mini-comité Técnico 2

*Pendiente.* Registrar aquí la fecha, el veredicto (aprobada / aprobada con cambios / rechazada), las objeciones del sínodo y los cambios que provoquen.

---

**Uso de IA:** Claude (Anthropic) ayudó a contrastar los documentos del repositorio con los resultados de los experimentos, a calcular los costos y la disponibilidad compuesta, y a redactar este ADR. La decisión, los supuestos de demanda y el veredicto son del equipo.
