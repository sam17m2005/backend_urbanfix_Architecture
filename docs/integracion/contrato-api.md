# UrbanFix — Contratos API: Mapa de Reportes e Inicio de Sesión

**Proyecto:** UrbanFix — Aplicación móvil para el reporte de problemáticas urbanas
**Ámbito:** Ciudades y localidades urbanas (contexto de referencia: Bogotá D.C.)
**Asignatura:** Arquitectura de Software — Universidad de Bogotá Jorge Tadeo Lozano
**Autores:** Johan Felipe Aguilar Castillo · Samuel Alejandro González Grajales · Juan David Barragán
**Módulo:** 5 — Semana 10 · Contratos e interfaces de integración
**Documentos previos:** [subdominios.md](./subdominios.md) · [responsabilidades-contextos.md](./responsabilidades-contextos.md) · [context-map.md](./context-map.md) · [decision-integracion.md](./decision-integracion.md)
**Fuente:** Elaboración propia a partir de `app/routes.py` y `app/models.py` del backend (`backend_urbanfix_Architecture`) y de su uso en el cliente Android (`UrbanFix_Architecture`).

> La especificación formal (OpenAPI 3.0) de ambos contratos está en
> [contrato-api.yml](./contrato-api.yml). Las rutas del cliente se citan con el prefijo `android:` y
> son relativas a `app/src/main/java/com/example/urbanfix/`.

---

## 1. Alcance

El equipo eligió formalizar dos operaciones que **ya existen** y que la app Android usa hoy. Este
documento no agrega capacidades nuevas: describe el comportamiento observable actual, lo que cada
contrato protege y lo que falta decidir para que el contrato sea suficientemente explícito.

| Contrato | Operación | Proveedor | Consumidor | Integración |
|---|---|---|---|---|
| **A · Mapa de reportes** | `GET /reportes/geojson` | Gestión de Reportes | Pantalla de mapa de la app | Síncrona (REST) |
| **B · Inicio de sesión** | `POST /login` | Identidad y Acceso | Pantalla de login de la app | Síncrona (REST) |

Ambos son síncronos porque el usuario espera la respuesta en pantalla: el mapa no se puede dibujar
sin los puntos, y la app no puede continuar sin saber el rol del actor.

---

## 2. Contrato A — Mapa de reportes

### 2.1 Especificación conceptual

| Campo | Definición |
|---|---|
| **Proveedor** | Gestión de Reportes (BC-2) |
| **Consumidor** | App Android — pantalla de mapa (`android:viewmodel/MapaViewModel.kt`, `android:screens/MapaScreen.kt`) |
| **Capacidad expuesta** | Obtener los reportes como puntos geográficos para mostrarlos en el mapa. |
| **Datos de entrada** | Ninguno. |
| **Datos de salida** | FeatureCollection GeoJSON. Por cada reporte: coordenadas `[longitud, latitud]`, `id`, `nombre` (subtipo del daño), `categoria` y `estado`. |
| **Errores conocidos** | `500` con `{ "error": "Error interno al generar GeoJSON" }`. |
| **Información que no se expone** | Descripción, dirección, referencia, fotos, creador del reporte, funcionario asignado y respaldo comunitario. Para verlos, la app abre el detalle con el `id`. |
| **Versionamiento** | Sin versión en la ruta. Pendiente de decisión (§5). |

### 2.2 Lo que el contrato NO permite

- Crear, editar o eliminar reportes.
- Cambiar el estado de un reporte.
- Filtrar en el servidor por categoría, estado o zona (lo hace la app sobre la respuesta).
- Obtener el detalle completo de un reporte (para eso existe `GET /reportes/{id}`).
- Saber quién creó el reporte o qué funcionario lo atiende.

