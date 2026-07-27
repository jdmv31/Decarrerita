from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import models
from dependencies import get_db, templates

router = APIRouter(
    tags=["Pasajeros"]
)

@router.get("/panel-pasajero")
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

@router.get("/pasajero/perfil")
def perfil_pasajero(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    usuario_db = db.query(models.Usuarios).filter(models.Usuarios.id_usuario == id_pasajero).first()
    pasajero_db = db.query(models.Pasajeros).filter(models.Pasajeros.id_pasajero == id_pasajero).first()
    
    return templates.TemplateResponse(
        request = request,
        name = "informacion_pasajero.html",
        context = {
            "pasajero": pasajero_db,
            "usuario": usuario_db,
            "id_pasajero": id_pasajero
        }
    )

@router.get("/pasajero/saldo")
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

@router.get("/pasajero/saldo/recargar")
def recargar_saldo(request: Request, id_pasajero: int):
    return templates.TemplateResponse(
        request = request,
        name = "recarga_saldo.html",
        context = {"id_pasajero": id_pasajero}
    )

@router.post("/pasajero/saldo/procesar-recarga")
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

@router.get("/pasajero/saldo/historial")
def ver_historial(request: Request, id_pasajero: int, db: Session = Depends(get_db)):
    recargas_db = db.query(models.HistorialRecargas, models.Banco).join(
        models.Banco, models.HistorialRecargas.id_banco == models.Banco.id_banco
    ).filter(
        models.HistorialRecargas.id_pasajero == id_pasajero
    ).order_by(models.HistorialRecargas.fecha.desc()).all()
    
    return templates.TemplateResponse(
        request = request,
        name = "historial_recargas.html",
        context = {
            "id_pasajero": id_pasajero,
            "recargas": recargas_db
        }
    )