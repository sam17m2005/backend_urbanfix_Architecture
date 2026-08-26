# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    _docker_db = os.getenv('DATABASE_URL')
    
    if _docker_db:

        SQLALCHEMY_DATABASE_URI = _docker_db
    else:
        PGUSER = os.getenv('PGUSER')
        PGPASSWORD = os.getenv('PGPASSWORD')
        PGHOST = os.getenv('PGHOST')
        PGDATABASE = os.getenv('PGDATABASE')
        SQLALCHEMY_DATABASE_URI = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}/{PGDATABASE}?sslmode=require"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = { "pool_pre_ping": True }

    # --- AWS Config ---
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_REPORTES = os.getenv('S3_REPORTES')
    S3_PERFILES = os.getenv('S3_PERFILES')