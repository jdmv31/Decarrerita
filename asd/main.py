import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import engine, SessionLocal
import models
import random
from datetime import datetime,time

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
        
    elif usuario_db.rol.lower() == "superadmin":
        url_destino = f"/panel-administracion?rol={usuario_db.rol}"
        return RedirectResponse(url=url_destino, status_code=303)

def generar_referencia():
    tiempo = datetime.now().strftime("%Y%m%d%H%M%S")
    numero = random.randint(1000,9999)
    return f"{tiempo}{numero}"

@app.post("/pasajero/saldo/procesar-recarga")
def recarga(
    id_pasajero: int = Form(...),
    banco: str = Form(...),
    nro_cuenta: str = Form(...),
    monto: float = Form(...),
    db: Session = Depends(get_db)
):
    numero_referencia = generar_referencia()
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
        numero_cuenta = nro_cuenta,
        monto_recargado = monto,
        numero_referencia = numero_referencia
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

@app.get("/pasajero/solicitar-viaje")
def solicitar_viaje(request: Request, id_pasajero: int):
    return templates.TemplateResponse(
        request=request,
        name = "solicitar_viaje.html",
        context={"id_pasajero":id_pasajero}
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
    choferes_disponibles = db.query(models.Choferes).filter(
        models.Choferes.estado_chofer == models.EstadoChofer.DISPONIBLE
    ).all()

    if not choferes_disponibles:
        return templates.TemplateResponse(
            request=request,
            name="solicitar_viaje.html",
            context={
                "id_pasajero": id_pasajero,
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

    tarifa_por_km = 0.50
    tarifa_base = 1.00
    tarifa_minima = 2.50 
    precio_min = 0.15
    multiplicador_tiempo = obtener_multiplicador_horario()
    costo_calculado = tarifa_base + (distancia_km * tarifa_por_km) + (tiempo_minutos * (precio_min * multiplicador_tiempo))


    costo_final = max(costo_calculado, tarifa_minima)
    costo_total = round(costo_final, 2)

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
    
    chofer_asignado.estado_chofer = models.EstadoChofer.EN_VIAJE

    db.add(nuevo_viaje)
    db.commit()

    url_destino = f"/panel-pasajero?id_pasajero={id_pasajero}"
    return RedirectResponse(url=url_destino, status_code=303)

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
def panel_administracion(request: Request, rol: str):
    return templates.TemplateResponse(
        request = request,
        name = "panel_administracion.html",
        context = {"rol":rol}
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

@app.get ("/panel-chofer")
def panel_chofer(request: Request, id_chofer: int, db: Session = Depends(get_db)):
    evaluacion_db = db.query(models.EvaluacionChofer).filter(models.EvaluacionChofer.id_chofer == id_chofer).first()
    puntuacion = evaluacion_db.puntuacion if evaluacion_db is not None else 0 
    cantidad_contactos = db.query(models.AgendaContactos).filter(models.AgendaContactos.id_chofer == id_chofer).count()
    vehiculos_aprobados = db.query(models.Vehiculos).join(
        models.RevisionVehiculo, models.Vehiculos.matricula == models.RevisionVehiculo.id_vehiculo
    ).filter(
        models.Vehiculos.id_chofer == id_chofer,
        models.RevisionVehiculo.puntuacion >= 65
    ).all()

    return templates.TemplateResponse(
        request= request,
        name = "panel_chofer.html",
        context={
            "puntuacion": puntuacion, 
            "id_chofer": id_chofer,
            "vehiculos": vehiculos_aprobados,
            "cantidad_contactos": cantidad_contactos
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
        
    url_destino = f"/panel-administracion?rol={rol_creador}"
    return RedirectResponse(url = url_destino, status_code=303)

@app.get("/administracion/administradores")
def registrar_administrador(request: Request, rol: str):
    return templates.TemplateResponse(
        request = request,
        name = "administrador.html",
        context= {"rol":rol}
    )

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
    if chofer_db:
        chofer_db.estado_chofer = estado_nuevo
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