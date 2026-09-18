# ADR 0002 — Introducir una capa de Repositorios por dominio, con un `bind` de SQLAlchemy propio para cada uno, que aísle la lógica de negocio del acceso directo a PostgreSQL

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán

**Estado:** Propuesta

---

## Contexto

El ADR 0001 dejó como riesgo declarado que todo el sistema comparte un único pool de conexiones
hacia PostgreSQL, sin ninguna frontera entre dominios. La inspección directa del código confirma
que ese riesgo no es solo teórico: hoy no existe ninguna capa intermedia. Los cuatro módulos de
dominio documentados en `docs/07-c4-componentes.md` (Usuarios y Autenticación, Reportes,
Interacciones, Funcionarios y Entidades) llaman al ORM directamente desde `app/routes.py`
(`Usuario.query`, `Reporte.query`, `Apoyo.query`, etc.), compartiendo un único motor de
SQLAlchemy configurado en `config.py` con `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` —
sin `pool_size` ni `max_overflow` explícitos, es decir, el valor por defecto de 15 conexiones
concurrentes (5 + 10) repartidas sin ningún control entre los nueve endpoints del backend.

La medición de línea base (`docs/04-escenarios-calidad.md`, escenario ESC-07) sometió `POST
/login` a una rampa de carga hasta 800 usuarios virtuales concurrentes y registró, sobre cinco
corridas válidas, una tasa de error mediana de 11,11% y un p95 mediano de 31,06 s. Esa medición
es la evidencia que motiva esta decisión, pero se declara con precisión lo que sí y lo que no
demuestra: **no aísla la causa**. El servidor de aplicación activo (`app.py`, servidor de
desarrollo de Werkzeug, `debug=True`, sin `threaded=True`) es, con al menos la misma probabilidad
que el pool de conexiones, responsable de la degradación observada, y esta medición no permite
separar cuánto corresponde a cada uno. Esta decisión no se presenta como una corrección de esa
degradación medida; se presenta como lo que realmente ataca: la ausencia estructural de una
frontera entre dominio y persistencia, que el ADR 0001 ya había señalado como riesgo antes de
medir nada.

---

## Alternativas consideradas

### 1. Mantener el acceso directo al ORM desde `routes.py` (statu quo)
**Costo:** 0 horas de ingeniería. **Por qué se descartó:** es el estado actual, verificado en
`docs/07-c4-componentes.md` (la hipótesis de una capa de servicios fue evaluada y eliminada del
modelo por no existir en el código). No ofrece ningún punto donde limitar o auditar el consumo de
conexiones por dominio: un pico en Reportes puede seguir agotando las conexiones que necesita
Autenticación, sin que el código tenga forma de evitarlo ni de detectarlo.

### 2. Separar cada dominio en un microservicio con base de datos propia
**Costo estimado:** entre 120 y 160 horas de ingeniería de equipo (orquestación de red, CI/CD por
servicio, migración de esquema, comunicación entre servicios). **Por qué se descartó:** es la
misma alternativa ya rechazada en el ADR 0001 por su costo de infraestructura y el riesgo que
introduce sobre el RNF #1; nada de lo medido en ESC-07 cambia esa conclusión, porque la prueba no
aisló siquiera si el cuello de botella está en la base de datos.

### 3. Capa de Repositorios por dominio, con un `bind` de SQLAlchemy propio para cada uno (elegida)
**Costo estimado:** ~22 horas de ingeniería de equipo, distribuibles entre los tres integrantes:

| Tarea | Horas |
|---|---|
| `UsuarioRepository` / `FuncionarioRepository` (autenticación y cuentas) | 4 |
| `ReporteRepository` (incluye conteo de apoyos/desapoyos y `to_dict`) | 5 |
| `InteraccionRepository` (`Apoyo`, `Comentario`) | 3 |
| `CatalogoRepository` (`Categoria`, `EntidadPublica`) | 2 |
| Refactor de los 9 endpoints en `app/routes.py` para usar los repositorios | 4 |
| Pruebas unitarias con repositorios simulados (mocks) | 4 |
| **Total** | **22** |

**Por qué se eligió:** ataca la causa estructural señalada desde el ADR 0001 (ausencia de
frontera) sin la reescritura completa que exigía la Alternativa 2, y sin inventar una solución
para un problema (el servidor de desarrollo) que esta decisión no mide ni resuelve.

