from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import models
from dependencies import get_db, templates, vehiculos_activos_sesion

router = APIRouter(
    tags=["Choferes"]
)

@router.get("/panel-chofer")
def panel_chofer(request: Request, id_chofer: int, db: Session = Depends(get_db)):
    evaluacion_db = db.query(models.EvaluacionChofer).filter(models.EvaluacionChofer.id_chofer == id_chofer).first()
    puntuacion = evaluacion_db.puntuacion if evaluacion_db is not None else 0
    
    cantidad_contactos = db.query(models.AgendaContactos).filter(models.AgendaContactos.id_chofer == id_chofer).count()
    tiene_banco = db.query(models.DatosBancarios).filter(models.DatosBancarios.id_chofer == id_chofer).first() is not None
    
    hoy = date.today()
    limite_vencimiento = hoy - timedelta(days=365)
    
    vehiculos_aprobados = db.query(models.Vehiculos).join(
        models.RevisionVehiculo, models.Vehiculos.matricula == models.RevisionVehiculo.id_vehiculo
    ).filter(
        models.Vehiculos.id_chofer == id_chofer,
        models.RevisionVehiculo.puntuacion >= 65,
        models.RevisionVehiculo.fecha_revision >= limite_vencimiento
    ).all()
    
    return templates.TemplateResponse(
        request= request,
        name = "panel_chofer.html",
        context={
            "puntuacion": puntuacion, 
            "id_chofer": id_chofer,
            "vehiculos": vehiculos_aprobados,
            "cantidad_contactos": cantidad_contactos,
            "tiene_banco": tiene_banco
        }
    )

@router.get("/chofer/vehiculo")
def panel_vehiculo(request: Request, id_chofer: int):
    return templates.TemplateResponse(
        request = request,
        name = "registro_vehiculo.html",
        context={"id_chofer": id_chofer} 
    )

@router.get("/chofer/perfil")
def ver_datos_personales(request: Request, id_chofer: int, db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_chofer).first()
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == id_chofer).first()
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

@router.get("/chofer/datos-bancarios")
def panel_banco(request: Request, id_chofer: int):
    return templates.TemplateResponse(
        request = request,
        name = "datos_bancarios.html",
        context = {"id_chofer": id_chofer}
    )

@router.get("/chofer/contactos-emergencia")
def panel_contactos(request: Request, id_chofer: int, db: Session = Depends(get_db)):
    contactos = db.query(models.AgendaContactos).filter(models.AgendaContactos.id_chofer == id_chofer).count()
    return templates.TemplateResponse(
        request = request,
        name = "contactos.html",
        context = {
            "id_chofer": id_chofer, 
            "contactos": contactos
        }
    )

@router.post("/chofer/registrar-contacto")
def registrar_contacto(
    id_chofer: int = Form(...),
    nombre: str = Form(...),
    numero: str = Form(...),
    numeral: str = Form(...),
    db: Session = Depends(get_db)
):
    numero_telefonico = numeral + "-" + numero
    numero_telefonico = numero_telefonico.strip()
    
    numero_db = db.query(models.ContactosEmergencia).filter(models.ContactosEmergencia.numero_telefonico == numero_telefonico).first()
    
    if not numero_db:
        numero_db = models.ContactosEmergencia(numero_telefonico = numero_telefonico)
        db.add(numero_db)
        db.commit()
        db.refresh(numero_db)
        
    contacto_registrado = models.AgendaContactos(
        id_chofer = id_chofer,
        id_contacto = numero_db.id_contacto,
        nombre_contacto = nombre.title().strip()
    )
    db.add(contacto_registrado)
    db.commit()
    
    url_destino = f"/panel-chofer?id_chofer={id_chofer}"
    return RedirectResponse(url=url_destino, status_code=303)
     
