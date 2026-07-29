from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
import models
from dependencies import get_db, templates

router = APIRouter(
    tags=["Administración"]
)

@router.get("/panel-administracion")
def panel_administracion(request: Request, rol: str, id_admin: int = 0):
    return templates.TemplateResponse(
        request = request,
        name = "panel_administracion.html",
        context = {
            "rol": rol,
            "id_admin": id_admin 
        }
    )

@router.get("/administracion/evaluacion")
def evaluaciones_psicologicas(request: Request, db: Session = Depends(get_db)):
    evaluaciones_db = db.query(models.Usuarios, models.EvaluacionChofer).join(
        models.EvaluacionChofer, models.Usuarios.id_usuario == models.EvaluacionChofer.id_chofer
    ).filter(models.EvaluacionChofer.puntuacion == 0).all()
    
    return templates.TemplateResponse(
        request = request,
        name = "evaluaciones_psicologicas.html",
        context = {"evaluaciones": evaluaciones_db}
    )

@router.post("/administracion/evaluacion/guardar")
def guardar_calificacion(
    id_evaluacion: int = Form(...),
    puntuacion: int = Form(...),
    db: Session = Depends(get_db)
):
    evaluacion_db = db.query(models.EvaluacionChofer).filter(models.EvaluacionChofer.id_evaluacion == id_evaluacion).first()
    if evaluacion_db:
        evaluacion_db.puntuacion = puntuacion
        db.commit()
    return RedirectResponse(url="/administracion/evaluacion", status_code=303)

@router.get("/administracion/revision")
def revisiones_vehiculares(request: Request, db: Session = Depends(get_db)):
    revisiones_db = db.query(models.Vehiculos, models.RevisionVehiculo).join(
        models.RevisionVehiculo, models.Vehiculos.matricula == models.RevisionVehiculo.id_vehiculo
    ).filter(models.RevisionVehiculo.puntuacion == 0.0).all()
    
    return templates.TemplateResponse(
        request = request,
        name = "revisiones_vehiculares.html",
        context = {"revisiones": revisiones_db}
    )

@router.get("/administracion/revisiones-vencimiento")
def revisiones_por_vencer(request: Request, rol: str, id_admin: int, db: Session = Depends(get_db)):
    hoy = date.today()
    limite_fecha = hoy - timedelta(days=275)
    
    revisiones_db = db.query(models.Vehiculos, models.RevisionVehiculo, models.Usuarios).join(
        models.RevisionVehiculo, models.Vehiculos.matricula == models.RevisionVehiculo.id_vehiculo
    ).join(
        models.Usuarios, models.Vehiculos.id_chofer == models.Usuarios.id_usuario
    ).filter(
        models.RevisionVehiculo.fecha_revision <= limite_fecha,
        models.RevisionVehiculo.puntuacion >= 65
    ).all()
    
    resultados = []
    for vehiculo, revision, usuario in revisiones_db:
        dias_transcurridos = (hoy - revision.fecha_revision).days
        dias_restantes = 365 - dias_transcurridos
        
        resultados.append({
            "vehiculo": vehiculo,
            "revision": revision,
            "usuario": usuario,
            "dias_restantes": dias_restantes
        })
        
    resultados.sort(key=lambda x: x["dias_restantes"])
    
    return templates.TemplateResponse(
        request=request,
        name="revisiones_vencimiento.html",
        context={
            "rol": rol,
            "id_admin": id_admin,
            "resultados": resultados
        }
    )

@router.post("/administracion/revision/guardar")
def guardar_revision_vehiculo(
    id_revision: int = Form(...),
    puntuacion: float = Form(...),
    db: Session = Depends(get_db)
):
    revision_db = db.query(models.RevisionVehiculo).filter(models.RevisionVehiculo.id_revision == id_revision).first()
    if revision_db:
        revision_db.puntuacion = puntuacion
        revision_db.fecha_revision = datetime.now().date()
        db.commit()
    return RedirectResponse(url="/administracion/revision", status_code=303)

@router.get("/administracion/choferes")
def choferes_registrados(request: Request, rol: str, db: Session = Depends(get_db)):
    choferes_db = db.query(models.Usuarios, models.Choferes).join(
        models.Choferes, models.Usuarios.id_usuario == models.Choferes.id_chofer
    ).all()
    
    if not choferes_db:
        choferes_db = 0
        
    return templates.TemplateResponse(
        request = request,
        name = "choferes.html",
        context = {
            "choferes": choferes_db, 
            "rol": rol
        }
    )

