import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models
import random
from datetime import datetime,time,date,timedelta
from typing import Optional
from fastapi.responses import JSONResponse

app = FastAPI(title="API")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

vehiculos_activos_sesion = {}

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
        url_destino = f"/panel-chofer?id_chofer={usuario_db.id_usuario}"
        return RedirectResponse(url=url_destino, status_code=303)   
    elif usuario_db.rol.lower() == "cliente":
        url_destino = f"/panel-pasajero?id_pasajero={usuario_db.id_usuario}"
        return RedirectResponse(url=url_destino, status_code=303)
    elif usuario_db.rol.lower() in ["superadmin", "admin"]: 
        url_destino = f"/panel-administracion?rol={usuario_db.rol}&id_admin={usuario_db.id_usuario}"
        return RedirectResponse(url=url_destino, status_code=303)

@app.post("/pasajero/saldo/procesar-recarga")
def recarga(
    id_pasajero: int = Form(...),
    banco: str = Form(...),
    monto: float = Form(...),
    numero_referencia: str = Form(...),
    db: Session = Depends(get_db)
):
    banco_db = db.query(models.Banco).filter(models.Banco.nombre == banco).first()
    
    if not banco_db:
        nuevo_banco = models.Banco(nombre = banco)
        db.add(nuevo_banco)
        db.commit()
        db.refresh(nuevo_banco)
        id_banco = nuevo_banco.id_banco
    else:
        id_banco = banco_db.id_banco

    nueva_recarga = models.HistorialRecargas(
        id_pasajero = id_pasajero,
        id_banco = id_banco,
        monto_recargado = monto,
        numero_referencia = numero_referencia.strip()
    )

    db.add(nueva_recarga)
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()
    if pasajero_db:
        saldo_actual = pasajero_db.saldo_disponible if pasajero_db.saldo_disponible is not None else 0.0
        pasajero_db.saldo_disponible = saldo_actual + monto
    db.commit()

    url_destino = f"/pasajero/saldo?id_pasajero={id_pasajero}"
    return RedirectResponse(url=url_destino, status_code=303)

@app.get ("/pasajero/saldo/recargar")
def recargar_saldo(request: Request, id_pasajero: int):
    return templates.TemplateResponse(
        request = request,
        name = "recarga_saldo.html",
        context = {"id_pasajero":id_pasajero}
    )

@app.get("/pasajero/historial")
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

@app.get("/chofer/traslados")
def historial_traslados_chofer(
    request: Request, 
    id_chofer: int, 
    fecha_inicio: str = None, 
    fecha_fin: str = None, 
    db: Session = Depends(get_db)
):
    # Cruzamos Viajes con Usuarios (pasajero) y PagosChoferes
    # Solo traemos los viajes FINALIZADOS, ya que los cancelados no generan pago
    query = db.query(models.Viajes, models.Usuarios, models.PagosChoferes).join(
        models.Usuarios, models.Viajes.id_pasajero == models.Usuarios.id_usuario
    ).outerjoin(
        models.PagosChoferes, models.Viajes.id_viaje == models.PagosChoferes.id_viaje
    ).filter(
        models.Viajes.id_chofer == id_chofer,
        models.Viajes.estado_viaje == models.EstadoViaje.FINALIZADO
    )

    # Aplicamos los filtros de fecha (sobre la fecha del viaje)
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

    # Particionamos la información
    for viaje, pasajero, pago in viajes_db:
        ganancia = round(viaje.costo_viaje * 0.70, 2)
        item = {
            "viaje": viaje,
            "pasajero": pasajero,
            "pago": pago,
            "ganancia": ganancia
        }
        
        # Si el pago tiene un administrador asignado, significa que ya fue liquidado
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

@app.get("/pasajero/solicitar-viaje")
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
    """
    Devuelve un multiplicador basado en la hora actual del servidor.
    """
    hora_actual = datetime.now().time()
    
    if hora_actual >= time(0, 0) and hora_actual < time(6, 0):
        return 1.5 
    elif hora_actual >= time(20, 0):
        return 1.2 
    else:
        return 1.0
    
