<a name="inicio"></a>
<h1 align="center"><img src="assets/readme/hero.svg" width="100%" alt="UrbanFix Backend. Este es el repositorio del servidor backend para UrbanFix, una aplicación móvil diseñada para reportar daños o incidencias en el espacio público de manera rápida y eficiente. El objetivo de este backend es gestionar toda la lógica de negocio, autenticación de usuarios/funcionarios, creación de reportes, y el almacenamiento de datos (PostgreSQL) e imágenes (AWS S3). El servidor está construido en Python usando el framework Flask."></h1>

<p align="center">
  <a href="#tecnologias"><b>Tecnologías</b></a> &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="#estado"><b>Estado del despliegue</b></a> &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="#desarrollo"><b>Desarrollo local</b></a> &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="#pruebas"><b>Pruebas de carga</b></a> &nbsp;&nbsp;|&nbsp;&nbsp;
  <a href="#despliegue"><b>Despliegue y CI/CD</b></a>
</p>

<br>

<a name="tecnologias"></a>
<p align="center"><img src="assets/readme/tecnologias.svg" width="100%" alt="Tecnologías: Lenguaje Python 3.10+; Framework Flask (con Blueprints); Base de Datos PostgreSQL (gestionada en Neon); ORM SQLAlchemy con Flask-Migrate (para migraciones); Servidor de App (Producción) Gunicorn; Almacenamiento (Archivos) AWS S3 (para imágenes de reportes y fotos de perfil); Contenedores Docker; Despliegue Continuo GitHub Actions."></p>

<br>

<a name="estado"></a>
<p align="center"><img src="assets/readme/estado.svg" width="100%" alt="Nota sobre el estado actual del despliegue. Este README documenta dos configuraciones distintas que conviven en el proyecto: 1. Configuración original del proyecto: despliegue en una instancia AWS EC2, con GitHub Actions para CI/CD; no representa el flujo de trabajo actual. 2. Configuración actual (activa): el backend se ejecuta dentro de un contenedor Docker, de momento solo local. Es decir: el flujo con EC2 + GitHub Actions no ha sido eliminado del repositorio, pero actualmente no se está usando. El flujo vigente para correr el proyecto es Docker en local."></p>

<br>

<a name="desarrollo"></a>
<h2><img src="assets/readme/seccion-desarrollo.svg" width="100%" alt="Configuración para Desarrollo Local"></h2>

### Opción A (actual): Usando Docker

1. **Clona el repositorio:**
    ```bash
    git clone https://github.com/FelipeAguilar302/backend_urbanfix.git
    cd backend_urbanfix
    ```

2. **Crea tu archivo `.env`:**
    Crea un archivo llamado `.env` en la raíz del proyecto. Este archivo **no** se sube a Git. Usa esta plantilla basada en `config.py`:
    ```ini
    # --- Base de Datos (NEON) ---
    # Solo se usan si NO existe DATABASE_URL (ver nota más abajo).
    PGHOST="[Tu Host de Neon]"
    PGUSER="[Tu Usuario de Neon]"
    PGPASSWORD="[Tu Contraseña de Neon]"
    PGDATABASE="neondb"
    # --- AWS S3 ---
    AWS_ACCESS_KEY_ID="[Tu Key ID de S3]"
    AWS_SECRET_ACCESS_KEY="[Tu Secret Key de S3]"
    AWS_REGION="[Tu Región de S3, ej: us-east-1]"
    S3_REPORTES="urbanfiximagenesbucket"
    S3_PERFILES="urbanfixperfilimagenesbucket"
    ```

    > [!TIP]
    > **Nota sobre la base de datos:** `config.py` usa `DATABASE_URL` si existe, y solo si no existe cae a las variables `PGHOST`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` (Neon). Al levantar el proyecto con `docker compose` (paso 3), `DATABASE_URL` ya viene definida en `docker-compose.yml` apuntando a la base de datos local del propio `docker compose`, así que las variables de Neon en el `.env` no son necesarias para este flujo — solo hacen falta las de AWS S3.

3. **Levanta los servicios con Docker Compose:**
    ```bash
    docker compose up -d --build backend
    ```
    Este comando construye la imagen del backend y, al estar `backend` declarado con `depends_on: [db]` en `docker-compose.yml`, también levanta automáticamente el servicio `db` (PostgreSQL 16 local, contenedor `urbanfixdb`). Ambos quedan conectados entre sí en la red que crea Docker Compose, sin que tengas que configurar nada manualmente.

    El servidor estará disponible en `http://127.0.0.1:5000/` y la base de datos en el puerto `5432` de tu máquina.

    Para ver los logs: `docker compose logs -f backend`. Para detener todo: `docker compose down`.

    > [!TIP]
    > **Alternativa (sin Postgres local):** si prefieres correr solo el backend contra tu base de datos de Neon (sin levantar el servicio `db`), puedes seguir usando `docker build -t urbanfix-backend .` seguido de `docker run -p 5000:5000 --env-file .env urbanfix-backend`. En ese caso sí necesitas completar las variables de Neon en el `.env`.

