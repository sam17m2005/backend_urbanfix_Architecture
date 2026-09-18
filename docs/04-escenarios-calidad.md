# UrbanFix — Escenarios de Calidad y Evidencia Ejecutable

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Documentos previos:** [01](./01-contexto-sistema.md) · [02](./02-stakeholders-drivers.md) · [03](./03-atributos-calidad.md)
**Evidencia cruda asociada:** `exp/` (pendiente de cargar la salida de las corridas; ver sección 8)

Este documento convierte los atributos priorizados en escenarios verificables y reporta la
medición de línea base ejecutada contra el sistema real, con herramienta, método, condiciones y
datos. Corresponde a la evidencia obligatoria de la semana 4 y es el único de la serie 01–04 que
no puede escribirse sin ejecutar.

El criterio de la rúbrica es explícito: una medición sin datos, condiciones y método reproducible
no se considera medición.

---

## Índice interno

1. Formato de escenario
2. Escenarios formulados
3. Registro de escenarios generados por IA y corregidos
4. Escenario medido y método
5. Síntesis de la medición
6. Verificación estricta del protocolo
7. Exclusiones de alcance de la medición
8. Clasificación del material y trazabilidad
9. Declaración de uso de IA

---

## 1. Formato de escenario

Un escenario de calidad no es un deseo ("el sistema debe ser rápido"). Tiene seis partes, y la
última es la que lo hace verificable:

| Parte | Qué responde |
|---|---|
| **Fuente** | ¿Quién o qué genera el estímulo? |
| **Estímulo** | ¿Qué ocurre exactamente? |
| **Artefacto** | ¿Sobre qué componente del sistema? |
| **Entorno** | ¿En qué condiciones? (operación normal, carga pico, fallo parcial) |
| **Respuesta** | ¿Qué debe hacer el sistema? |
| **Medida de respuesta** | ¿Con qué número se comprueba? |

### 1.1 Origen de cada escenario

Cada escenario declara de dónde viene. La rúbrica distingue dos rutas y exige registrar ambas:

- **RNF-V** — reescritura de un requerimiento no funcional ya verificado del proyecto.
- **IA-C** — propuesto por IA y **corregido por el equipo** para hacerlo medible (ver §2.7).

---

---

## 2. Escenarios formulados

### ESC-01 — Creación concurrente de reportes con imagen

