# 10 · Seguridad de UrbanFix — documento de entrada

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Fecha:** 2026-11-06
**Estado de `main` al redactarlo:** commit `644adcc`
**Qué es este documento:** el punto de entrada del análisis de seguridad. Resume y enlaza el trabajo de [`docs/seguridad/`](./seguridad/) (01 a 08); no lo duplica. El detalle de cada riesgo está en la [matriz 03](./seguridad/03-matriz-riesgos-controles.md).

---

## 1. Resumen ejecutivo

- Se modelaron las amenazas del **sistema completo** (backend, base de datos, S3, despliegue y cliente Android) con STRIDE y OWASP, y se identificaron **14 riesgos**: **5 críticos**, **6 altos** y **3 medios**.
- **Ningún control está implementado.** Los 14 están **propuestos**; solo hay 4 controles ya presentes en la línea base, comprobados (hash `scrypt`, el hash no sale en las respuestas, consultas parametrizadas por el ORM y `.env` ignorado).
- Los riesgos críticos de la API (SEG-01 a SEG-04) tienen una causa común: el login no emite ninguna credencial, así que el servidor no puede saber quién llama y toma la identidad de datos que envía el cliente.
- **Lo más urgente, sin código de aplicación:** retirar `data/` del repositorio y rotar la clave de Gemini del cliente. `data/` es un clúster de PostgreSQL versionado en un repositorio público que contiene **20 hashes de contraseña y más de diez correos reales** ([hallazgos](./seguridad/05-evidencias-verificacion/hallazgos-repositorio.md)).
- Los riesgos se verifican con **23 pruebas ejecutables** sobre el código real: hoy **3 pasan** (controles existentes) y **20 fallan por la razón esperada** (`xfail`).

## 2. Método

| Elemento | Qué se hizo | Dónde |
|---|---|---|
| Contexto, activos y límites de confianza | Activos A1 a A8, componentes C1 a C8 y límites TB1 a TB6 | [01](./seguridad/01-contexto-y-alcance.md), [diagrama de superficie de ataque](./seguridad/02-diagrama-superficie-ataque.png) |
| Del checklist heredado al sistema completo | Cada ítem del checklist de seguridad previo se contrasta con lo que revela el modelado | [01 §8](./seguridad/01-contexto-y-alcance.md) |
| Modelado de amenazas | STRIDE por componente y límite de confianza, con OWASP como referencia | [03](./seguridad/03-matriz-riesgos-controles.md) |
| Prioridad | Escala 3 × 3 (probabilidad × impacto): 9 crítico, 6 alto, 3–4 medio | [04](./seguridad/04-criterios-evaluacion.md) |
| Evidencia | Revisión del código y de los repositorios, y pruebas ejecutables | [05](./seguridad/05-evidencias-verificacion/README.md) |

## 3. Riesgos priorizados, con su control

**Versión de OWASP.** Los documentos 03 y 04 etiquetan con **OWASP Top Ten 2021** y **API Security Top 10 2023**. Para la edición **2025**, la más reciente, esta tabla agrega la correspondencia con la renumeración oficial: A05 → A02, A02 → A04, A03 → A05, A04 → A06, A06 → A03 (ampliada a cadena de suministro) y SSRF → A01. A01, A07, A08 y A09 no cambian de número.

