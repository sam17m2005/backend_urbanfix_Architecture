# ADR 0001 — Estructurar el Backend de UrbanFix utilizando una Arquitectura por Capas

**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán

**Estado:** Aceptada

---

## Contexto

El proyecto UrbanFix requería establecer una topología base para el backend que soportara autenticación, reportes ciudadanos geolocalizados y gestión de almacenamiento dual (PostgreSQL y AWS S3). El equipo de desarrollo contaba con recursos de infraestructura limitados y un tiempo de entrega ajustado. Adicionalmente, el sistema debía cumplir de manera estricta con el rendimiento dictado por el **RNF #1** (creación de reporte de punta a punta en menos de 90 s).

Las pruebas de concepto ejecutadas validaron que la ejecución centralizada procesa 312 peticiones concurrentes (15 VUs en k6) con un tiempo de respuesta p(95) de 523.32 ms. Sin embargo, pruebas de estrés destructivas (rampa hasta 800 VUs) confirmaron que, bajo alta exigencia, la base de datos se convierte en un cuello de botella físico que agota sus conexiones: a lo largo de seis ejecuciones, el check *"Status 200 (Login Exitoso)"* registró una tasa de éxito de entre 86.62% y 91.84%, con tiempos de respuesta p(95) de entre 30.95 s y 36.47 s (promedio de `http_req_duration` entre 13.35 s y 17.44 s por petición).

---

## Alternativas consideradas

### 1. Arquitectura de Microservicios Distribuidos
Consistía en aislar físicamente los dominios (Usuarios, Reportes, Catálogos) en contenedores separados comunicados por red.

**Por qué se descartó:** su costo de infraestructura era inviable para un piloto, retrasaba la entrega por la complejidad de orquestar redes internas (CI/CD) y añadía latencia de red entre servicios que ponía en riesgo el cumplimiento del RNF #1.

### 2. Arquitectura Hexagonal (Puertos y Adaptadores)
Consistía en aislar completamente la lógica de negocio de los frameworks web y bases de datos usando interfaces estrictas.

**Por qué se descartó:** la alta carga cognitiva y la cantidad de código repetitivo (boilerplate) requerido superaban el beneficio inmediato, retrasando el desarrollo de los casos de uso principales.

---

## Decisión

Se estructuró el backend de UrbanFix implementando una estricta **Arquitectura por Capas** de arriba hacia abajo:

```
Capa de Presentación → Capa de Negocio → Capa de Persistencia
```

Se aislaron lógicamente las responsabilidades utilizando enrutadores (Blueprints de Flask), y se ejecutaron todas las capas compartiendo un único espacio de memoria y un único pool de conexiones hacia PostgreSQL.

---

## Consecuencias

**Positivas (qué ganamos):**
- Se aceleró el tiempo de desarrollo y se simplificó el despliegue al manejar un único contenedor Docker (`docker-compose up`).
- Se garantizó una latencia interna mínima, ya que la comunicación entre las capas se realiza en memoria a velocidad de CPU, asegurando el cumplimiento del RNF #1.

**Negativas (qué sacrificamos):**
- Se comprometió la disponibilidad general ante fallos críticos: si la capa de Reportes sufre un desbordamiento de memoria procesando una imagen corrupta, todo el proceso de Flask se cae, inhabilitando también la autenticación.
- Todo el sistema compite por las mismas conexiones a la base de datos, lo cual quedó evidenciado en las pruebas a 800 VUs, donde hasta un 13.37% de los intentos de login fallaron y los tiempos de respuesta se degradaron hasta superar los 30 segundos en el percentil 95.

---

## Reversibilidad

**Baja.** Deshacer esta arquitectura para migrar hacia un modelo distribuido requeriría una reescritura profunda del sistema: separar los esquemas de la base de datos relacional, aislar el código en múltiples repositorios, configurar un API Gateway e implementar comunicación asíncrona por red.

---

## Supuestos

Se asumió que el tráfico de la localidad piloto será orgánico y predecible, sin picos masivos repentinos que superen la capacidad de conexiones del motor PostgreSQL antes de que el equipo pueda aprovisionar un balanceador de carga.

Este supuesto se revisará formalmente si las métricas de producción registran un tráfico sostenido superior a 100 peticiones concurrentes por segundo, momento en el cual el diseño actual podría estrangularse.
