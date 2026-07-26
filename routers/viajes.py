from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import random
from datetime import datetime, time
import models
from dependencies import get_db, templates, vehiculos_activos_sesion

router = APIRouter(
    tags=["Viajes"]
)

@router.get("/pasajero/historial")
def historial_viajes(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    viajes_db = db.query(models.Viajes, models.Usuarios).join(
        models.Usuarios, models.Viajes.id_chofer == models.Usuarios.id_usuario
    ).filter(
        models.Viajes.id_pasajero == id_pasajero
    ).order_by(models.Viajes.id_viaje.desc()).all()
    
    return templates.TemplateResponse(
        request=request,
        name="historial_viajes.html",
        context={
            "id_pasajero": id_pasajero,
            "viajes": viajes_db
        }
    )

@router.get("/chofer/traslados")
def historial_traslados_chofer(
    request: Request,
    id_chofer: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Viajes, models.Usuarios, models.PagosChoferes).join(
        models.Usuarios, models.Viajes.id_pasajero == models.Usuarios.id_usuario
    ).outerjoin(
        models.PagosChoferes, models.Viajes.id_viaje == models.PagosChoferes.id_viaje
    ).filter(
        models.Viajes.id_chofer == id_chofer,
        models.Viajes.estado_viaje == models.EstadoViaje.FINALIZADO
    )
    
    if fecha_inicio and fecha_inicio.strip() != "":
        fecha_ini_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        query = query.filter(models.Viajes.fecha_viaje >= fecha_ini_date)
        
    if fecha_fin and fecha_fin.strip() != "":
        fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        query = query.filter(models.Viajes.fecha_viaje <= fecha_fin_date)
        
    viajes_db = query.order_by(models.Viajes.fecha_viaje.desc()).all()
    
    pendientes = []
    pagados = []
    total_ganado = 0.0
    total_pendiente = 0.0
    
    for viaje, pasajero, pago in viajes_db:
        ganancia = round(viaje.costo_viaje * 0.70, 2)
        item = {
            "viaje": viaje,
            "pasajero": pasajero,
            "pago": pago,
            "ganancia": ganancia
        }
        
        if pago and pago.id_administrador is not None:
            pagados.append(item)
            total_ganado += ganancia
        else:
            pendientes.append(item)
            total_pendiente += ganancia
            
    return templates.TemplateResponse(
        request=request,
        name="historial_chofer.html",
        context={
            "id_chofer": id_chofer,
            "pendientes": pendientes,
            "pagados": pagados,
            "total_ganado": round(total_ganado, 2),
            "total_pendiente": round(total_pendiente, 2),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }
    )

@router.get("/pasajero/solicitar-viaje")
def solicitar_viaje(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()
    saldo = pasajero_db.saldo_disponible if pasajero_db and pasajero_db.saldo_disponible else 0.0
    
    return templates.TemplateResponse(
        request=request,
        name="solicitar_viaje.html",
        context={
            "id_pasajero": id_pasajero,
            "saldo_actual": saldo
        }
    )

def obtener_multiplicador_horario():
    hora_actual = datetime.now().time()
    if hora_actual >= time(0, 0) and hora_actual < time(6, 0):
        return 1.5 
    elif hora_actual >= time(20, 0):
        return 1.2 
    else:
        return 1.0 

def calcular_costo_viaje(distancia_km: float, tiempo_minutos: float) -> float:
    tarifa_base = 1.00
    tarifa_minima = 2.50
    precio_por_km = 0.50
    precio_por_min = 0.15
    
    multiplicador_tiempo = obtener_multiplicador_horario()
    costo_calculado = tarifa_base + (distancia_km * precio_por_km) + (tiempo_minutos * (precio_por_min * multiplicador_tiempo))
    
    return round(max(costo_calculado, tarifa_minima), 2)

@router.get("/chofer/aceptar-viaje")
def pantalla_aceptar_viaje(request: Request, id_chofer: int, id_viaje: int, db: Session = Depends(get_db)):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    
    if not viaje_db:
        return RedirectResponse(url=f"/panel-chofer?id_chofer={id_chofer}", status_code=303)
        
    pasajero_usuario = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == viaje_db.id_pasajero).first()
    pasajero_perfil = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == viaje_db.id_pasajero).first()
    
    nombre_completo = f"{pasajero_usuario.nombre} {pasajero_usuario.apellido}" if pasajero_usuario else "Pasajero Desconocido"
    calificacion = pasajero_perfil.calificacion if pasajero_perfil else 0.0
    
    return templates.TemplateResponse(
        request=request,
        name="aceptar_viaje.html",
        context={
            "id_chofer": id_chofer,
            "viaje": viaje_db,
            "nombre_pasajero": nombre_completo,
            "calificacion_pasajero": calificacion
        }
    )

