# UrbanFix — Escenarios de Calidad y Medición de Línea Base

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Documentos previos:** [01](./01-contexto-sistema.md) · [02](./02-stakeholders-drivers.md) · [03](./03-atributos-calidad.md)

Este documento convierte los atributos priorizados en escenarios verificables y mide al menos uno
contra el sistema real, con herramienta, método, condiciones y datos. Corresponde a la evidencia
obligatoria de la semana 4 y es el único de la serie 01–04 que no puede escribirse sin ejecutar.

El criterio de la rúbrica es explícito: una medición sin datos, condiciones y método reproducible
no se considera medición. El docente puede pedir re-ejecutarla en vivo en cualquier corte, según
lo previsto en la sección 7.

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
| **Medida** | p95 de latencia ≤ ___ ms · tasa de error ≤ ___ % con N = ___ usuarios concurrentes |

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
| **Medida** | Tiempo hasta mostrar mensaje de error ≤ ___ s · el borrador del reporte se conserva: sí/no |

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
| **Medida** | Timeout configurado ≤ ___ s · el reporte se crea igualmente: sí/no |

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
| **Medida** | Respuesta HTTP 403 en el 100% de los intentos anónimos |

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
| **Medida** | El build falla: sí/no · tiempo de detección ≤ ___ min |

**Atributo:** Desplegabilidad, Mantenibilidad · **Prioridad:** Alta
*(Este escenario es el que se automatiza como función de aptitud en CI — semanas 12–14.)*

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
| **Medida** | ___ % de asignaciones correctas sobre un conjunto de ___ casos de prueba con entidad esperada conocida |

**Atributo:** Interoperabilidad, Mantenibilidad · **Prioridad:** Alta

---

### 2.7 Registro de escenarios generados por IA y corregidos por el equipo

Entregable exigido por la rúbrica. Los escenarios marcados IA-C nacieron de una propuesta generada
con asistencia de IA. Esta tabla documenta qué estaba mal en la propuesta original y qué corrigió
el equipo. Un escenario que pasa sin corrección es una señal de alerta: casi siempre significa que
no se contrastó contra el sistema real.

| ESC | Propuesta original de la IA | Problema detectado por el equipo | Versión corregida | Fundamento de la corrección |
|---|---|---|---|---|
| ESC-02 | | *(ej.: medida no verificable / umbral arbitrario / no contextualizado al sistema)* | | *(código, arquitectura, restricción o norma que lo sustenta)* |
| ESC-03 | | | | |
| ESC-05 | | | | |

**Escenarios rechazados por completo:**

| Escenario propuesto | Por qué se descartó |
|---|---|
| | |

---

## 3. Escenario seleccionado para la medición de línea base

**Escenario elegido:** ESC-___

**Justificación de la elección:** *(por qué este y no otro — debe apuntar a la priorización del
documento 03)*

---

## 4. Método de medición

Todo lo de esta sección se completa antes de ejecutar. Es el método reproducible que exige la
rúbrica.

| Aspecto | Definición |
|---|---|
| Herramienta y versión | k6 / JMeter / Locust — versión: |
| Endpoint objetivo | |
| Carga simulada | ___ usuarios virtuales durante ___ segundos, rampa de ___ |
| Datos de prueba | ¿Imágenes sintéticas? ¿De qué tamaño? ¿Cuántas distintas? |
| Entorno medido | ¿Producción o réplica local? ¿Desde qué red y qué máquina? |
| Commit medido | `hash` |
| Métricas capturadas | p50, p95, p99, throughput, tasa de error |
| Observación del servidor | CloudWatch: CPU, memoria, red |
| Número de corridas | Mínimo 3 |

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

## 5. Resultados

*(Completar únicamente con datos de ejecución real. Ninguna celda de esta sección puede
rellenarse con una estimación.)*

**Fecha y hora de ejecución:** ___ · **Ejecutado por:** ___ · **Commit:** ___

| Métrica | Corrida 1 | Corrida 2 | Corrida 3 | Mediana |
|---|---|---|---|---|
| p50 (ms) | | | | |
| p95 (ms) | | | | |
| p99 (ms) | | | | |
| Throughput (req/s) | | | | |
| Tasa de error (%) | | | | |
| CPU máx. servidor (%) | | | | |
| Memoria máx. servidor (%) | | | | |

**Punto de saturación observado:** ___ usuarios concurrentes

---

## 6. Contraste del escenario contra el dato real

Tarea explícita del checklist, con 45 minutos asignados. No basta con reportar números: hay que
volver al escenario formulado en la sección 2 y decir si se cumplió.

| Elemento | Valor formulado en el escenario | Valor medido | ¿Se cumple? |
|---|---|---|---|
| p95 de latencia | | | |
| Tasa de error | | | |
| Concurrencia soportada | | | |

**¿Dónde está realmente el cuello de botella?**
*(CPU del backend, memoria, subida a S3, latencia de Gemini, consultas a la base de datos…)*

**¿Confirma o refuta el diagnóstico previo?**
El análisis PASS MADE afirmaba que el backend sobre `t2.micro` es el componente que limita el
desempeño global, especialmente en la subida concurrente de imágenes a S3. Contrastar esa
afirmación con los datos obtenidos.

Una refutación bien documentada vale más que una confirmación sin datos. Si la medición muestra
que el cuello de botella está en otro lado, ese hallazgo es el material más fuerte para la fila de
"Uso de IA" de la rúbrica y para la defensa oral.

**¿Hay que corregir el umbral del escenario?** Si la medida formulada resultó arbitraria o
irrealizable, decirlo y ajustarla — dejando registro del valor anterior.

**Decisión derivada y ADR asociado:**

---

## 7. Reproducibilidad y re-ejecución

El docente puede pedir re-ejecutar esta medición en vivo, en cualquier corte. Si hace falta
recordar cómo se corría, la medición no es reproducible.

**Ubicación de los artefactos:** `/experimentos/medicion-escenario-XX/`

Contenido obligatorio de esa carpeta:

| Archivo | Contenido |
|---|---|
| `README.md` | Cómo re-ejecutar, en un solo comando |
| `carga.js` (o equivalente) | Script de la prueba de carga |
| `config/` | Configuración exacta usada |
| `datos-prueba/` | Imágenes sintéticas y su generador |
| `resultados/` | Salida cruda de cada corrida, sin editar |
| `resumen.md` | Este análisis en versión corta |

**Comando único de re-ejecución:**

```bash
# ejemplo — ajustar a la herramienta elegida
k6 run experimentos/medicion-escenario-XX/carga.js
```

Ensayen la re-ejecución una vez antes del corte, desde una carpeta limpia y con otro integrante
al teclado. Si no corre a la primera, el `README.md` está incompleto.

### 7.1 Nivel avanzado (opcional, sin nota)

- Medir un segundo escenario: disponibilidad (ESC-02) o consumo de recursos.
- Parametrizar el script de carga para que la re-medición del módulo 6 sea el mismo comando con
  otro valor de concurrencia. Vale la pena: en las semanas 11–12 hay que volver a medir para la
  comparación antes/después, y tenerlo automatizado ahorra una tarde completa.

---

## 8. Declaración de uso de IA

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

*(Ver también el registro detallado de escenarios corregidos en §2.7.)*