def calcular_costo_viaje(distancia_km: float, tiempo_minutos: float) -> float:
    """Función central para calcular el costo de cualquier viaje."""
    tarifa_base = 1.00
    tarifa_minima = 2.50
    precio_por_km = 0.50
    precio_por_min = 0.15

    multiplicador_tiempo = obtener_multiplicador_horario()
    costo_calculado = tarifa_base + (distancia_km * precio_por_km) + (tiempo_minutos * (precio_por_min * multiplicador_tiempo))
    
    return round(max(costo_calculado, tarifa_minima), 2)

@app.get("/chofer/aceptar-viaje")
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

@app.post("/chofer/procesar-viaje")
def procesar_viaje(
    id_chofer: int = Form(...),
    id_viaje: int = Form(...),
    decision: str = Form(...),
    db: Session = Depends(get_db)
):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == id_chofer).first()

    if decision == "aceptar":
        viaje_db.estado_viaje = models.EstadoViaje.PAGO # O un nuevo estado "EN_CURSO"
        chofer_db.estado_chofer = models.EstadoChofer.EN_VIAJE
    
        db.commit()
        return RedirectResponse(url=f"/chofer/viaje-actual?id_chofer={id_chofer}&id_viaje={id_viaje}", status_code=303)
    else:
        viaje_db.estado_viaje = models.EstadoViaje.CANCELADO
        chofer_db.estado_chofer = models.EstadoChofer.DISPONIBLE 

    db.commit()
    return RedirectResponse(url=f"/panel-chofer?id_chofer={id_chofer}", status_code=303)

@app.post("/pasajero/confirmar-viaje")
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

@app.get("/pasajero/viaje-actual")
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

@app.get("/chofer/viaje-actual")
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

@app.post("/chofer/finalizar-viaje")
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

    # 1. El chofer califica al pasajero y dejamos un 3 por defecto para el chofer
    viaje_db.estado_viaje = models.EstadoViaje.FINALIZADO
    viaje_db.puntuacion_pasajero = calificacion
    viaje_db.puntuacion_chofer = 3

    # 2. RECALCULAR Y ACTUALIZAR EL PROMEDIO DEL PASAJERO EN SU PERFIL
    if pasajero_db:
        viajes_pasajero = db.query(models.Viajes).filter(
            models.Viajes.id_pasajero == viaje_db.id_pasajero, 
            models.Viajes.puntuacion_pasajero != None
        ).all()
        
        if viajes_pasajero:
            promedio_pasajero = sum(v.puntuacion_pasajero for v in viajes_pasajero) / len(viajes_pasajero)
            pasajero_db.calificacion = round(promedio_pasajero, 1)

    # 3. Recalcular promedio del chofer (con el 3 por defecto)
    if chofer_db:
        viajes_chofer = db.query(models.Viajes).filter(
            models.Viajes.id_chofer == chofer_db.id_chofer,
            models.Viajes.puntuacion_chofer != None
        ).all()
        
        if viajes_chofer:
            promedio_chofer = sum(v.puntuacion_chofer for v in viajes_chofer) / len(viajes_chofer)
            chofer_db.calificacion = round(promedio_chofer, 1)

    # 4. Crear instancia de pago en stand by
    nuevo_pago = models.PagosChoferes(
        id_viaje=id_viaje,
        id_chofer=id_chofer
    )
    db.add(nuevo_pago)
    
    db.commit()
    return RedirectResponse(url=f"/panel-chofer?id_chofer={id_chofer}", status_code=303)


@app.post("/pasajero/calificar-viaje")
def calificar_viaje_pasajero(
    id_pasajero: int = Form(...),
    id_viaje: int = Form(...),
    calificacion: int = Form(3), # Asume 3 si el pasajero logra enviar el formulario vacío
    db: Session = Depends(get_db)
):
    viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == id_viaje).first()
    
    if viaje_db:
        # El pasajero califica al chofer (sobreescribe el 3 automático que le dimos antes)
        viaje_db.puntuacion_chofer = calificacion 
        
        chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == viaje_db.id_chofer).first()
        
        # Volvemos a recalcular el promedio histórico del chofer con la nota real
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