@router.post("/chofer/procesar-viaje")
def procesar_viaje(
    id_chofer: int = Form(...),
    id_viaje: int = Form(...),
    decision: str = Form(...),
    db: Session = Depends(get_db)
):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == id_chofer).first()
    
    if decision == "aceptar":
        viaje_db.estado_viaje = models.EstadoViaje.PAGO
        chofer_db.estado_chofer = models.EstadoChofer.EN_VIAJE
        db.commit()
        return RedirectResponse(url=f"/chofer/viaje-actual?id_chofer={id_chofer}&id_viaje={id_viaje}", status_code=303)
    else:
        viaje_db.estado_viaje = models.EstadoViaje.CANCELADO
        chofer_db.estado_chofer = models.EstadoChofer.DISPONIBLE
        db.commit()
        
    return RedirectResponse(url=f"/panel-chofer?id_chofer={id_chofer}", status_code=303)

@router.post("/pasajero/confirmar-viaje")
def confirmar_viaje(
    request: Request,
    id_pasajero: int = Form(...),
    distancia_km: float = Form(...),
    tiempo_minutos: float = Form(...),
    lat_origen: str = Form(...),
    lng_origen: str = Form(...),
    lat_destino: str = Form(...),
    lng_destino: str = Form(...),
    db: Session = Depends(get_db)
):
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()
    saldo_actual = pasajero_db.saldo_disponible if pasajero_db and pasajero_db.saldo_disponible else 0.0
    
    choferes_disponibles = db.query(models.Choferes).filter(
        models.Choferes.estado_chofer == models.EstadoChofer.DISPONIBLE
    ).all()
    
    if not choferes_disponibles:
        return templates.TemplateResponse(
            request=request,
            name="solicitar_viaje.html",
            context={
                "id_pasajero": id_pasajero,
                "saldo_actual": saldo_actual,
                "error": True
            }
        )
        
    chofer_asignado = random.choice(choferes_disponibles)
    matricula_vehiculo = vehiculos_activos_sesion.get(chofer_asignado.id_chofer)
    
    if not matricula_vehiculo:
        vehiculo = db.query(models.Vehiculos).filter(
            models.Vehiculos.id_chofer == chofer_asignado.id_chofer
        ).first()
        matricula_vehiculo = vehiculo.matricula if vehiculo else "SIN-PLACA"
        
    costo_total = calcular_costo_viaje(distancia_km, tiempo_minutos)
    
    if saldo_actual < costo_total:
        return templates.TemplateResponse(
            request=request,
            name="solicitar_viaje.html",
            context={
                "id_pasajero": id_pasajero,
                "saldo_actual": saldo_actual,
                "error_saldo": True
            }
        )
        
    nuevo_viaje = models.Viajes(
        id_vehiculo=matricula_vehiculo,
        id_chofer=chofer_asignado.id_chofer,
        id_pasajero=id_pasajero,
        duracion=tiempo_minutos,
        distancia=distancia_km,
        lugar_inicio=f"{lat_origen}, {lng_origen}",
        lugar_destino=f"{lat_destino}, {lng_destino}",
        fecha_viaje=datetime.now().date(),
        estado_viaje=models.EstadoViaje.EN_ESPERA,
        costo_viaje=costo_total
    )
    
    db.add(nuevo_viaje)
    db.commit()
    db.refresh(nuevo_viaje)
    
    url_destino = f"/pasajero/viaje-actual?id_pasajero={id_pasajero}&id_viaje={nuevo_viaje.id_viaje}"
    return RedirectResponse(url=url_destino, status_code=303)

@router.get("/pasajero/viaje-actual")
def pasajero_viaje_actual(request: Request, id_pasajero: int, id_viaje: int, db: Session = Depends(get_db)):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    chofer_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == viaje_db.id_chofer).first()
    vehiculo_db = db.query(models.Vehiculos).filter(models.Vehiculos.matricula == viaje_db.id_vehiculo).first()
    
    return templates.TemplateResponse(
        request=request,
        name="viaje_pasajero.html",
        context={
            "id_pasajero": id_pasajero, 
            "viaje": viaje_db, 
            "chofer": chofer_db, 
            "vehiculo": vehiculo_db
        }
    )