> [!NOTE]
> **Nota:** Las migraciones de base de datos (`flask db upgrade`) deben ejecutarse dentro del contenedor del backend, contra la base de datos que esté activa según `DATABASE_URL` (local, si usaste `docker compose`) o contra Neon (si usaste el flujo alternativo). Con Docker Compose:
> ```bash
> docker compose exec backend flask db upgrade
> ```


<details>
<summary><strong>Opción B (alternativa): Sin Docker, con entorno virtual</strong></summary>


Si prefieres no usar Docker, también puedes correr el proyecto de forma tradicional:

1.  **Crea y activa un entorno virtual:**
    ```bash
    # En macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    
    # En Windows (CMD)
    python -m venv venv
    venv\Scripts\activate
    ```
2.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Crea tu archivo `.env`** (mismo formato mostrado arriba).
4.  **Ejecuta las migraciones de la base de datos:**
    ```bash
    # (Asegúrate de que tu venv esté activado)
    
    # En macOS/Linux
    export FLASK_APP=app.py 
    
    # En Windows (CMD)
    set FLASK_APP=app.py
    
    # Ejecuta la migración
    flask db upgrade
    ```
5.  **¡Corre el servidor!**
    ```bash
    flask run --debug
    ```
    El servidor estará disponible en `http://127.0.0.1:5000/`.

</details>

<br>

<a name="pruebas"></a>
<h2><img src="assets/readme/seccion-pruebas.svg" width="100%" alt="Pruebas de carga (k6)"></h2>


El repositorio incluye dos scripts de carga en `Pruebas/` (`prueba1.js` para `POST /reportes`, `prueba2.js` para `POST /login`). No hace falta instalar k6: se ejecutan con la imagen oficial de Docker, pasándole el script por entrada estándar.

Con el backend ya corriendo (ver [Configuración para Desarrollo Local](#desarrollo)):

```powershell
# Windows (PowerShell)
Get-Content Pruebas\prueba2.js | docker run --rm -i grafana/k6 run -
```

```bash
# macOS/Linux
docker run --rm -i grafana/k6 run - < Pruebas/prueba2.js
```

> [!WARNING]
> **Nota:** `prueba2.js` apunta al endpoint fijo `http://172.18.0.1:5000/login` (la IP de gateway de la red bridge por defecto de `docker run`). Si el backend se levantó con `docker compose` en lugar de `docker run` suelto, esa IP puede no ser la del gateway correcto — verifícala antes de correr la prueba, o ajusta la URL en el script.

<br>

<a name="despliegue"></a>
<h2><img src="assets/readme/seccion-despliegue.svg" width="100%" alt="Despliegue y CI/CD"></h2>

> [!IMPORTANT]
> **Importante:** Esta sección describe la configuración de despliegue **original** del proyecto. Actualmente **no está activa** como flujo de trabajo principal; el proyecto se corre localmente vía Docker (ver arriba). Se conserva esta documentación como referencia histórica/futura, en caso de que se retome el despliegue en la nube.

<p align="center"><img src="assets/readme/despliegue.svg" width="100%" alt="Este proyecto fue configurado en su momento para despliegue continuo usando GitHub Actions. Servidor: AWS EC2 (t2.micro) corriendo Ubuntu. IP del Servidor: http://54.144.11.53:5000 (IP Elástica permanente). Proceso: El servidor corre como un servicio systemd (urbanfix.service) usando Gunicorn. El flujo de despliegue automático (original) era el siguiente: 1. Un desarrollador hace git push a la rama main. 2. GitHub Actions se activa automáticamente. 3. La Acción se conecta por SSH al servidor EC2. 4. Ejecuta git pull para descargar los nuevos cambios. 5. Reinicia el servicio (sudo systemctl restart urbanfix) para aplicar las actualizaciones."></p>

<p align="right"><a href="#inicio">Volver arriba</a></p>
