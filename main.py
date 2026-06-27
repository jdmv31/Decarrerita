import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models

app = FastAPI(title="API")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def inicio(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/registro")
def registrar_usuario(
    nombre: str = Form(...),
    apellido: str = Form(...),
    cedula: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...),
    rol: str = Form(...),
    direccion: str = Form(...),
    db: Session = Depends(get_db)
):
    nuevo_usuario = models.Usuarios(
        nombre=nombre,
        apellido=apellido,
        cedula=cedula,
        correo=correo,
        password=password,
        rol=rol,
        direccion=direccion
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/login")
def iniciar_sesion(
    correo: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.correo == correo).first()

    if not usuario_db or usuario_db.password != password:
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")
    return RedirectResponse(url="/reporte-viajes", status_code=303)

@app.get("/reporte-viajes")
def reporte_viajes(request: Request, db: Session = Depends(get_db)):
    viajes_db = db.query(models.Viajes).all()
    return templates.TemplateResponse(
        request=request, 
        name="reporte.html", 
        context={"viajes": viajes_db}
    )