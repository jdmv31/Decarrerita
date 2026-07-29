import os
from fastapi.templating import Jinja2Templates
from database import SessionLocal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

vehiculos_activos_sesion = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()