### 2.3 Respuesta exitosa — HTTP 200

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [-74.114567, 4.571234] },
      "properties": { "id": 42, "nombre": "Hueco profundo", "categoria": "Huecos", "estado": "En proceso" }
    }
  ]
}
```

### 2.4 Error — HTTP 500

```json
{ "error": "Error interno al generar GeoJSON" }
```

---

## 3. Contrato B — Inicio de sesión

### 3.1 Especificación conceptual

| Campo | Definición |
|---|---|
| **Proveedor** | Identidad y Acceso (BC-1) |
| **Consumidor** | App Android — pantalla de login (`android:viewmodel/LoginViewModel.kt`) |
| **Capacidad expuesta** | Verificar las credenciales de un ciudadano o de un funcionario y devolver su rol y sus datos de perfil. |
| **Datos de entrada** | `email` y `contrasena`, ambos obligatorios. |
| **Datos de salida** | `message`, `role` (`usuario` o `funcionario`) y `user_data`. Para un ciudadano: id, nombre, email, teléfono, fecha de registro y foto de perfil. Para un funcionario: además cargo, legajo, id y nombre de su entidad. |
| **Errores conocidos** | `400` falta el correo o la contraseña · `401` contraseña incorrecta · `404` no existe una cuenta con ese correo. Todos con `{ "message": "..." }`. |
| **Información que no se expone** | La contraseña ni su hash. Los datos de otros usuarios. |
| **Versionamiento** | Sin versión en la ruta. Pendiente de decisión (§5). |

### 3.2 Lo que el contrato NO permite

- Registrar una cuenta nueva (para eso existen `POST /usuarios` y `POST /funcionarios`).
- Cambiar la contraseña o los datos del perfil.
- Consultar datos de otra persona.
- Cambiar el rol del actor o su entidad.

### 3.3 Respuesta exitosa — HTTP 200

```json
{
  "message": "Inicio de sesión exitoso",
  "role": "usuario",
  "user_data": {
    "id": 7,
    "nombre": "Ana Pérez",
    "email": "ana.perez@correo.com",
    "telefono": "3001234567",
    "fecha_registro": "2026-08-14T15:32:10",
    "foto_perfil_url": "https://urbanfixperfilimagenesbucket.s3.us-east-1.amazonaws.com/3f1c2a.png"
  }
}
```

### 3.4 Errores

| Código | Cuándo | Cuerpo |
|---|---|---|
| `400` | Falta el correo o la contraseña | `{ "message": "Faltan email o contraseña" }` |
| `401` | La cuenta existe pero la contraseña no coincide | `{ "message": "Credenciales incorrectas" }` |
| `404` | No existe ninguna cuenta con ese correo | `{ "message": "La cuenta no existe. Por favor, regístrate." }` |

---

## 4. Auditoría de los contratos

Se revisa si cada contrato es suficientemente explícito según los criterios del módulo. Cada celda
empieza con **Explícito**, **Ambiguo** (ambiguo o contradictorio) o **Pendiente** (falta una decisión
del equipo).

| Criterio | A · Mapa de reportes | B · Inicio de sesión |
|---|---|---|
| **Operación** | **Explícito.** Una sola operación de lectura, clara. | **Explícito.** Una sola operación, clara. |
| **Entradas** | **Explícito.** No tiene. | **Ambiguo.** No se define si el correo distingue mayúsculas (hoy sí las distingue: `filter_by(email=...)`). |
| **Salidas** | **Ambiguo.** El comentario del código dice que devuelve solo reportes "Nuevos o En proceso", pero el filtro incluye `Resuelto` (`app/routes.py:819-824`). Los reportes sin estado no aparecen. | **Ambiguo.** `user_data` cambia de forma según el rol. La app los lee con una sola clase (`android:network/NetworkModels.kt:15-22`) y no recibe cargo ni legajo. |
| **Errores** | **Ambiguo.** Solo `500`. El cuerpo usa la clave `error`, mientras que el login usa `message`: no hay un formato de error común. | **Ambiguo.** Un fallo de base de datos no está controlado: Flask responde un `500` en HTML, no en JSON. Bajo carga (ESC-07) hubo peticiones fallidas, y el contrato no describe qué recibe la app en ese caso. |
| **Responsabilidades** | **Explícito.** Solo lectura; no modifica nada. | **Ambiguo.** Si un correo existe como ciudadano y como funcionario, siempre gana el ciudadano (`app/routes.py:56`) y el funcionario nunca puede entrar. |
| **Límites** | **Ambiguo.** Devuelve **todos** los reportes, sin paginación ni límite. | **Ambiguo.** El `404` revela si un correo está registrado, aunque la contraseña sea falsa. |
| **Versionamiento** | **Pendiente.** No hay versión en la ruta. | **Pendiente.** No hay versión en la ruta. |
| **Compatibilidad** | **Ambiguo.** La app compara el nombre de la categoría con textos fijos ("huecos", "alumbrado publico", "basura acumulada"…) y el estado con su texto (`android:screens/MapaScreen.kt:281-317`): renombrar una categoría o un estado en la base de datos rompe los filtros del mapa sin dar error. | **Ambiguo.** La app muestra el texto de `message` al usuario (`android:viewmodel/LoginViewModel.kt:53-58`): cambiar ese texto cambia lo que ve el usuario. No hay un código de error estable. |

**Observación transversal:** el login no devuelve un token de sesión. La app guarda el id y el rol, y
los reenvía en otras operaciones sin que el backend pueda verificarlos. No es un defecto de este
contrato, pero sí un límite de lo que el contrato B garantiza: confirma la identidad **una vez**, no en
cada petición.

---

## 5. Decisiones pendientes del equipo

La auditoría no completa estas decisiones; las deja planteadas para que el equipo las tome.

| # | Contrato | Pregunta |
|---|---|---|
| 1 | A y B | ¿Se agrega la versión a la ruta (`/api/v1/...`) aunque eso obligue a actualizar la app, o se mantiene la ruta actual y se versiona por otro medio? |
| 2 | A | ¿El mapa debe mostrar los reportes `Resuelto`? El código los incluye, pero su comentario dice que no. |

---