@router.get("/administracion/pagos")
def ver_pagos_pendientes(request: Request, id_admin: int, rol: str = "superadmin", db: Session = Depends(get_db)):
    pagos_pendientes = db.query(models.PagosChoferes, models.Viajes, models.Usuarios).join(
        models.Viajes, models.PagosChoferes.id_viaje == models.Viajes.id_viaje
    ).join(
        models.Usuarios, models.Viajes.id_chofer == models.Usuarios.id_usuario
    ).filter(
        models.PagosChoferes.id_administrador.is_(None)
    ).all()
    
    pagos_con_cuentas = []
    for pago, viaje, usuario in pagos_pendientes:
        cuentas_chofer = db.query(models.DatosBancarios, models.Banco).join(
            models.Banco, models.DatosBancarios.id_banco == models.Banco.id_banco
        ).filter(models.DatosBancarios.id_chofer == viaje.id_chofer).all()
        
        pagos_con_cuentas.append({
            "pago": pago,
            "viaje": viaje,
            "usuario": usuario,
            "cuentas": cuentas_chofer
        })
        
    return templates.TemplateResponse(
        request=request,
        name="pagos_pendientes.html",
        context={
            "pagos": pagos_con_cuentas,
            "rol": rol,
            "id_admin": id_admin
        }
    )

@router.post("/administracion/pagos/procesar")
def procesar_pago_chofer(
    request: Request,
    id_pago: int = Form(...),
    id_datos: int = Form(...),
    numero_referencia: str = Form(...),
    id_admin: int = Form(...),
    db: Session = Depends(get_db)
):
    ref_limpia = numero_referencia.strip()
    error_msg = None

    if not ref_limpia.isdigit() or len(ref_limpia) != 10:
        error_msg = "El número de referencia debe contener exactamente 10 dígitos numéricos."
    else:
        referencia_existente = db.query(models.PagosChoferes).filter(models.PagosChoferes.numero_referencia == ref_limpia).first()
        if referencia_existente:
            error_msg = "Esta referencia de pago ya se encuentra registrada en el sistema."

    if error_msg:
        pagos_pendientes = db.query(models.PagosChoferes, models.Viajes, models.Usuarios).join(
            models.Viajes, models.PagosChoferes.id_viaje == models.Viajes.id_viaje
        ).join(
            models.Usuarios, models.Viajes.id_chofer == models.Usuarios.id_usuario
        ).filter(
            models.PagosChoferes.id_administrador.is_(None)
        ).all()
        
        pagos_con_cuentas = []
        for pago, viaje, usuario in pagos_pendientes:
            cuentas_chofer = db.query(models.DatosBancarios, models.Banco).join(
                models.Banco, models.DatosBancarios.id_banco == models.Banco.id_banco
            ).filter(models.DatosBancarios.id_chofer == viaje.id_chofer).all()
            
            pagos_con_cuentas.append({
                "pago": pago,
                "viaje": viaje,
                "usuario": usuario,
                "cuentas": cuentas_chofer
            })
            
        admin_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_admin).first()
        rol_admin = admin_db.rol if admin_db else "superadmin"

        return templates.TemplateResponse(
            request=request,
            name="pagos_pendientes.html",
            context={
                "pagos": pagos_con_cuentas,
                "rol": rol_admin,
                "id_admin": id_admin,
                "error": error_msg
            }
        )
    pago_db = db.query(models.PagosChoferes).filter(models.PagosChoferes.id_pago == id_pago).first()
    
    if pago_db:
        viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == pago_db.id_viaje).first()
        chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == viaje_db.id_chofer).first()
        
        ganancia = round(viaje_db.costo_viaje * 0.70, 2)
        
        pago_db.id_administrador = id_admin
        pago_db.id_datos = id_datos
        pago_db.fecha_pago = datetime.now().date()
        pago_db.numero_referencia = ref_limpia
        pago_db.monto_cancelado = ganancia
        
        if chofer_db:
            chofer_db.saldo_pendiente -= ganancia
            
        db.commit()
        
    return RedirectResponse(url=f"/administracion/pagos?rol=superadmin&id_admin={id_admin}", status_code=303)

@router.get("/administracion/pasajeros")
def pasajeros_registrados(request: Request, rol: str, db: Session = Depends(get_db)):
    pasajeros_db = db.query(models.Usuarios, models.Pasajeros).join(
        models.Usuarios, models.Usuarios.id_usuario == models.Pasajeros.id_pasajero
    ).all()
    
    if not pasajeros_db:
        pasajeros_db = 0
        
    return templates.TemplateResponse(
        request = request,
        name = "pasajeros.html",
        context = {
            "pasajeros": pasajeros_db,
            "rol": rol
        }
    )

@router.post("/administracion/administradores/agregar")
def agregar_administrador(
    nombre: str = Form(...),
    apellido: str = Form(...),
    direccion: str = Form(...),
    cedula: int = Form(...),
    rol: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...),
    rol_creador: str = Form(...),
    id_admin: int = Form(0),
    db: Session = Depends(get_db)
):
    rol = rol.lower().strip()
    
    usuario_existente = db.query(models.Usuarios).filter(
        (models.Usuarios.cedula == cedula) | (models.Usuarios.correo == correo.lower().strip())
    ).first()
    
    if not usuario_existente:
        nuevo_admin = models.Usuarios(
            nombre = nombre.title().strip(),
            apellido = apellido.title().strip(),
            cedula = cedula,
            correo = correo.lower().strip(),
            password = password.strip(),
            rol = rol,
            direccion = direccion.strip()
        )
        db.add(nuevo_admin)
        db.commit()
        
    url_destino = f"/administracion/personal?rol={rol_creador}&id_admin={id_admin}"
    return RedirectResponse(url = url_destino, status_code=303)