| ID | Riesgo | Nivel | OWASP (doc 03, 2021) | OWASP:2025 | Control | Estado |
|---|---|---|---|---|---|---|
| SEG-01 | Suplantación: la API acepta cualquier identidad enviada por el cliente | **9 Crítico** | A07, API2 | A07 | CTL-01 Token firmado en el borde de la API | Propuesto |
| SEG-02 | Acceso a objetos ajenos (IDOR/BOLA) | **9 Crítico** | A01, API1 | A01 | CTL-02 Autorización por propiedad del recurso | Propuesto |
| SEG-03 | Escalamiento a funcionario con la cabecera `User-Role` o `POST /funcionarios` | **9 Crítico** | A01, API5 | A01 | CTL-03 RBAC + ABAC por entidad | Propuesto |
| SEG-04 | Volcado de datos personales de usuarios y funcionarios | **9 Crítico** | A01, API3 | A01 | CTL-04 Minimización de datos por audiencia | Propuesto |
| SEG-05 | Clúster de PostgreSQL (`data/`) y credenciales publicados en el repositorio | **9 Crítico** | A05, A02 | A02, A04 | CTL-05 Higiene del repositorio y BD aislada | Propuesto |
| SEG-06 | Fuerza bruta, enumeración de cuentas y denegación de servicio en `/login` | 6 Alto | A07, API4 | A07 | CTL-06 Límite de tasa y respuesta uniforme | Propuesto |
| SEG-07 | Contraseñas y datos en tránsito sin cifrar (HTTP) | 6 Alto | A02 | A04 | CTL-07 TLS en proxy inverso | Propuesto |
| SEG-08 | Imágenes sin límite tumban el proceso; reporte guardado con imagen inexistente | 6 Alto | API4, A04 | A06 | CTL-08 Validación de entrada y subida desacoplada | Propuesto |
| SEG-09 | Configuración insegura: `debug=True` en `0.0.0.0` y ruta `/test-deploy` | 6 Alto | A05 | A02 | CTL-09 Configuración por entorno endurecida | Propuesto |
| SEG-10 | Los errores 500 devuelven detalles internos | 4 Medio | A05 | A02 (la más cercana por contenido: A10, manejo incorrecto de condiciones excepcionales) | CTL-10 Manejador global de errores | Propuesto |
| SEG-11 | Secretos en el cliente: clave de Gemini y contraseña guardada en claro | 6 Alto | A02, A05 | A04, A02 | CTL-11 Ningún secreto en el cliente | Propuesto |
| SEG-12 | Claves AWS estáticas sin mínimo privilegio; buckets con lectura pública | 6 Alto | A05, A01 | A02, A01 | CTL-12 Rol de carga de trabajo y mínimo privilegio en S3 | Propuesto · no verificable |
| SEG-13 | Cadena de entrega: acción de terceros sin fijar, despliegue directo, dependencias sin auditar | 3 Medio | A08, A06 | A08, A03 | CTL-13 Pipeline con controles de integridad | Propuesto |
| SEG-14 | Sin rastro de auditoría de acciones sensibles | 3 Medio | A09 | A09 | CTL-14 Registro de eventos de seguridad | Propuesto |

**Orden de implementación sugerido** ([03 §4](./seguridad/03-matriz-riesgos-controles.md)): (1) inmediato y sin código de aplicación: rotar la clave de Gemini y retirar `data/`; (2) bloque de identidad: CTL-01 → CTL-02 → CTL-03 → CTL-04; (3) borde: CTL-07, CTL-06 y CTL-08 en el mismo proxy inverso; (4) endurecimiento: CTL-09, CTL-10, CTL-12, CTL-13 y CTL-14.

## 4. Amenazas genéricas descartadas

Estas amenazas aparecen con frecuencia en listas genéricas, incluidas las que sugiere una IA. Se **descartan** porque no hay superficie en este sistema, y cada descarte se puede repetir con la búsqueda indicada (resultado sobre `app/` en `main`, 2026-11-06).

| Amenaza genérica | Por qué no aplica | Cómo se comprueba | Resultado |
|---|---|---|---|
| Inyección SQL | Todo el acceso a datos pasa por el ORM, que parametriza las consultas | `grep -rnE "text\(|\.execute\(" app/` y la prueba `test_base_orm_parametriza_consultas` | 0 coincidencias; la prueba pasa |
| SSRF (incluida en A01:2025) | El backend no hace peticiones a direcciones elegidas por el usuario | `grep -rnE "requests|urllib|httpx|urlopen" app/` | 0 coincidencias |
| XSS | La API devuelve JSON a una app Android y no genera HTML dinámico | `grep -rnE "render_template|Markup" app/` | 0 coincidencias; el único HTML es la constante de `/test-deploy`, que SEG-09 elimina |
| Deserialización insegura o ejecución dinámica | No se deserializa ni se evalúa entrada del usuario | `grep -rnE "pickle|yaml\.load|eval\(|exec\(" app/` | 0 coincidencias |
| XXE | El backend no procesa XML | `grep -rnE "xml|lxml|etree" app/` | 0 coincidencias |
| Inyección de comandos | No ejecuta comandos del sistema | `grep -rnE "subprocess|os\.system|popen" app/` | 0 coincidencias |
| CSRF | No usa sesiones ni cookies: la identidad, cuando exista, viajará en un token en la cabecera | `grep -rnE "set_cookie|request\.cookies|SECRET_KEY" app/` | 0 coincidencias. Se revisaría si se adoptan cookies |
| Recorrido de rutas en archivos | No se abren rutas dadas por el usuario: las imágenes se leen como bytes en memoria y se suben con un nombre `uuid` | `grep -rnE "send_file|open\(" app/` | Solo `Image.open` sobre bytes en memoria (`app/utils.py:25` y `:55`) |

