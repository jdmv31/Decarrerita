from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import models
from dependencies import get_db, templates

router = APIRouter(
    tags=["Autenticación"]
)

@router.get("/")
def inicio(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@router.post("/registro")
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
        nombre=nombre.title().strip(),
        apellido=apellido.title().strip(),
        cedula=cedula.strip(),
        correo=correo.lower().strip(),
        password=password.strip(),
        rol=rol,
        direccion=direccion
    )
    
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    if rol.lower() == "cliente":
        nuevo_pasajero = models.Pasajeros(
            id_pasajero = nuevo_usuario.id_usuario
        )
        db.add(nuevo_pasajero)
        db.commit()

    elif rol.lower() == "chofer":
        nuevo_chofer = models.Choferes(
            id_chofer = nuevo_usuario.id_usuario
        )
        db.add(nuevo_chofer)
        db.commit()
        db.refresh(nuevo_chofer)
        
        nueva_evaluacion = models.EvaluacionChofer(
            id_chofer = nuevo_chofer.id_chofer,
            puntuacion = 0,
        )
        db.add(nueva_evaluacion)
        db.commit()

    return RedirectResponse(url="/", status_code=303)

@router.post("/login")
def iniciar_sesion(
    correo: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.correo == correo).first()

    if not usuario_db or usuario_db.password != password:
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")

    elif usuario_db.rol.lower() == "chofer":
        url_destino = f"/panel-chofer?id_chofer={usuario_db.id_usuario}"
        return RedirectResponse(url=url_destino, status_code=303)
       
    elif usuario_db.rol.lower() == "cliente":
        url_destino = f"/panel-pasajero?id_pasajero={usuario_db.id_usuario}"
        return RedirectResponse(url=url_destino, status_code=303)

    elif usuario_db.rol.lower() in ["superadmin", "admin"]:
        url_destino = f"/panel-administracion?rol={usuario_db.rol}&id_admin={usuario_db.id_usuario}"
        return RedirectResponse(url=url_destino, status_code=303)