@router.get("/chofer/viaje-actual")
def chofer_viaje_actual(request: Request, id_chofer: int, id_viaje: int, db: Session = Depends(get_db)):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    pasajero_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == viaje_db.id_pasajero).first()
    perfil_pasajero = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == viaje_db.id_pasajero).first()
    
    ganancia_chofer = round(viaje_db.costo_viaje * 0.70, 2)
    
    return templates.TemplateResponse(
        request=request,
        name="viaje_chofer.html",
        context={
            "id_chofer": id_chofer, 
            "viaje": viaje_db, 
            "pasajero": pasajero_db, 
            "perfil_pasajero": perfil_pasajero,
            "ganancia": ganancia_chofer
        }
    )

@router.post("/chofer/finalizar-viaje")
def finalizar_viaje(
    id_chofer: int = Form(...), 
    id_viaje: int = Form(...), 
    calificacion: int = Form(3), 
    db: Session = Depends(get_db)
):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == viaje_db.id_pasajero).first()
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == id_chofer).first()
    
    if pasajero_db:
        pasajero_db.saldo_disponible -= viaje_db.costo_viaje
        
    if chofer_db:
        ganancia = round(viaje_db.costo_viaje * 0.70, 2)
        chofer_db.saldo_pendiente += ganancia
        chofer_db.estado_chofer = models.EstadoChofer.DISPONIBLE
        
    viaje_db.estado_viaje = models.EstadoViaje.FINALIZADO
    viaje_db.puntuacion_pasajero = calificacion
    viaje_db.puntuacion_chofer = 3
    
    if pasajero_db:
        viajes_pasajero = db.query(models.Viajes).filter(
            models.Viajes.id_pasajero == viaje_db.id_pasajero, 
            models.Viajes.puntuacion_pasajero != None
        ).all()
        
        if viajes_pasajero:
            promedio_pasajero = sum(v.puntuacion_pasajero for v in viajes_pasajero) / len(viajes_pasajero)
            pasajero_db.calificacion = round(promedio_pasajero, 1)
            
    if chofer_db:
        viajes_chofer = db.query(models.Viajes).filter(
            models.Viajes.id_chofer == chofer_db.id_chofer,
            models.Viajes.puntuacion_chofer != None
        ).all()
        
        if viajes_chofer:
            promedio_chofer = sum(v.puntuacion_chofer for v in viajes_chofer) / len(viajes_chofer)
            chofer_db.calificacion = round(promedio_chofer, 1)
            
    nuevo_pago = models.PagosChoferes(
        id_viaje=id_viaje,
        id_chofer=id_chofer
    )
    db.add(nuevo_pago)
    db.commit()
    
    return RedirectResponse(url=f"/panel-chofer?id_chofer={id_chofer}", status_code=303)

@router.post("/pasajero/calificar-viaje")
def calificar_viaje_pasajero(
    id_pasajero: int = Form(...),
    id_viaje: int = Form(...),
    calificacion: int = Form(3),
    db: Session = Depends(get_db)
):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    
    if viaje_db:
        viaje_db.puntuacion_chofer = calificacion
        chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == viaje_db.id_chofer).first()
        
        if chofer_db:
            viajes_chofer = db.query(models.Viajes).filter(
                models.Viajes.id_chofer == chofer_db.id_chofer,
                models.Viajes.puntuacion_chofer != None
            ).all()
            
            if viajes_chofer:
                promedio = sum(v.puntuacion_chofer for v in viajes_chofer) / len(viajes_chofer)
                chofer_db.calificacion = round(promedio, 1)
                
        db.commit()
        
    return RedirectResponse(url=f"/panel-pasajero?id_pasajero={id_pasajero}", status_code=303)

@router.get("/api/calcular-tarifa")
def api_calcular_tarifa(distancia_km: float, tiempo_minutos: float):
    costo_final = calcular_costo_viaje(distancia_km, tiempo_minutos)
    return JSONResponse({"costo_total": costo_final})

@router.get("/api/chofer/verificar-viaje/{id_chofer}")
def verificar_viaje_pendiente(id_chofer: int, db: Session = Depends(get_db)):
    viaje_db = db.query(models.Viajes).filter(
        models.Viajes.id_chofer == id_chofer,
        models.Viajes.estado_viaje == models.EstadoViaje.EN_ESPERA
    ).order_by(models.Viajes.id_viaje.desc()).first()
    
    if viaje_db:
        return JSONResponse({"viaje_pendiente": True, "id_viaje": viaje_db.id_viaje})
        
    return JSONResponse({"viaje_pendiente": False})