**Fuera de alcance por no tener superficie propia:** ingeniería social y phishing (no hay una superficie de la API que lo habilite); denegación de servicio volumétrica de red (se limita la tasa con CTL-06 y el [ADR 0005](../adrs/0005-politica-seguridad-observabilidad.md) descarta WAF por costo); vulnerabilidades de día cero en Flask o PostgreSQL (se atienden con `pip-audit` y Dependabot, CTL-13, y no con un control propio); y acceso físico o interno a la nube (no hubo acceso a la cuenta de AWS, ver [07](./seguridad/07-declaracion-uso-ia.md)).

## 5. Verificación automatizada

| Qué | Dónde | Estado a 2026-11-06 |
|---|---|---|
| Pruebas de los controles de seguridad | [`tests/security/`](../tests/security/test_controles_seguridad.py) | 3 pasan (controles existentes) y 20 `xfail` (riesgos confirmados, controles sin implementar) |
| Fitness function FF-01 y FF-02 (ADR 0001 y ADR 0003) | [`tests/architecture/`](../tests/architecture/test_fitness_function.py) | Verdes en CI; ya se vio romper una violación deliberada |
| Fitness function FF-03, FF-04 y FF-05 (ADR 0005) | [`test_fitness_seguridad_observabilidad.py`](../tests/architecture/test_fitness_seguridad_observabilidad.py) | **Pendientes** (`xfail` estricto): hoy detectan 34 rutas sin protección, 18 `print(` y `debug=True` con `data/` versionada. Cuando se implemente cada control, la regla pasa y el CI obliga a quitar la marca |

## 6. Despliegue y costo relativo

Se compararon tres paquetes de controles sobre la alternativa B del [ADR 0004](../adrs/0004-decision-distribucion.md) (≈ 19 USD/mes). El detalle por control está en [08](./seguridad/08-diagrama-despliegue-y-costos.md).

| Paquete | Composición | ≈ USD/mes | Índice |
|---|---|---|---|
| **P1 · Mínimo autogestionado (elegido en el ADR 0005)** | Nginx + Let's Encrypt, SSM, JWT propio, rol IAM y URLs prefirmadas | 19 | 1,0× |
| P2 · Borde gestionado | ALB + ACM, Secrets Manager, JWT propio | 43 | ≈ 2,3× |
| P3 · Todo gestionado | ALB + WAF, Cognito, CloudFront | 52 o más | ≈ 2,8× |

## 7. Observabilidad y seguridad

El riesgo SEG-14 (A09) se atiende con el registro de eventos de seguridad (CTL-14) y con la alerta A-08 del plan de observabilidad, que usa los mismos umbrales que el límite de intentos de CTL-06. El plan, la selección de riesgos OWASP y su prueba de concepto están en el pull request de observabilidad (`docs/arquitectura/plan-observabilidad.md` y `docs/arquitectura/riesgos-owasp-seleccionados.md`), pendiente de mezcla.

## 8. Riesgos residuales y limitaciones

Ver [06](./seguridad/06-riesgos-residuales-y-limitaciones.md). Lo esencial:
- Ningún control está implementado: el nivel de riesgo actual sigue siendo el de la matriz.
- Todo lo relativo a IAM y buckets de S3 es inferencia: no hubo acceso a la cuenta de AWS (SEG-12).
- La estimación de que los riesgos críticos bajan a 2–3 con CTL-01 a CTL-05 **no está verificada** hasta que las pruebas de `tests/security` pasen de `xfail` a pasar.
- Implementar la autenticación cambia el contrato con la app móvil, que vive en otro repositorio.

## 9. Trazabilidad

| Elemento | Ubicación |
|---|---|
| Análisis completo | [`docs/seguridad/`](./seguridad/) (01 a 08) |
| Decisiones | [ADR 0004](../adrs/0004-decision-distribucion.md) y [ADR 0005](../adrs/0005-politica-seguridad-observabilidad.md) |
| Pruebas y fitness functions | [`tests/security/`](../tests/security/test_controles_seguridad.py) y [`tests/architecture/`](../tests/architecture/test_fitness_seguridad_observabilidad.py) |
| Capacidad medida de `/login` (≈ 16 logins/s) | [`experimentos/crecimiento.md`](../experimentos/crecimiento.md) |
| Matrices de fallos y resiliencia | [matriz-fallos.md](./arquitectura/matriz-fallos.md) · [matriz-resiliencia.md](./arquitectura/matriz-resiliencia.md) |
| Declaración de uso de IA | [07](./seguridad/07-declaracion-uso-ia.md) |

**Uso de IA:** Claude (Anthropic) ayudó a revisar el código y los repositorios, a escribir las pruebas y las fitness functions, y a redactar este documento, junto con el resto de `docs/seguridad/` (ver 07). Las calificaciones de riesgo, la elección de controles y su aceptación son decisión del equipo.