@app.get("/pasajero/saldo/historial")
def ver_historial(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    recargas_db = db.query(models.HistorialRecargas, models.Banco).join(models.Banco, models.HistorialRecargas.id_banco == models.Banco.id_banco).filter(
        models.HistorialRecargas.id_pasajero == id_pasajero).order_by(models.HistorialRecargas.fecha.desc()).all()
    return templates.TemplateResponse(
        request = request,
        name = "historial_recargas.html",
        context = {
            "id_pasajero": id_pasajero,
            "recargas": recargas_db
        }
    )

@app.get("/panel-pasajero")
def panel_pasajeros(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_pasajero).first()
    nombre_usuario = usuario_db.nombre if usuario_db else "Pasajero"
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()
    saldo = pasajero_db.saldo_disponible if pasajero_db and pasajero_db.saldo_disponible else 0.0
    calificacion = pasajero_db.calificacion if pasajero_db and pasajero_db.calificacion else 0.0

    return templates.TemplateResponse(
        request = request,
        name = "panel_pasajero.html",
        context = {
            "id_pasajero": id_pasajero,
            "saldo": saldo,
            "calificacion": calificacion,
            "nombre": nombre_usuario 
        }
    )

@app.get("/pasajero/saldo")
def panel_saldo(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()
    saldo = pasajero_db.saldo_disponible if pasajero_db and pasajero_db.saldo_disponible else 0.0

    return templates.TemplateResponse(
        request = request,
        name = "panel_saldo.html",
        context = {
            "id_pasajero": id_pasajero,
            "saldo": saldo
        }
    )

@app.get("/pasajero/perfil")
def perfil_pasajero(request:Request, id_pasajero: int, db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_pasajero).first()
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()

    return templates.TemplateResponse(
        request = request,
        name = "informacion_pasajero.html",
        context = {
            "pasajero":pasajero_db,
            "usuario":usuario_db,
            "id_pasajero":id_pasajero
        }
    )

@app.get("/panel-administracion")
def panel_administracion(request: Request, rol: str, id_admin: int = 0):
    return templates.TemplateResponse(
        request = request,
        name = "panel_administracion.html",
        context = {
            "rol": rol,
            "id_admin": id_admin 
        }
    )

@app.get("/administracion/evaluacion")
def evaluaciones_psicologicas(request: Request, db: Session = Depends(get_db)):
    evaluaciones_db = db.query(models.Usuarios, models.EvaluacionChofer).join(
        models.EvaluacionChofer, models.Usuarios.id_usuario == models.EvaluacionChofer.id_chofer
    ).filter(models.EvaluacionChofer.puntuacion == 0).all()

    return templates.TemplateResponse(
        request = request,
        name = "evaluaciones_psicologicas.html",
        context = {"evaluaciones":evaluaciones_db}
    )

@app.post ("/administracion/evaluacion/guardar")
def guardar_calificacion(
    id_evaluacion: int = Form(...),
    puntuacion: int = Form(...),
    db: Session = Depends(get_db)                   
):
    evaluacion_db = db.query(models.EvaluacionChofer).filter(models.EvaluacionChofer.id_evaluacion == id_evaluacion).first()
    if evaluacion_db:
        evaluacion_db.puntuacion = puntuacion
        db.commit()

    return RedirectResponse(url="/administracion/evaluacion",status_code=303)

@app.get("/administracion/revision")
def revisiones_vehiculares(request: Request, db: Session = Depends(get_db)):
    revisiones_db = db.query(models.Vehiculos, models.RevisionVehiculo).join(
        models.RevisionVehiculo, models.Vehiculos.matricula == models.RevisionVehiculo.id_vehiculo
    ).filter(models.RevisionVehiculo.puntuacion == 0.0).all()

    return templates.TemplateResponse(
        request = request,
        name = "revisiones_vehiculares.html",
        context = {"revisiones": revisiones_db}
    )

@app.get("/administracion/revisiones-vencimiento")
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

@app.post("/administracion/revision/guardar")
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

@app.get("/panel-chofer")
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

@app.get ("/chofer/vehiculo")
def panel_vehiculo(request: Request, id_chofer: int):
    return templates.TemplateResponse(
        request = request,
        name = "registro_vehiculo.html",
        context={"id_chofer": id_chofer} 
    )

@app.get("/chofer/perfil")
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

@app.get ("/chofer/datos-bancarios")
def panel_banco(request:Request, id_chofer: int):
    return templates.TemplateResponse(
        request = request,
        name = "datos_bancarios.html",
        context = {"id_chofer":id_chofer}
    )


@app.get ("/chofer/contactos-emergencia")
def panel_contactos(request: Request, id_chofer: int, db: Session = Depends(get_db)):
    contactos = db.query(models.AgendaContactos).filter(models.AgendaContactos.id_chofer == id_chofer).count()
    return templates.TemplateResponse(
        request = request,
        name = "contactos.html",
        context = {
            "id_chofer":id_chofer, 
            "contactos": contactos
        }
    )

@app.get("/administracion/choferes")
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

@app.get("/administracion/pagos")
def ver_pagos_pendientes(request: Request, id_admin: int, rol: str = "superadmin", db: Session = Depends(get_db)):
    pagos_pendientes = db.query(models.PagosChoferes, models.Viajes, models.Usuarios).join(
        models.Viajes, models.PagosChoferes.id_viaje == models.Viajes.id_viaje
    ).join(
        models.Usuarios, models.PagosChoferes.id_chofer == models.Usuarios.id_usuario
    ).filter(
        models.PagosChoferes.id_administrador == None
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="pagos_pendientes.html",
        context={
            "pagos": pagos_pendientes,
            "rol": rol,
            "id_admin": id_admin # Pasamos el ID a la vista final
        }
    )

@app.post("/administracion/pagos/procesar")
def procesar_pago_chofer(
    id_pago: int = Form(...),
    numero_referencia: int = Form(...),
    id_admin: int = Form(...), # Recibimos el ID real desde el formulario
    db: Session = Depends(get_db)
):
    pago_db = db.query(models.PagosChoferes).filter(models.PagosChoferes.id_pago == id_pago).first()
    
    if pago_db:
        viaje_db = db.query(models.Viajes).filter(models.Viajes.id_viaje == pago_db.id_viaje).first()
        chofer_db = db.query(models.Choferes).filter(models.Choferes.id_chofer == pago_db.id_chofer).first()
        
        ganancia = round(viaje_db.costo_viaje * 0.70, 2)
        
        # ASIGNACIÓN DINÁMICA DEL ADMIN
        pago_db.id_administrador = id_admin 
        pago_db.fecha_pago = datetime.now().date()
        pago_db.numero_referencia = numero_referencia
        pago_db.monto_cancelado = ganancia
        
        if chofer_db:
            chofer_db.saldo_pendiente -= ganancia
            
        db.commit()
        
    # Volvemos a la vista pasándole el ID para no perder la sesión
    return RedirectResponse(url=f"/administracion/pagos?rol=superadmin&id_admin={id_admin}", status_code=303)

@app.get("/administracion/pasajeros")
def pasajeros_registrados(request: Request,rol:str, db: Session = Depends(get_db)):
    pasajeros_db = db.query(models.Usuarios,models.Pasajeros).join(models.Usuarios,models.Usuarios.id_usuario == models.Pasajeros.id_pasajero).all()

    if not pasajeros_db:
        pasajeros_db = 0
    return templates.TemplateResponse(
        request = request,
        name = "pasajeros.html",
        context = {
            "pasajeros":pasajeros_db,
            "rol":rol
        }
    )

@app.post("/administracion/administradores/agregar")
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

@app.get("/administracion/administradores")
def registrar_administrador(request: Request, rol: str, id_admin: int = 0):
    return templates.TemplateResponse(
        request = request,
        name = "administrador.html",
        context= {
            "rol": rol,
            "id_admin": id_admin
        }
    )

@app.get("/api/calcular-tarifa")
def api_calcular_tarifa(distancia_km: float, tiempo_minutos: float):
    costo_final = calcular_costo_viaje(distancia_km, tiempo_minutos)
    
    return JSONResponse({"costo_total": costo_final})

@app.get("/api/chofer/verificar-viaje/{id_chofer}")
def verificar_viaje_pendiente(id_chofer: int, db: Session = Depends(get_db)):
    """
    Consultada cada 5s desde el panel del chofer (via base.html).
    Devuelve si hay un viaje EN_ESPERA asignado a este chofer, y su id,
    para poder redirigir a /chofer/aceptar-viaje.
    """
    viaje_db = db.query(models.Viajes).filter(
        models.Viajes.id_chofer == id_chofer,
        models.Viajes.estado_viaje == models.EstadoViaje.EN_ESPERA
    ).order_by(models.Viajes.id_viaje.desc()).first()

    if viaje_db:
        return JSONResponse({"viaje_pendiente": True, "id_viaje": viaje_db.id_viaje})
    return JSONResponse({"viaje_pendiente": False})

@app.post("/chofer/registrar-contacto")
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
    
@app.post("/chofer/registrar-datos")
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
        id_banco = banco_db.id_banco,
        numero_cuenta = numero_cuenta
    )
    db.add(nueva_cuenta)
    db.commit()

    url_destino = f"/panel-chofer?id_chofer={id_chofer}"
    return RedirectResponse(url=url_destino, status_code=303)


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
    matricula_formateada = placa.upper().strip()
    
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

@app.post("/chofer/estado")
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
    
@app.get("/reporte-viajes")
def reporte_viajes(request: Request, db: Session = Depends(get_db)):
    viajes_db = db.query(models.Viajes).all()
    return templates.TemplateResponse(
        request=request, 
        name="reporte.html", 
        context={"viajes": viajes_db}
    )

@app.get("/administracion/historial-pagos")
def historial_pagos_ganancias(
    request: Request, 
    id_admin: int, 
    rol: str, 
    fecha_inicio: str = None, 
    fecha_fin: str = None, 
    chofer_id: str = None, 
    db: Session = Depends(get_db)
):
    # Traemos TODOS los pagos (tanto pendientes como cancelados)
    query = db.query(models.PagosChoferes, models.Viajes, models.Usuarios).join(
        models.Viajes, models.PagosChoferes.id_viaje == models.Viajes.id_viaje
    ).join(
        models.Usuarios, models.PagosChoferes.id_chofer == models.Usuarios.id_usuario
    )

    # Aplicamos filtros basados en la FECHA DEL VIAJE (los pendientes aún no tienen fecha de pago)
    if fecha_inicio and fecha_inicio.strip() != "":
        fecha_ini_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        query = query.filter(models.Viajes.fecha_viaje >= fecha_ini_date)
        
    if fecha_fin and fecha_fin.strip() != "":
        fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        query = query.filter(models.Viajes.fecha_viaje <= fecha_fin_date)
        
    if chofer_id and chofer_id.strip() != "":
        query = query.filter(models.PagosChoferes.id_chofer == int(chofer_id))

    # Ordenamos por la fecha en que se realizó el viaje
    todos_los_registros = query.order_by(models.Viajes.fecha_viaje.desc()).all()

    pagados = []
    pendientes = []
    
    total_viajes = 0.0
    total_pagado = 0.0
    total_ganancia_empresa = 0.0

    # Separación lógica y finanzas
    for pago, viaje, usuario in todos_los_registros:
        total_viajes += viaje.costo_viaje
        
        if pago.id_administrador is not None:
            # Viaje Cancelado (Pagado al chofer)
            pagados.append((pago, viaje, usuario))
            total_pagado += pago.monto_cancelado
            total_ganancia_empresa += (viaje.costo_viaje - pago.monto_cancelado)
        else:
            # Viaje Pendiente
            pendientes.append((pago, viaje, usuario))
            # La empresa ya retiene el 30% como ganancia aunque el pago al chofer esté pendiente
            total_ganancia_empresa += (viaje.costo_viaje * 0.30)

    choferes_lista = db.query(models.Usuarios).filter(models.Usuarios.rol == 'chofer').all()

    return templates.TemplateResponse(
        request=request,
        name="historial_pagos_admin.html",
        context={
            "pagados": pagados,
            "pendientes": pendientes,
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

@app.get("/administracion/personal")
def ver_personal(request: Request, rol: str, id_admin: int, db: Session = Depends(get_db)):
    # Medida de seguridad: Solo un superadmin puede entrar aquí
    if rol != "superadmin":
        return RedirectResponse(url=f"/panel-administracion?rol={rol}&id_admin={id_admin}", status_code=303)
        
    # Filtramos la tabla de Usuarios para traer solo a los que administran el sistema
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

@app.post("/administracion/personal/promover")
def promover_admin(
    id_usuario: int = Form(...),
    id_admin: int = Form(...),
    rol: str = Form(...),
    db: Session = Depends(get_db)
):
    # Buscamos al usuario que será ascendido
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_usuario).first()
    
    # Confirmamos que exista y que actualmente sea un administrador normal
    if usuario_db and usuario_db.rol == "admin":
        usuario_db.rol = "superadmin"
        db.commit()
        
    return RedirectResponse(url=f"/administracion/personal?rol={rol}&id_admin={id_admin}", status_code=303)