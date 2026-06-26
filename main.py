from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, SessionLocal

app = FastAPI(title="API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def test_conexion(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "exito", 
            "mensaje": "se conecto a la base de datos"
        }
    except Exception as e:
        return {
            "status": "error", 
            "mensaje": f"fallo al conectar con la base de datos: {str(e)}"
        }