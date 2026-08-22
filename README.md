# UrbanFix Backend
Este es el repositorio del servidor backend para UrbanFix, una aplicación móvil diseñada para reportar daños o incidencias en el espacio público de manera rápida y eficiente.
El objetivo de este backend es gestionar toda la lógica de negocio, autenticación de usuarios/funcionarios, creación de reportes, y el almacenamiento de datos (PostgreSQL) e imágenes (AWS S3). El servidor está construido en Python usando el framework Flask.

---

## Tecnologías 
* **Lenguaje:** Python 3.10+
* **Framework:** Flask (con Blueprints)
* **Base de Datos:** PostgreSQL (gestionada en [Neon](https://neon.tech/))
* **ORM:** SQLAlchemy con Flask-Migrate (para migraciones)
* **Servidor de App (Producción):** Gunicorn
* **Almacenamiento (Archivos):** AWS S3 (para imágenes de reportes y fotos de perfil)
* **Contenedores:** Docker
* **Despliegue Continuo:** GitHub Actions

---

## Nota sobre el estado actual del despliegue

Este README documenta **dos configuraciones distintas** que conviven en el proyecto, para evitar confusiones:

1. **Configuración original del proyecto:** despliegue en una instancia **AWS EC2**, con **GitHub Actions** para CI/CD (descrita en la sección [Despliegue y CI/CD](#despliegue-y-cicd) más abajo). Esta configuración sigue documentada porque fue parte del diseño original del proyecto, pero **no representa el flujo de trabajo actual**.
2. **Configuración actual (activa):** el backend ahora se ejecuta dentro de un **contenedor Docker**, y **de momento el uso de Docker es solo local** (para desarrollo). No hay, por ahora, un pipeline de CI/CD ni despliegue en EC2 usando la imagen Docker.

Es decir: **el flujo con EC2 + GitHub Actions no ha sido eliminado del repositorio, pero actualmente no se está usando**. El flujo vigente para correr el proyecto es Docker en local.

---

## Configuración para Desarrollo Local

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

3. **Construye la imagen Docker:**
    ```bash
    docker build -t urbanfix-backend .
    ```

4. **Corre el contenedor:**
    ```bash
    docker run -p 5000:5000 --env-file .env urbanfix-backend
    ```

    El servidor estará disponible en `http://127.0.0.1:5000/`.

> **Nota:** Las migraciones de base de datos (`flask db upgrade`) deben ejecutarse contra la base de datos de Neon configurada en el `.env`. Si necesitas correrlas manualmente dentro del contenedor, puedes hacerlo con:
> ```bash
> docker exec -it <container_id> flask db upgrade
> ```

---

### Opción B (alternativa): Sin Docker, con entorno virtual

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

---

## Despliegue y CI/CD

> **Importante:** Esta sección describe la configuración de despliegue **original** del proyecto. Actualmente **no está activa** como flujo de trabajo principal; el proyecto se corre localmente vía Docker (ver arriba). Se conserva esta documentación como referencia histórica/futura, en caso de que se retome el despliegue en la nube.

Este proyecto fue configurado en su momento para **despliegue continuo** usando **GitHub Actions**.

* **Servidor:** AWS EC2 (t2.micro) corriendo Ubuntu.
* **IP del Servidor:** `http://54.144.11.53:5000` (IP Elástica permanente).
* **Proceso:** El servidor corre como un servicio `systemd` (`urbanfix.service`) usando Gunicorn.

**El flujo de despliegue automático (original) era el siguiente:**
1.  Un desarrollador hace `git push` a la rama `main`.
2.  GitHub Actions se activa automáticamente.
3.  La Acción se conecta por SSH al servidor EC2.
4.  Ejecuta `git pull` para descargar los nuevos cambios.
5.  Reinicia el servicio (`sudo systemctl restart urbanfix`) para aplicar las actualizaciones.
