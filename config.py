# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PGUSER = os.getenv('PGUSER')
    PGPASSWORD = os.getenv('PGPASSWORD')
    PGHOST = os.getenv('PGHOST')
    PGDATABASE = os.getenv('PGDATABASE')
    
    SQLALCHEMY_DATABASE_URI = f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}/{PGDATABASE}?sslmode=require"
    SQLALCHEMY_TRACK_MODIFICATIONS = False