@router.get("/administracion/administradores")
def registrar_administrador(request: Request, rol: str, id_admin: int = 0):
    return templates.TemplateResponse(
        request = request,
        name = "administrador.html",
        context= {
            "rol": rol,
            "id_admin": id_admin
        }
    )

@router.get("/administracion/historial-pagos")
def historial_pagos_ganancias(
    request: Request,
    id_admin: int,
    rol: str,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    chofer_id: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Viajes, models.Usuarios, models.PagosChoferes).join(
        models.Usuarios, models.Viajes.id_chofer == models.Usuarios.id_usuario
    ).outerjoin(
        models.PagosChoferes, models.Viajes.id_viaje == models.PagosChoferes.id_viaje
    ).filter(
        models.Viajes.estado_viaje.in_([models.EstadoViaje.FINALIZADO, models.EstadoViaje.CANCELADO])
    )

    if fecha_inicio and fecha_inicio.strip() != "":
        fecha_ini_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        query = query.filter(models.Viajes.fecha_viaje >= fecha_ini_date)
        
    if fecha_fin and fecha_fin.strip() != "":
        fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        query = query.filter(models.Viajes.fecha_viaje <= fecha_fin_date)
        
    if chofer_id and chofer_id.strip() != "":
        query = query.filter(models.Viajes.id_chofer == int(chofer_id))
        
    todos_los_registros = query.order_by(models.Viajes.fecha_viaje.desc()).all()
    
    viajes_unificados = []
    total_viajes = 0.0
    total_pagado = 0.0
    total_ganancia_empresa = 0.0
    
    for viaje, usuario, pago in todos_los_registros:
        if viaje.estado_viaje == models.EstadoViaje.CANCELADO:
            estado = "CANCELADO"
            pago_chofer = 0.0
            ganancia_empresa = 0.0
        else:
            total_viajes += viaje.costo_viaje
            if pago and pago.id_administrador is not None:
                estado = "PAGADO"
                pago_chofer = pago.monto_cancelado
                ganancia_empresa = viaje.costo_viaje - pago.monto_cancelado
                total_pagado += pago_chofer
                total_ganancia_empresa += ganancia_empresa
            else:
                estado = "PENDIENTE"
                pago_chofer = viaje.costo_viaje * 0.70
                ganancia_empresa = viaje.costo_viaje * 0.30
                total_ganancia_empresa += ganancia_empresa
                
        viajes_unificados.append({
            "viaje": viaje,
            "usuario": usuario,
            "pago": pago,
            "pago_chofer": round(pago_chofer, 2),
            "ganancia_empresa": round(ganancia_empresa, 2),
            "estado": estado
        })
        
    choferes_lista = db.query(models.Usuarios).filter(models.Usuarios.rol == 'chofer').all()
    
    return templates.TemplateResponse(
        request=request,
        name="historial_pagos_admin.html",
        context={
            "viajes": viajes_unificados,
            "rol": rol,
            "id_admin": id_admin,
            "total_viajes": round(total_viajes, 2),
            "total_pagado": round(total_pagado, 2),
            "total_ganancia": round(total_ganancia_empresa, 2),
            "choferes": choferes_lista,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "chofer_id": int(chofer_id) if chofer_id and chofer_id.isdigit() else None
        }
    )

@router.get("/administracion/personal")
def ver_personal(request: Request, rol: str, id_admin: int, db: Session = Depends(get_db)):
    if rol != "superadmin":
        return RedirectResponse(url=f"/panel-administracion?rol={rol}&id_admin={id_admin}", status_code=303)
        
    personal_db = db.query(models.Usuarios).filter(
        models.Usuarios.rol.in_(["admin", "superadmin"])
    ).all()
    
    return templates.TemplateResponse(
        request=request,
        name="lista_personal.html",
        context={
            "personal": personal_db,
            "rol": rol,
            "id_admin": id_admin
        }
    )

@router.post("/administracion/personal/promover")
def promover_admin(
    id_usuario: int = Form(...),
    id_admin: int = Form(...),
    rol: str = Form(...),
    db: Session = Depends(get_db)
):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_usuario).first()
    
    if usuario_db and usuario_db.rol == "admin":
        usuario_db.rol = "superadmin"
        db.commit()
        
    return RedirectResponse(url=f"/administracion/personal?rol={rol}&id_admin={id_admin}", status_code=303)

@router.get("/reporte-viajes")
def reporte_viajes(request: Request, db: Session = Depends(get_db)):
    viajes_db = db.query(models.Viajes).all()
    return templates.TemplateResponse(
        request=request, 
        name="reporte.html", 
        context={"viajes": viajes_db}
    )