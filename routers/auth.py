from fastapi import APIRouter, Request, Form, Depends, HTTPException 
from fastapi.responses import RedirectResponse 
from sqlalchemy.orm import Session 
from sqlalchemy.exc import IntegrityError 
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
    request: Request, 
    nombre: str = Form(...), 
    apellido: str = Form(...), 
    cedula: str = Form(...), 
    correo: str = Form(...), 
    password: str = Form(...), 
    rol: str = Form(...), 
    direccion: str = Form(...), 
    db: Session = Depends(get_db) 
):
    try: 
        # Conversión de cédula a entero
        cedula_entero = int(cedula.strip())

        # --- INICIO DE VERIFICACIONES MANUALES ---
        
        # 1. Buscamos en la base de datos tanto la cédula como el correo
        usuario_existente_cedula = db.query(models.Usuarios).filter(models.Usuarios.cedula == cedula_entero).first()
        usuario_existente_correo = db.query(models.Usuarios).filter(models.Usuarios.correo == correo.lower().strip()).first()

        # 2. Evaluamos qué fue lo que se encontró para armar el mensaje exacto
        if usuario_existente_cedula and usuario_existente_correo:
            mensaje_error = "La cédula y el correo electrónico ingresados ya se encuentran registrados."
        elif usuario_existente_cedula:
            mensaje_error = "Esta cédula ya se encuentra registrada en el sistema."
        elif usuario_existente_correo:
            mensaje_error = "Este correo electrónico ya está en uso."
        else:
            mensaje_error = None

        # 3. Si se generó algún mensaje de error, detenemos el proceso y mostramos la alerta
        if mensaje_error:
            return templates.TemplateResponse(
                request=request, 
                name="index.html", 
                context={"error_registro": mensaje_error}
            )
            
        # --- FIN DE VERIFICACIONES MANUALES ---

        nuevo_usuario = models.Usuarios(
            nombre=nombre.title().strip(), 
            apellido=apellido.title().strip(), 
            cedula=cedula_entero, 
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
    
    except IntegrityError:
        # Se mantiene como un escudo final de la base de datos
        db.rollback()
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error_registro": "Error en el servidor: los datos proporcionados generan conflicto con un registro existente."}
        )
        
    except ValueError:
        # Esto evita que crashee si la cédula no se puede convertir a int()
        db.rollback()
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error_registro": "La cédula debe contener únicamente números."}
        )


@router.post("/login") 
def iniciar_sesion(
    request: Request, 
    correo: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db) 
):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.correo == correo).first() 

    if not usuario_db or usuario_db.password != password: 
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error": "Correo o contraseña incorrectos"} 
        )

    elif usuario_db.rol.lower() == "chofer": 
        url_destino = f"/panel-chofer?id_chofer={usuario_db.id_usuario}" 
        return RedirectResponse(url=url_destino, status_code=303) 
       
    elif usuario_db.rol.lower() == "cliente": 
        url_destino = f"/panel-pasajero?id_pasajero={usuario_db.id_usuario}" 
        return RedirectResponse(url=url_destino, status_code=303) 

    elif usuario_db.rol.lower() in ["superadmin", "admin"]: 
        url_destino = f"/panel-administracion?rol={usuario_db.rol}&id_admin={usuario_db.id_usuario}" 
        return RedirectResponse(url=url_destino, status_code=303)