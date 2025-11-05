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
* **Despliegue Continuo:** GitHub Actions

---

## Configuración para Desarrollo Local

Para correr este proyecto en tu máquina local, sigue estos pasos:

1.  **Clona el repositorio:**
    ```bash
    git clone [https://github.com/FelipeAguilar302/backend_urbanfix.git](https://github.com/FelipeAguilar302/backend_urbanfix.git)
    cd backend_urbanfix
    ```

2.  **Crea y activa un entorno virtual:**
    ```bash
    # En macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    
    # En Windows (CMD)
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Crea tu archivo `.env`:**
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

5.  **Ejecuta las migraciones de la base de datos:**
    Esto creará todas las tablas en tu base de datos de Neon.
    ```bash
    # (Asegúrate de que tu venv esté activado)
    
    # En macOS/Linux
    export FLASK_APP=app.py 
    
    # En Windows (CMD)
    set FLASK_APP=app.py
    
    # Ejecuta la migración
    flask db upgrade
    ```

6.  **¡Corre el servidor!**
    ```bash
    flask run --debug
    ```
    El servidor estará disponible en `http://127.0.0.1:5000/`.

---

## Despliegue y CI/CD

Este proyecto está configurado para **despliegue continuo** usando **GitHub Actions**.

* **Servidor:** AWS EC2 (t2.micro) corriendo Ubuntu.
* **IP del Servidor:** `http://54.144.11.53:5000` (IP Elástica permanente).
* **Proceso:** El servidor corre como un servicio `systemd` (`urbanfix.service`) usando Gunicorn.

**El flujo de despliegue es automático:**
1.  Un desarrollador hace `git push` a la rama `main`.
2.  GitHub Actions se activa automáticamente.
3.  La Acción se conecta por SSH al servidor EC2.
4.  Ejecuta `git pull` para descargar los nuevos cambios.
5.  Reinicia el servicio (`sudo systemctl restart urbanfix`) para aplicar las actualizaciones.