**Origen:** RNF-V (RNF #1 — proceso de reporte simplificado, tope de 90 s)

| Parte | Contenido |
|---|---|
| Fuente | Ciudadanos usuarios de la app |
| Estímulo | N usuarios crean simultáneamente un reporte con fotografía |
| Artefacto | Endpoint de creación de reportes del backend Flask + subida a S3 |
| Entorno | Operación normal, instancia EC2 actual |
| Respuesta | El sistema acepta y persiste todos los reportes sin errores |
| **Medida** | Hipótesis, sin medir: p95 ≤ 400 ms y tasa de error ≤ 5% con 10 usuarios concurrentes |

**Atributo:** Rendimiento · **Prioridad:** Alta

---

### ESC-02 — Caída del backend

**Origen:** IA-C (derivado del riesgo "punto único de falla" — requiere corrección del equipo)

| Parte | Contenido |
|---|---|
| Fuente | Fallo de infraestructura |
| Estímulo | La instancia EC2 deja de responder |
| Artefacto | Cliente Android + API |
| Entorno | Fallo parcial |
| Respuesta | La app degrada de forma controlada e informa al usuario, sin cerrarse ni perder el reporte en curso |
| **Medida** | Hipótesis, sin medir: mensaje de error visible en ≤ 3 s y borrador conservado |

**Atributo:** Disponibilidad · **Prioridad:** Crítica

---

### ESC-03 — Indisponibilidad de Gemini AI

**Origen:** IA-C (derivado del riesgo "dependencia de terceros sin fallback")

| Parte | Contenido |
|---|---|
| Fuente | Servicio externo de terceros |
| Estímulo | La API de Gemini responde con error o excede el tiempo de espera |
| Artefacto | Módulo de generación de descripción |
| Entorno | Operación normal con dependencia externa degradada |
| Respuesta | El reporte puede completarse con descripción manual; la funcionalidad principal no se bloquea |
| **Medida** | Hipótesis, sin medir: timeout ≤ 5 s y el reporte se crea con descripción manual |

**Atributo:** Disponibilidad, Rendimiento · **Prioridad:** Crítica/Alta

---

### ESC-04 — Acceso no autorizado a imágenes de reportes

**Origen:** RNF-V (Ley 1581/2012, restricción regulatoria del documento 01 §3.4)

| Parte | Contenido |
|---|---|
| Fuente | Atacante externo no autenticado |
| Estímulo | Intento de listar o descargar objetos del bucket S3 directamente |
| Artefacto | Buckets `urbanfiximagenesbucket` y `urbanfixperfilimagenesbucket` |
| Entorno | Operación normal |
| Respuesta | El acceso es denegado |
| **Medida** | Hipótesis, sin medir: respuesta HTTP 403 en el 100% de los intentos anónimos |

**Atributo:** Seguridad · **Prioridad:** Crítica

---

### ESC-05 — Despliegue de un cambio defectuoso

**Origen:** IA-C (derivado de la restricción "sin ambiente de staging")

| Parte | Contenido |
|---|---|
| Fuente | Equipo de desarrollo |
| Estímulo | Se fusiona a `main` un cambio que rompe un endpoint |
| Artefacto | Pipeline de GitHub Actions |
| Entorno | Despliegue continuo |
| Respuesta | El pipeline detiene el despliegue antes de llegar a producción |
| **Medida** | Hipótesis, sin medir: el build falla y la detección ocurre en ≤ 5 min |

**Atributo:** Desplegabilidad, Mantenibilidad · **Prioridad:** Alta
Este escenario es el que se automatiza como función de aptitud en CI en las semanas 12 a 14.

---

### ESC-06 — Enrutamiento del reporte a la entidad competente

**Origen:** RNF-V (RNF #2 — canalización automática a entidades)

| Parte | Contenido |
|---|---|
| Fuente | Ciudadano que crea un reporte |
| Estímulo | Se envía un reporte de categoría ___ en la ubicación ___ |
| Artefacto | Módulo de clasificación y enrutamiento del backend |
| Entorno | Operación normal |
| Respuesta | El reporte queda asociado a la entidad legalmente competente según categoría y ubicación |
| **Medida** | Hipótesis, sin medir: ≥ 95% de asignaciones correctas sobre 20 casos con entidad esperada conocida |

**Atributo:** Interoperabilidad, Mantenibilidad · **Prioridad:** Alta

---

### ESC-07 — Autenticación concurrente bajo escalado agresivo

**Origen:** derivado de la medición de línea base. Formulado después de la medición, lo cual se declara
explícitamente: el escenario se ajustó a lo que se midió, no al revés.

| Parte | Contenido |
|---|---|
| Fuente | Ciudadanos usuarios de la app |
| Estímulo | Un número creciente de usuarios se autentica de forma concurrente, en una rampa de carga diseñada deliberadamente para llevar al sistema a su punto de quiebre |
| Artefacto | Endpoint `POST /login` del backend Flask + consulta a PostgreSQL |
| Entorno | Contenedor Docker en máquina de desarrollo local (IP `172.18.0.1`, gateway típico de una red Docker). No es el entorno de producción (EC2 `t2.micro` + Neon) |
| Respuesta | Hipótesis previa, según el propio comentario del script (`"el martillazo... aquí debería romperse"`): el sistema **no** sostendría los 800 VUs sin degradarse |
| Medida | El script no declara un bloque `thresholds` formal. Como referencia de calificación se adopta, por consistencia con el resto de este documento, una tasa de error ≤ 5%; se declara explícitamente que este umbral no fue parte del diseño original de la prueba |

Formular un escenario después de medirlo es aceptable siempre que se declare. Lo que no es
aceptable es presentarlo como si hubiera sido la hipótesis previa.

---

---

## 3. Registro de escenarios generados por IA y corregidos

| ESC | Propuesta original de la IA | Problema detectado | Versión corregida | Fundamento |
|---|---|---|---|---|
| ESC-02 | | | | |
| ESC-03 | | | | |
| ESC-05 | | | | |

**Escenarios descartados para esta entrega:**

| Escenario | Por qué se descartó |
|---|---|
| ESC-02 — Caída del backend | No aplica al montaje actual: las pruebas se ejecutan en un entorno local con Docker, donde no existe la instancia EC2 cuyo fallo se pretendía simular |
| ESC-05 — Despliegue de un cambio defectuoso | El pipeline de despliegue continuo no está activo, de modo que no hay flujo real que pueda detener un cambio defectuoso |

---

---

## 4. Escenario medido y método

**Escenario elegido para la línea base:** ESC-07 — Autenticación concurrente.

**Justificación de la elección.** Es el escenario ejecutable con menor riesgo operativo sobre el
sistema en producción: no invoca servicios externos de terceros, no persiste datos nuevos y no
contamina el conjunto de reportes reales. La elección no fue por prioridad arquitectónica sino por
viabilidad; ESC-01, que sí ataca el atributo más crítico, quedó excluido por las razones de la
sección 7.

| Aspecto | Definición |
|---|---|
| Herramienta | k6 |
| Script | `Pruebas/prueba2.js`, rama `main` del repositorio backend |
| Endpoint objetivo | `POST /login` en `http://172.18.0.1:5000` (IP de gateway de la red Docker local, no `host.docker.internal`) |
| Carga simulada | Rampa en cuatro etapas: 10 s hasta 50 VUs, 20 s hasta 300 VUs, 20 s hasta 800 VUs, 10 s de descenso a 0 (60 s de duración total) |
| Pausa entre iteraciones | `sleep(0.1)` |
| Umbrales declarados | Ninguno. El script no define un bloque `thresholds`; no hay un criterio de éxito/fallo codificado en el instrumento |
| Semilla | Credenciales fijas de prueba (`test@urbanfix.com`), sin distribución aleatoria |
| Entorno medido | Local. Backend en contenedor Docker sobre equipo de desarrollo, corriendo el servidor de desarrollo de Flask (`python3 app.py`, `debug=True`, sin `threaded=True`) — no Gunicorn, pese a que `requirements.txt` tampoco lo incluye. La ejecución no se realizó sobre la instancia EC2 |
| Equipo de ejecución | HP Laptop 14-cf3xxx (DESKTOP-V11ML71) · Intel Core i5-1035G1 a 1.00 GHz · 16 GB de RAM · Windows de 64 bits (dispositivo de Samuel) |
| Métricas capturadas | `http_req_duration` (avg, min, med, max, p90, p95), tasa de error (`http_req_failed`), throughput (`http_reqs`), VUs, iteraciones completas e interrumpidas |
| Número de corridas | 6 ejecutadas; la primera se descarta por ser de calentamiento (el contenedor recién iniciado). Se reportan las corridas 2 a 6 |

### 4.1 Qué invalidaría esta medición

Sección exigida por el checklist, con 90 minutos asignados. Declarar de antemano bajo qué
condiciones el resultado no sería válido es lo que separa una medición de una anécdota. También es
la mejor defensa posible: si el jurado señala una amenaza a la validez que el equipo ya listó, la
respuesta está escrita.

| # | Amenaza a la validez | Por qué invalidaría el resultado | Cómo se controla o se declara |
|---|---|---|---|
| 1 | La máquina que genera la carga es el cuello de botella, no el servidor | Se estaría midiendo el cliente de prueba | Verificar CPU y red del generador durante la corrida |
| 2 | Latencia de red variable entre el generador y EC2 | El p95 reflejaría la red, no el sistema | Registrar región, tipo de conexión y latencia base (`ping`) |
| 3 | Ruido de tráfico real concurrente en producción | Los datos mezclarían carga sintética y real | Medir en ventana de bajo uso, o sobre réplica; declararlo |
| 4 | Caché en frío o en caliente entre corridas | Resultados no comparables entre sí | Fijar el estado inicial; descartar la corrida de calentamiento |
| 5 | Imágenes de prueba de tamaño no representativo | Subestima o exagera el costo de subida a S3 | Usar el tamaño mediano real observado en reportes existentes |
| 6 | Base de datos con volumen distinto al de producción | Las consultas se comportan distinto según el volumen | Documentar el número de registros al momento de medir |
| 7 | Cuota o límite de tasa de un servicio externo (Gemini, S3) | Errores atribuibles al proveedor, no al diseño | Separar los errores por origen en el reporte |

**Declaración de alcance:** esta medición es válida únicamente para ___ *(endpoint, carga,
entorno y commit específicos)*. No permite concluir nada sobre ___.

### 4.2 Advertencias operativas

- **No midan contra producción sin avisar al equipo.** Una prueba de carga sobre una `t2.micro`
  puede tumbar el servicio.
- **Nunca usen imágenes reales de ciudadanos como datos de prueba.** Generen imágenes sintéticas
  de tamaño comparable. El sistema está bajo la Ley 1581/2012.
- **Reporten percentiles, no promedios.** El promedio esconde exactamente el problema que buscan.

---

---

## 5. Síntesis de la medición

**Sistema medido.** Backend UrbanFix, aplicación Flask ejecutándose en un contenedor Docker sobre
el equipo de Samuel, con el servidor de desarrollo de Werkzeug (`python3 app.py`, `debug=True`, sin
`threaded=True`) — no Gunicorn. La ejecución no se realizó sobre la instancia EC2.

**Escenario medido.** Autenticación concurrente contra el endpoint `POST /login`, en entorno
local, bajo una rampa de carga agresiva hasta 800 usuarios virtuales. Corresponde al escenario
**ESC-07**, no a ESC-01.

**Hipótesis previa contrastada.** El script no declara un umbral formal (`thresholds`). La
hipótesis recuperable es la que consta en el comentario del propio código — que el sistema debería
romperse al acercarse a 800 VUs — no un criterio de SLA con número explícito. Para poder calificar
el resultado de forma comparable con los demás escenarios de este documento, se adopta aquí, solo
como referencia de lectura, una tasa de error ≤ 5%; se deja explícito en cada afirmación que ese
umbral no estaba codificado en el instrumento.

**Semilla de datos.** No es aleatoria: son credenciales fijas de prueba (`test@urbanfix.com`)
usadas por todos los usuarios virtuales. Queda pendiente el volumen de la base al momento de medir.

**Instrumento.** k6. Perfil de carga en cuatro etapas: rampa de 10 s hasta 50 VUs, 20 s hasta 300
VUs, 20 s hasta 800 VUs, y descenso de 10 s hasta 0. Duración total de 60 s por corrida, con
`sleep(0.1)` entre iteraciones. Sin umbrales declarados en el script.

**Condiciones.** Equipo de ejecución: HP Laptop 14-cf3xxx (DESKTOP-V11ML71), Intel Core
i5-1035G1 a 1.00 GHz, 16 GB de RAM, Windows de 64 bits (dispositivo de Samuel). Las pruebas se
ejecutaron de forma local, por lo que no se realizaron sobre la instancia EC2.

**Validación del instrumento.** Parcial. A favor: k6 ejecutó y contabilizó 9.037 checks de
código de respuesta a lo largo de las cinco corridas reportadas, con una mezcla real de éxitos y
fallos (8.065 exitosos, 972 fallidos) — es decir, el instrumento demostró ser capaz de distinguir
y contar un fallo real. Sigue faltando la prueba negativa explícita (apuntar a un endpoint
inexistente o a credenciales inválidas) para confirmar que cada fallo detectado es atribuible al
sistema y no a un artefacto del instrumento.

**Corridas realizadas.** Seis en total; la primera se descarta por ser de calentamiento (el
contenedor recién iniciado, antes de estabilizar cachés y conexiones). Se reportan las corridas 2
a 6, con 9.037 peticiones acumuladas.

**Resultado reportado.**

| Métrica | Corrida 2 | Corrida 3 | Corrida 4 | Corrida 5 | Corrida 6 | Mediana |
|---|---|---|---|---|---|---|
| Tasa de éxito (%) | 86,62 | 87,26 | 91,77 | 91,13 | 88,88 | **88,88** |
| Tasa de error (%) | 13,37 | 12,73 | 8,22 | 8,86 | 11,11 | 11,11 |
| p95 `http_req_duration` (s) | 31,60 | 36,47 | 31,06 | 31,02 | 30,95 | **31,06** |
| avg `http_req_duration` (s) | 17,44 | 17,37 | 15,81 | 16,07 | 16,99 | 16,99 |
| Peticiones (`http_reqs`) | 1.780 | 1.610 | 1.922 | 1.907 | 1.818 | — |
| Iteraciones interrumpidas | 57 | 204 | 57 | 53 | 56 | — |
| VUs máximos alcanzados | 800 | 800 | 800 | 800 | 800 | — |

**Comparación con el criterio de referencia adoptado.** La tasa de error mediana (11,11%)
**excede** el umbral de referencia de 5% adoptado para poder calificar el resultado. El escenario,
leído bajo ese criterio, **no se cumple** en ninguna de las cinco corridas reportadas (el rango de
error va de 8,22% a 13,37%, siempre por encima de 5%). Contra el umbral de tiempo de respuesta
usado en otro escenario de este documento (`p(95)<1500 ms`), el incumplimiento es aún mayor: el p95
mediano de 31,06 s equivale a 20,7 veces ese umbral.

**Qué puede afirmarse.** Bajo una rampa de carga que escala hasta 800 usuarios virtuales
concurrentes contra `/login`, el backend UrbanFix —corriendo con el servidor de desarrollo de
Flask, sin Gunicorn, en un contenedor Docker local— presentó una tasa de error de entre 8,22% y
13,37% (mediana 11,11%) a lo largo de cinco corridas, con un p95 de `http_req_duration` de entre
30,95 s y 36,47 s (mediana 31,06 s). El sistema se degrada de forma medible y consistente bajo esa
carga.

**Qué todavía no puede afirmarse.** Varias cosas, y conviene decirlas todas:

Esta medición **no aísla la causa** de la degradación. Son candidatas al menos el servidor de
desarrollo de Werkzeug (`app.run(..., debug=True)`, sin `threaded=True`), que procesa solicitudes
de forma esencialmente secuencial, y el pool de conexiones de SQLAlchemy, configurado con sus
valores por defecto (`pool_size=5`, `max_overflow=10`, máximo 15 conexiones). Separar cuánto
corresponde a cada una requeriría observar CPU, memoria y el estado del pool durante la corrida,
ninguno de los cuales se registró aquí.

El diagnóstico previo sostenía que el cuello de botella del sistema es la subida concurrente de
imágenes a S3 desde el backend. Esta medición **no lo contrasta**: `/login` no toca S3, no invoca
a Gemini y no procesa imágenes. Afirmar que esta medición valida o refuta ese diagnóstico sería una
**INTERPRETACIÓN PREMATURA**. La razón por la que no se midió el flujo de creación de reportes es
una exclusión de alcance documentada en la sección 7.

Sí se identificó un indicio del punto de saturación: entre 300 y 800 VUs la tasa de error se
dispara de forma consistente en las cinco corridas reportadas. Pero el punto exacto de quiebre —el
VU específico donde el sistema empieza a fallar— no se midió, porque el script escala en bloques de
250-500 VUs y no reporta métricas por escalón.

No puede concluirse nada sobre el RNF #1. Los 90 s cubren el flujo completo desde la app, con
captura de foto, geolocalización y generación de descripción; aquí solo se midió una petición HTTP
de autenticación.

**Limitaciones.** Entorno local en lugar de producción (EC2 `t2.micro` + Neon), con el servidor de
desarrollo de Flask en lugar de Gunicorn — que es, de hecho, la limitación más relevante, porque el
servidor de desarrollo es en sí mismo una causa candidata de la degradación observada, no solo una
diferencia de entorno neutral. Credencial única, lo que puede beneficiarse de caché de consulta
sobre el mismo registro. Ausencia de datos de CPU y memoria del contenedor durante las corridas.
Sin umbral formal declarado en el script.

**Dónde está la evidencia reproducible.** `exp/` en el repositorio backend (la rúbrica del curso la
nombra `/experimentos`; ver nota de unificación en la sección 8), con el script de carga
(`Pruebas/prueba2.js`). La salida cruda de las seis corridas (incluida la de calentamiento
descartada) está pendiente de subir a esa carpeta como texto plano.

---

---

## 6. Verificación estricta del protocolo

| # | Criterio | Estado | Observación |
|---|---|---|---|
| 1 | Mínimo tres corridas | Cumple | Seis corridas ejecutadas, cinco reportadas |
| 2 | Primera corrida descartada | Cumple | La corrida 1 se descarta por ser de calentamiento; muestra 493 iteraciones interrumpidas frente a 53-204 en las cinco corridas reportadas, consistente con esa lectura — ver sección 5 |
| 3 | Mediana reportada | Cumple | Tasa de error mediana de 11,11% y p95 mediano de 31,06 s sobre las cinco corridas reportadas |
| 4 | Códigos de respuesta verificados | Cumple con salvedad | 9.037 checks evaluados; 8.065 exitosos y 972 fallidos — el instrumento registró una mezcla real de resultados, no un 100% que impediría verificar su sensibilidad a fallos |
| 5 | Máquina y condiciones registradas | Cumple | HP Laptop 14-cf3xxx, Intel Core i5-1035G1 a 1.00 GHz, 16 GB de RAM, Windows de 64 bits; ejecución local en contenedor Docker |
| 6 | Volumen y distribución de semilla registrados | Parcial | Semilla definida y declarada: credenciales fijas de prueba, sin distribución aleatoria. Falta el volumen de la base al momento de medir |
| 7 | Mismo escenario y condiciones comparables entre corridas | Cumple | El script es el mismo (`Pruebas/prueba2.js`, confirmado contra `main`) y el equipo de ejecución es el mismo en las cinco corridas reportadas |
| 8 | Evidencia de que el instrumento funcionaba | Cumple con salvedad | Los 972 checks fallidos, correctamente distinguidos de los 8.065 exitosos, son evidencia indirecta de que k6 detecta fallos reales; sigue faltando una prueba negativa deliberada (endpoint inexistente o credenciales inválidas) para confirmarlo de forma directa |

De ocho criterios, cinco se cumplen sin salvedad, dos se cumplen con salvedad y uno es parcial
(el volumen de la base al momento de medir).

---

---

## 7. Alcance de la medición y escenarios no reportados

Esta sección registra qué se midió, qué se intentó medir y qué se decidió no medir, con la
consecuencia de cada caso sobre lo que el equipo puede afirmar.

### 7.1 ESC-01 tiene script ejecutable, sin resultados reportados

En la rama `main` existe `Pruebas/prueba1.js`, que ejerce `POST /reportes` con imagen en base64,
diez usuarios virtuales concurrentes, una iteración cada uno y un umbral de `p(95)<400`. Es decir,
el escenario de creación concurrente de reportes sí fue instrumentado. Lo que no existe es un
registro de resultados: el documento de salidas solo contiene las seis corridas de autenticación.

Dos caminos posibles, y conviene elegir uno de forma explícita:

Si la prueba llegó a ejecutarse, recuperar la salida y reportarla, aunque haya fallado el umbral de
400 ms. Un escenario que no cumple su medida es un resultado tan válido como uno que la cumple, y
más útil para el rediseño.

Si no llegó a ejecutarse, declararlo así y no presentar la existencia del script como si fuera
evidencia. Un script sin corrida no es una medición.

### 7.2 Corrección sobre la justificación de la exclusión

La versión anterior de este documento sostenía que no se medía la creación de reportes porque el
flujo invoca la API de Gemini y ello expone el proyecto a limitación de tasa o bloqueo de la clave.
La inspección del backend refuta esa premisa: no hay ninguna referencia a Gemini, `genai`, Google
ni OpenAI en `app/routes.py`, y el backend no realiza llamadas HTTP salientes. El flujo de creación
de reportes consiste en decodificar el base64, normalizar la imagen con Pillow, subirla a S3 y
persistir el registro. La generación de la descripción con IA ocurre en el cliente Android, antes
de llamar a la API.

Mantener esa justificación sería sostener una restricción que el código desmiente. Se retira.

### 7.3 Restricciones que sí se sostienen

El flujo de creación escribe objetos reales en los buckets de S3 configurados en el `.env` y
persiste registros en la base de datos apuntada por la configuración. Una prueba de carga sobre ese
endpoint genera imágenes y reportes sintéticos indistinguibles de los reales, con costo de
almacenamiento asociado. Es una razón legítima para acotar el volumen de la prueba, y se resuelve
apuntando a buckets y base de datos de prueba en lugar de renunciar a la medición.

### 7.4 Consecuencia declarada

La hipótesis de que el cuello de botella del sistema está en la subida concurrente de imágenes
permanece sin contrastar con resultados publicados, pese a existir el instrumento para hacerlo. En
la defensa oral debe presentarse así, sin atribuir la ausencia a una restricción externa.

---

## 8. Clasificación del material y trazabilidad

Las rutas corresponden a la estructura real del repositorio backend, donde la carpeta de
experimentos se llama `exp/`. La rúbrica del curso la nombra `/experimentos`; conviene unificar el
nombre antes de la entrega.

| Material | Clasificación | Destino y razón |
|---|---|---|
| Salida cruda de las 6 corridas (texto plano, pendiente de subir) | EXPERIMENTO | Debe versionarse dentro de `exp/`, sin reformatear — hoy `exp/` solo contiene un archivo de marcador (`test.txt`) |
| `Pruebas/prueba2.js` — script de autenticación | EXPERIMENTO | Vive hoy en la rama `main`. Es el artefacto que permite re-ejecutar la medición reportada |
| `Pruebas/prueba1.js` — script de creación de reportes | EXPERIMENTO | Instrumenta ESC-01. Sin resultados publicados, ver sección 7.1 |
| Perfil de carga en cuatro etapas | DOSSIER | Sección 4 de este documento |
| Cifras de p95, mediana, throughput y errores | DOSSIER | Sección 5 de este documento |

### 8.1 Tabla de trazabilidad

| Driver (doc 01) | Atributo (doc 03) | Escenario | Estado | Resultado |
|---|---|---|---|---|
| Acceso de ciudadanos al servicio de reporte | Rendimiento | ESC-07 — autenticación concurrente bajo escalado agresivo | Medido en entorno local | p95 mediano 31,06 s, tasa de error mediana 11,11% (sobre 5 corridas, tras descartar 1 de calentamiento), hasta 800 VUs. Causa candidata: servidor de desarrollo de Flask sin concurrencia real |
| RNF #1 — reporte en menos de 90 s | Rendimiento | ESC-01 — creación concurrente con imagen | Instrumentado, sin resultados publicados | Ver sección 7.1 |
| Punto único de falla en EC2 | Disponibilidad | ESC-02 — caída del backend | Descartado para esta entrega | No aplica al montaje local |
| Ley 1581/2012 | Seguridad | ESC-04 — acceso anónimo a S3 | Sin ejecutar | Hipótesis |
| Sin ambiente de staging | Desplegabilidad | ESC-05 — despliegue defectuoso | Descartado para esta entrega | Pipeline inactivo |
| RNF #2 — enrutamiento a entidad competente | Interoperabilidad | ESC-06 — clasificación del reporte | Sin ejecutar | Hipótesis |

---

## 9. Declaración de uso de IA

| Pregunta | Respuesta |
|---|---|
| ¿Qué herramienta se usó? | Claude (Anthropic), en sesión de apoyo y orientación del 20 de agosto de 2026 |
| ¿Para qué se usó? | Obtener guía y retroalimentación para la estructuración de escenarios en formato de seis partes, solicitar recomendaciones para abordar la sección de amenazas a la validez, orientar el método de cálculo de medianas a partir de las salidas de k6, y recibir sugerencias sobre el esquema del documento y puntos clave a inspeccionar en el repositorio para contrastar con el código. |
| ¿Qué se aceptó? | La propuesta de estructura para el formato de seis partes; la orientación sugerida para la sección "qué invalidaría esta medición"; la recomendación metodológica de reportar la mediana junto al rango completo; y los borradores orientativos para los escenarios ESC-02, ESC-03 y ESC-05, sujetos a la corrección registrada en la sección 3. |
| ¿Qué se modificó? | Se corrigió la sugerencia inicial de marcar la semilla como pendiente: el equipo precisó que se trata de credenciales fijas de prueba elegidas deliberadamente, incorporando esa precisión y su efecto sobre la validez. Asimismo, se ajustó la orientación sobre el entorno del escenario ESC-07, el cual Claude había supuesto en la instancia EC2, cuando la revisión directa del equipo sobre el script confirmó que apuntaba a un contenedor local. |
| ¿Qué se rechazó? | La sugerencia de argumentación que la IA había propuesto para excluir la medición de creación de reportes, una vez que el análisis del equipo sobre el código la desmintió. Se rechazó también la propuesta de nomenclatura de carpeta `EXP-001` sugerida por la IA, en favor de `exp/`, que es la que realmente existe en el repositorio backend. |
| ¿Qué supuesto de IA fue problemático? | El más grave: Claude sugirió y fundamentó en su orientación, como si fuera una restricción arquitectónica, que el flujo de creación de reportes invoca la API de Gemini y que medirlo bajo carga expondría al proyecto a un bloqueo del servicio externo. La inspección del equipo en `app/routes.py` y `app/utils.py` demostró que el backend no contiene ninguna referencia a Gemini ni realiza llamadas HTTP salientes (la generación ocurre en el cliente Android). Claude había construido una recomendación técnicamente coherente sobre una premisa falsa. Un segundo supuesto: Claude orientó el análisis asumiendo que la medición ocurría en la instancia EC2, cuando se ejecutó contra un contenedor local con el servidor de desarrollo de Flask. |
| ¿Cómo se verificó? | Ejecución real de k6 realizada por el equipo (seis corridas, cinco reportadas tras descartar la de calentamiento) y métricas leídas del resumen del instrumento. Inspección manual del repositorio: `app/routes.py`, `app/utils.py`, `app.py`, `dockerfile`, `requirements.txt`, y los scripts `Pruebas/prueba1.js` y `Pruebas/prueba2.js` de la rama `main`. La URL base y el perfil de carga del script confirmaron el entorno y la ausencia de un umbral declarado. |
| ¿Qué riesgo permanece? | La hipótesis del cuello de botella en la subida de imágenes sigue sin contrastar con resultados publicados. El resultado disponible describe un contenedor local con servidor de desarrollo, no la configuración de producción, y por tanto no acota la capacidad real del sistema. Persiste además, sin causa identificada, la anomalía de la corrida 1 (493 iteraciones interrumpidas frente a 53-204 en las demás), por ausencia de métricas del lado servidor durante las corridas. |
