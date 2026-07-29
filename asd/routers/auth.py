from fastapi import APIRouter, Request, Form, Depends
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
        # 1. Escudo contra números gigantes que rompen PostgreSQL
        cedula_entero = int(cedula.strip())
        if cedula_entero > 2147483647:
            return templates.TemplateResponse(
                request=request, 
                name="index.html", 
                context={"error_registro": "El número de cédula ingresado es demasiado largo."}
            )

        # 2. Verificamos SIEMPRE el correo, ya que es único para iniciar sesión
        usuario_existente_correo = db.query(models.Usuarios).filter(models.Usuarios.correo == correo.lower().strip()).first()
        if usuario_existente_correo:
            return templates.TemplateResponse(
                request=request, 
                name="index.html", 
                context={"error_registro": "Este correo electrónico ya está en uso. Por favor, utiliza uno diferente."}
            )

        # 3. Buscamos TODOS los registros vinculados a esta cédula
        usuarios_misma_cedula = db.query(models.Usuarios).filter(models.Usuarios.cedula == cedula_entero).all()
        
        # Extraemos los roles que ya posee la cédula (ej. ["cliente"] o ["chofer", "cliente"])
        roles_registrados = [u.rol.lower() for u in usuarios_misma_cedula]
        rol_solicitado = rol.lower().strip()

        # 4. Validaciones de roles existentes
        # Caso A: Ya es tanto chofer como pasajero
        if "cliente" in roles_registrados and "chofer" in roles_registrados:
            return templates.TemplateResponse(
                request=request, 
                name="index.html", 
                context={"error_registro": "Esta cédula ya posee cuentas registradas tanto de pasajero como de chofer."}
            )

        # Caso B: Intenta registrarse en un rol que ya tiene
        if rol_solicitado in roles_registrados:
            if rol_solicitado == "cliente":
                mensaje_error = "Esta cédula ya se encuentra registrada como pasajero."
            elif rol_solicitado == "chofer":
                mensaje_error = "Esta cédula ya se encuentra registrada como chofer."
            elif rol_solicitado not in ["chofer", "cliente"]:
                mensaje_error = "Esta cédula ya está registrada con ambos roles."
                
            return templates.TemplateResponse(
                request=request, 
                name="index.html", 
                context={"error_registro": mensaje_error}
            )

        # 5. Si pasa las validaciones, procedemos a "jalar" los datos si existe una cuenta previa
        if usuarios_misma_cedula:
            # Tomamos los datos personales del primer registro que encontremos con esa cédula
            usuario_base = usuarios_misma_cedula[0]
            nombre_final = usuario_base.nombre
            apellido_final = usuario_base.apellido
            direccion_final = usuario_base.direccion
        else:
            # Si es totalmente nuevo, usamos lo que viene del formulario
            nombre_final = nombre.title().strip()
            apellido_final = apellido.title().strip()
            direccion_final = direccion.strip()

        # 6. Creamos el usuario con los datos definidos
        nuevo_usuario = models.Usuarios(
            nombre=nombre_final,
            apellido=apellido_final,
            cedula=cedula_entero,
            correo=correo.lower().strip(),
            password=password.strip(),
            rol=rol,
            direccion=direccion_final
        )
        
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        # 7. Asignamos a las tablas de rol correspondientes
        if rol.lower() == "cliente":
            nuevo_pasajero = models.Pasajeros(
                id_pasajero=nuevo_usuario.id_usuario
            )
            db.add(nuevo_pasajero)
            db.commit()

        elif rol.lower() == "chofer":
            nuevo_chofer = models.Choferes(
                id_chofer=nuevo_usuario.id_usuario
            )
            db.add(nuevo_chofer)
            db.commit()
            db.refresh(nuevo_chofer)
            
            nueva_evaluacion = models.EvaluacionChofer(
                id_chofer=nuevo_chofer.id_chofer,
                puntuacion=0,
            )
            db.add(nueva_evaluacion)
            db.commit()

        return RedirectResponse(url="/", status_code=303)
    
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error_registro": "Error en la base de datos: conflicto con un registro existente."}
        )
        
    except ValueError:
        db.rollback()
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error_registro": "La cédula debe contener únicamente números."}
        )
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error_registro": "Ocurrió un error inesperado al registrar el usuario. Intenta de nuevo."}
        )

@router.post("/login")
def iniciar_sesion(
    request: Request,
    correo: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
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
            
    except Exception as e:
        # Evita que el servidor explote en caso de desconexión con la BD al iniciar sesión
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"error": "Error interno del servidor al procesar el inicio de sesión."}
        )