---

## Decisión

Se introduce una capa de **Repositorios**, uno por cada módulo de dominio ya documentado en
`docs/07-c4-componentes.md` (`UsuarioRepository`, `ReporteRepository`, `InteraccionRepository`,
`CatalogoRepository`). Ningún Blueprint de `app/routes.py` vuelve a invocar el ORM directamente;
toda consulta o escritura pasa por el Repositorio de su dominio.

Cada Repositorio se conecta a través de un **`bind` propio de Flask-SQLAlchemy**
(`SQLALCHEMY_BINDS` en `config.py`), es decir, un motor y un pool de conexiones independientes por
dominio, aunque los cuatro sigan apuntando físicamente a la misma base de datos PostgreSQL mientras
no haya razón para separarla. Esto es lo que define la frontera de forma verificable en el código:
no es una convención de nombres, es una conexión distinta por dominio, con su propio
`pool_size`/`max_overflow` configurable de forma independiente.

---

## Consecuencias

**Positivas:**
- Ningún dominio puede agotar por sí solo el 100% de las conexiones disponibles: el límite es por
  `bind`, no compartido.
- La lógica de negocio queda desacoplada del ORM concreto, permitiendo pruebas unitarias con
  repositorios simulados.
- Mejora la reversibilidad "baja" dejada por el ADR 0001: migrar un dominio a una base de datos
  físicamente distinta es, a partir de esta decisión, cambiar una URI en `SQLALCHEMY_BINDS`, no
  reescribir código de acceso a datos disperso en `routes.py`.

**Negativas, declaradas sin evasivas:**
- Esta decisión **no resuelve la degradación medida en ESC-07**. Si la causa dominante resulta ser
  el servidor de desarrollo de Werkzeug —evidencia igual de fuerte que la del pool, ver
  Contexto—, el sistema seguirá degradándose bajo carga después de implementar esta ADR, y eso no
  debe presentarse como una corrección pendiente de verificar, sino como una limitación conocida
  de antemano.
- Cuatro `binds` significan hasta cuatro pools de conexiones abiertos simultáneamente contra el
  mismo PostgreSQL; hay que dimensionar la suma contra `max_connections` del servidor (Neon o
  local), no solo cada `bind` por separado.
- Añade 22 horas de trabajo de refactor a un equipo con tiempo de entrega ajustado, sobre una
  causa que la propia medición no confirma como dominante.

---

## Reversibilidad

**Media, delimitada con precisión.** Deshacer esta decisión implica: eliminar 4 clases de
Repositorio, revertir 9 endpoints en `app/routes.py` a llamadas directas al ORM, y quitar la
entrada `SQLALCHEMY_BINDS` de `config.py`. No hay cambio de esquema de base de datos ni de
contrato de la API — el esfuerzo de reversión es comparable al de implementación, ~15-20 horas,
porque es el mismo código el que se mueve en sentido contrario.

**Nota de re-decisión.** Si en algún momento se impone una restricción externa que prohíba
compartir la instancia física de PostgreSQL entre dominios (p. ej. un requisito regulatorio de
aislamiento de datos), esta decisión ya deja el punto de corte hecho: cambiar la URI de un `bind`
en `SQLALCHEMY_BINDS` para que ese dominio apunte a una instancia distinta no toca `routes.py` ni
los modelos. El costo de esa migración pasa de "reescribir accesos a datos dispersos" a
"reconfigurar una variable de entorno por dominio afectado".

---

## Supuestos

Se asume que cuatro `binds` simultáneos, cada uno con un pool pequeño (a definir en
implementación, p. ej. 5+5), no exceden `max_connections` de PostgreSQL/Neon. Se asume también que
el servidor de aplicación (Werkzeug o su reemplazo) no es la variable que se está controlando en
esta decisión — eso queda fuera de alcance de este ADR.

Ambos supuestos se revisarán re-ejecutando ESC-07 contra el backend con los Repositorios y los
`binds` implementados, y comparando contra la línea base ya documentada (tasa de error mediana
11,11%, p95 mediano 31,06 s). Si el resultado no mejora de forma sustancial, la conclusión correcta
no será que esta ADR fracasó, sino que confirma lo que el Contexto ya declaraba: la causa dominante
está en el servidor de aplicación, no en la ausencia de frontera de persistencia.