@router.post("/chofer/registrar-datos")
def registrar_datos(
    request: Request,
    id_chofer: int = Form(...),
    banco: str = Form(...),
    numero_cuenta: str = Form(...),
    db: Session = Depends(get_db)
):
    numero_cuenta_limpio = numero_cuenta.strip()

    if not numero_cuenta_limpio.isdigit() or len(numero_cuenta_limpio) != 20:
        return templates.TemplateResponse(
            request=request,
            name="datos_bancarios.html",
            context={
                "id_chofer": id_chofer,
                "error": "El número de cuenta debe contener exactamente 20 dígitos numéricos."
            }
        )

    cuenta_existente = db.query(models.DatosBancarios).filter(models.DatosBancarios.numero_cuenta == numero_cuenta_limpio).first()
    
    if cuenta_existente:
        return templates.TemplateResponse(
            request=request,
            name="datos_bancarios.html",
            context={
                "id_chofer": id_chofer,
                "error": "Este número de cuenta ya se encuentra registrado en el sistema."
            }
        )
    banco_db = db.query(models.Banco).filter(models.Banco.nombre == banco).first()
    
    if not banco_db:
        banco_db = models.Banco(nombre = banco)
        db.add(banco_db)
        db.commit()
        db.refresh(banco_db)
        
    nueva_cuenta = models.DatosBancarios(
        id_chofer = id_chofer,
        id_banco = banco_db.id_banco,
        numero_cuenta = numero_cuenta_limpio
    )
    db.add(nueva_cuenta)
    db.commit()
    
    url_destino = f"/panel-chofer?id_chofer={id_chofer}"
    return RedirectResponse(url=url_destino, status_code=303)

@router.post("/chofer/vehiculo")
def registrar_vehiculo(
    request: Request,
    placa: str = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    anio: int = Form(...),
    color: str = Form(...),
    id_chofer: int = Form(...),
    db: Session = Depends(get_db)
):
    matricula_formateada = placa.upper().strip()
    
    if not matricula_formateada.isalnum() or len(matricula_formateada) < 6 or len(matricula_formateada) > 7:
        return templates.TemplateResponse(
            request=request,
            name="registro_vehiculo.html",
            context={
                "id_chofer": id_chofer,
                "error": "La placa debe tener entre 6 y 7 caracteres alfanuméricos sin espacios ni guiones."
            }
        )
    vehiculo_existente = db.query(models.Vehiculos).filter(models.Vehiculos.matricula == matricula_formateada).first()
    
    if vehiculo_existente:
        return templates.TemplateResponse(
            request=request,
            name="registro_vehiculo.html",
            context={
                "id_chofer": id_chofer,
                "error": f"La placa {matricula_formateada} ya se encuentra registrada en el sistema por otro chofer."
            }
        )
    
    nuevo_vehiculo = models.Vehiculos(
        matricula = matricula_formateada,
        id_chofer = id_chofer,
        marca = marca.upper().strip(),
        modelo = modelo.title().strip(),
        annio = anio,
        color = color.strip().title()
    )
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    
    nueva_revision = db.query(models.RevisionVehiculo).filter(models.RevisionVehiculo.id_vehiculo == matricula_formateada).first()
    if not nueva_revision:
        nueva_revision = models.RevisionVehiculo(
            id_vehiculo = matricula_formateada,
            puntuacion = 0.0,
            fecha_revision = datetime.now().date()
        )
        db.add(nueva_revision)
        db.commit()

    url_destino = f"/panel-chofer?id_chofer={id_chofer}"
    return RedirectResponse(url=url_destino, status_code=303)

@router.post("/chofer/estado")
def actualizar_estado(
    id_chofer: int = Form(...),
    estado_nuevo: str = Form(...),
    matricula_activa: str = Form(None),
    db: Session = Depends(get_db)
):
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == id_chofer).first()
    
    if estado_nuevo == "DISPONIBLE":
        tiene_banco = db.query(models.DatosBancarios).filter(models.DatosBancarios.id_chofer == id_chofer).first()
        if not tiene_banco:
            return RedirectResponse(url=f"/panel-chofer?id_chofer={id_chofer}", status_code=303)
            
    if chofer_db:
        chofer_db.estado_chofer = models.EstadoChofer[estado_nuevo]
        db.commit()
        
        if estado_nuevo == "DISPONIBLE" and matricula_activa:
            vehiculos_activos_sesion[id_chofer] = matricula_activa
            
    url_destino = f"/panel-chofer?id_chofer={id_chofer}"
    return RedirectResponse(url=url_destino, status_code=303)