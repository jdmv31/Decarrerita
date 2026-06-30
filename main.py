import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models
import datetime

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
    if rol.lower() == "cliente":
        nuevo_pasajero = models.Pasajeros(
            id = nuevo_usuario.id
        )
        db.add(nuevo_pasajero)
        db.commit()
    elif rol.lower() == "chofer":
        nuevo_chofer = models.Choferes(
            id = nuevo_usuario.id
        )
        db.add(nuevo_chofer)
        db.commit()
        db.refresh(nuevo_chofer)
        
        nueva_evaluacion = models.EvaluacionChofer(
            id_chofer = nuevo_chofer.id,
            puntuacion = 0,

        )
        db.add(nueva_evaluacion)
        db.commit()

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
    elif usuario_db.rol.lower() == "chofer":
        return RedirectResponse(url="/panel-chofer", status_code=303)
    elif usuario_db.rol.lower() == "pasajero":
        return RedirectResponse(url="/panel-cliente",status_code = 303)
    
@app.get ("/panel-chofer")
def panel_chofer(request: Request, puntuacion: int = Query(0), id_chofer: int = Query(1)):
    return templates.TemplateResponse(
        request= request,
        name = "panel_chofer.html",
        context={"puntuacion": puntuacion, "id_chofer": id_chofer} 
    )

@app.get ("/chofer/vehiculo")
def panel_vehiculo(request: Request, id_chofer: int = Query(1)):
    return templates.TemplateResponse(
        request = request,
        name = "registro_vehiculo.html",
        context={"id_chofer": id_chofer} 
    )

@app.get("/chofer/perfil")
def ver_datos_personales(request: Request, id_chofer: int = Query(1), db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id == id_chofer).first()
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id == id_chofer).first()
    evaluacion_db = db.query(models.EvaluacionChofer).filter(models.EvaluacionChofer.id_chofer == id_chofer).first()

    return templates.TemplateResponse(
        request=request,
        name="informacion_chofer.html",
        context={
            "id_chofer": id_chofer,
            "usuario": usuario_db,
            "chofer": chofer_db,
            "evaluacion": evaluacion_db
        }
    )

@app.get ("/chofer/datos-bancarios")
def panel_banco(request:Request, id_chofer: int = Query(1)):
    return templates.TemplateResponse(
        request = request,
        name = "datos_bancarios.html",
        context = {"id_chofer":id_chofer}
    )

@app.post("/chofer/datos-bancarios")
def registrar_datos(
    id_chofer: int = Form(...),
    banco: str = Form(...),
    numero_cuenta: str = Form(...),
    db: Session = Depends(get_db)
):
    banco_db = db.query(models.Banco).filter(models.Banco.nombre == banco).first()
    if not banco_db:
        banco_db = models.Banco(nombre = banco)
        db.add(banco_db)
        db.commit()
        db.refresh(banco_db)

    nueva_cuenta = models.DatosBancarios(
        id_chofer = id_chofer,
        id_banco = banco_db.id,
        numero_cuenta = numero_cuenta
    )
    db.add(nueva_cuenta)
    db.commit()

    return RedirectResponse(url = "/panel-chofer",status_code=303)

@app.post ("/chofer/vehiculo")
def registrar_vehiculo(
    placa: str = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    anio: int = Form(...),
    color: str = Form(...),
    id_chofer: int = Form(...),
    db: Session = Depends(get_db)
):
    nuevo_vehiculo = models.Vehiculos(
        matricula = placa,
        id_chofer = id_chofer,
        marca = marca,
        modelo = modelo,
        annio = anio,
        color = color
    )
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    return RedirectResponse(url="/panel-chofer", status_code=303)

@app.post("/chofer/estado")
def actualizar_estado(
    id_chofer: int = Form(...),
    estado_nuevo: str = Form(...),
    db: Session = Depends(get_db)
):
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id == id_chofer).first()
    if chofer_db:
        chofer_db.estado_chofer = estado_nuevo
        db.commit()
    return RedirectResponse(url="/panel-chofer", status_code=303)
    
@app.get("/reporte-viajes")
def reporte_viajes(request: Request, db: Session = Depends(get_db)):
    viajes_db = db.query(models.Viajes).all()
    return templates.TemplateResponse(
        request=request, 
        name="reporte.html", 
        context={"viajes": viajes_db}
    )