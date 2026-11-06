# 06 · Riesgos residuales y limitaciones

La seguridad de UrbanFix **no queda resuelta** con este entregable: se diseñaron controles, ninguno de los nuevos está
implementado todavía. Este archivo separa lo diseñado, lo implementado y lo verificado.

## 1. Estado de los controles

| Control | Diseñado | Implementado | Verificado | Prueba que lo demuestra |
|---|---|---|---|---|
| BASE-01 Hash de contraseñas | ✅ | ✅ | ✅ | `test_base_contrasenas_se_guardan_con_hash` |
| BASE-02 Hash fuera de respuestas | ✅ | ✅ | ✅ | `test_base_login_no_devuelve_el_hash` |
| BASE-03 Consultas parametrizadas | ✅ | ✅ | ✅ | `test_base_orm_parametriza_consultas` |
| BASE-04 `.env` fuera del repo | ✅ | ✅ | ✅ (revisión manual del historial) | `05/hallazgos-repositorio.md` |
| CTL-01 … CTL-11, CTL-13, CTL-14 | ✅ | ❌ | ❌ (20 pruebas en XFAIL) | `tests/security/` |
| CTL-12 IAM / S3 | ✅ | ❓ | ❌ | Sin acceso a la cuenta AWS |

## 2. Qué riesgos se reducen y cuáles permanecen (si se implementa todo)

| Riesgo | Nivel actual | Nivel residual esperado | Qué permanece |
|---|---|---|---|
| SEG-01 Suplantación | 9 | 2 | Robo de token en dispositivo comprometido; ventana de 15 min sin revocación |
| SEG-02 IDOR | 9 | 2 | Rutas nuevas que olviden la política (mitiga la fitness function) |
| SEG-03 Privilegios | 9 | 3 | Abuso interno de un funcionario legítimo dentro de su entidad |
| SEG-04 Datos personales | 9 | 3 | Reportes públicos con ubicación e imágenes que pueden contener rostros o placas |
| SEG-05 Repositorio | 9 | 3 | Clones y *forks* previos del volcado: irrecuperables |
| SEG-06 Login | 6 | 3 | Ataques distribuidos desde muchas IP; enumeración por el registro (409) |
| SEG-07 TLS | 6 | 2 | Sin *certificate pinning* |
| SEG-08 Imágenes | 6 | 2 | Moderación de contenido |
| SEG-09 Configuración | 6 | 2 | Error humano al activar `FLASK_DEBUG` |
| SEG-10 Errores | 4 | 1 | — |
| SEG-11 Secretos del cliente | 6 | 2 | Clave antigua en el historial (ya rotada) |
| SEG-12 AWS | 6 | 2–6 | Depende del estado real de la cuenta, no verificado |
| SEG-13 Cadena de entrega | 3 | 2 | Riesgo de proveedor (GitHub) |
| SEG-14 Auditoría | 3 | 2 | Sin alertas en tiempo real |

## 3. Aspectos que no pudieron verificarse

- Configuración real de la cuenta AWS (políticas IAM, *Block Public Access* de los buckets, Security Group de EC2).
- Si la instancia EC2 `54.144.11.53` sigue encendida: **no se probó deliberadamente** (fuera del alcance autorizado).
- Si la base de datos de Neon contiene los mismos datos que la carpeta `data/`.
- Si los correos del volcado corresponden a cuentas reales activas (se asume que sí, por prudencia).
- El impacto en latencia de CTL-01 (verificar JWT es barato frente a `scrypt`, pero no se midió).

## 4. Supuestos que cambiarían el análisis

| Supuesto | Si cambia… |
|---|---|
| El sistema sigue siendo un piloto con pocos usuarios | Con datos de miles de ciudadanos, SEG-04 y SEG-05 exigirían además cifrado en reposo y un registro ante la SIC |
| El despliegue EC2 está inactivo | Si se reactiva, SEG-13 sube a 6 (Alto) y SEG-09 a 9 |
| El monolito sigue en un solo proceso (ADR 0001/0004) | Si se distribuye, aparece autenticación servicio-a-servicio y nuevos límites de confianza |
| Los repositorios son públicos | Si se vuelven privados, SEG-05 y SEG-11 bajan de probabilidad, pero la exposición pasada permanece |
| La app es el único cliente | No cambia nada: el análisis ya asume que cualquier cliente HTTP puede llamar a la API |
