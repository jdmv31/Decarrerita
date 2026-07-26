from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class EstadoChofer (enum.Enum):
    DISPONIBLE = "DISPONIBLE"
    EN_VIAJE = "EN VIAJE"
    DESCONECTADO = "DESCONECTADO"

class EstadoViaje(enum.Enum):
    CANCELADO = "cancelado"
    PAGO = "pago"
    EN_ESPERA = "en espera de pago"
    FINALIZADO = "finalizado"

class RevisionVehiculo(Base):
    __tablename__ = "revisionvehiculo"
    id_revision = Column(Integer,primary_key = True, index = True)
    id_vehiculo = Column(String,ForeignKey("vehiculos.matricula"))
    puntuacion = Column(Float,default=0.0)
    fecha_revision = Column(Date,server_default = func.current_date())
    
class Vehiculos (Base):
    __tablename__ = "vehiculos"
    matricula = Column(String,primary_key = True, index = True)
    id_chofer = Column(Integer,ForeignKey("choferes.id_chofer"))
    marca = Column(String, nullable = False)
    modelo = Column(String, nullable = False)
    annio = Column(Integer, nullable = False)
    color = Column(String, nullable = False)

class ContactosEmergencia(Base):
    __tablename__ = "contactosemergencia"
    id_contacto = Column(Integer,primary_key = True)
    numero_telefonico = Column(String, nullable = False)

class AgendaContactos(Base):
    __tablename__ = "agendacontactos"
    id_agenda = Column(Integer,primary_key=True)
    id_chofer = Column(Integer,ForeignKey("choferes.id_chofer"))
    id_contacto = Column(Integer,ForeignKey("contactosemergencia.id_contacto"))
    nombre_contacto = Column(String,nullable = False)


class Choferes(Base):
    __tablename__ = "choferes"
    id_chofer = Column(Integer,ForeignKey("usuarios.id_usuario"),primary_key = True)
    calificacion = Column(Float, default = 0.0)
    saldo_pendiente = Column(Float, default = 0.0)
    estado_chofer = Column(Enum(EstadoChofer),default = EstadoChofer.DESCONECTADO)

class Pasajeros(Base):
    __tablename__ = "pasajeros"
    id_pasajero = Column(Integer,ForeignKey("usuarios.id_usuario"),primary_key = True)
    saldo_disponible = Column(Float, default = 0.0)
    calificacion = Column(Float, default = 0.0)    

class Banco (Base):
    __tablename__ = "banco"
    id_banco = Column(Integer, primary_key = True)
    nombre = Column(String, nullable = False)

class HistorialRecargas(Base):
    __tablename__ = "historialrecargas"
    id_historial = Column(Integer,primary_key = True)
    id_pasajero = Column(Integer,ForeignKey("pasajeros.id_pasajero"))
    id_banco = Column(Integer,ForeignKey("banco.id_banco"))
    fecha = Column(Date, server_default = func.current_date())
    numero_referencia = Column(String, unique = True)
    monto_recargado = Column(Float, nullable = False)

class Viajes (Base):
    __tablename__ = "viajes"
    id_viaje = Column(Integer, primary_key = True)
    id_vehiculo = Column(String,ForeignKey("vehiculos.matricula"))
    id_chofer = Column(Integer,ForeignKey("choferes.id_chofer"))
    id_pasajero = Column(Integer,ForeignKey("pasajeros.id_pasajero"))
    duracion = Column(Float, nullable = False)
    distancia = Column (Float, nullable = False)
    lugar_inicio = Column(String, nullable = False)
    lugar_destino = Column(String, nullable = False)
    fecha_viaje = Column(Date, nullable = False)
    estado_viaje = Column(Enum(EstadoViaje), nullable = False, default = EstadoViaje.EN_ESPERA)
    costo_viaje = Column(Float, nullable = False)
    puntuacion_chofer = Column(Integer, nullable=True)
    puntuacion_pasajero = Column(Integer, nullable=True)


class EvaluacionChofer(Base):
    __tablename__ = "evaluacionchofer"
    id_evaluacion = Column(Integer,primary_key = True)
    id_chofer = Column(Integer, ForeignKey("choferes.id_chofer"))
    puntuacion = Column(Integer, nullable = False)
    fecha_evaluacion = Column(Date, server_default=func.current_date())

class DatosBancarios(Base):
    __tablename__ = "datosbancarios"
    id_datos = Column(Integer,primary_key = True)
    id_chofer = Column(Integer, ForeignKey("choferes.id_chofer"))
    id_banco = Column(Integer,ForeignKey("banco.id_banco"))
    numero_cuenta = Column(String, unique = True, nullable = False)

class PagosChoferes(Base):
    __tablename__ = "pagoschoferes"
    id_pago = Column(Integer,primary_key = True)
    id_viaje = Column(Integer,ForeignKey("viajes.id_viaje"))
    id_administrador = Column(Integer,ForeignKey("usuarios.id_usuario"), nullable=True)
    id_chofer = Column(Integer,ForeignKey("choferes.id_chofer"))
    fecha_pago = Column(Date, nullable=True) 
    numero_referencia = Column(Integer, unique=True, nullable=True) 
    monto_cancelado = Column(Float, nullable=True)

class Usuarios(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer,primary_key = True)
    nombre = Column(String,nullable = False)
    apellido = Column(String, nullable = False)
    direccion = Column(String, nullable = False)
    rol = Column(String, nullable = False)
    cedula = Column(Integer,unique = True, nullable = False)
    correo = Column(String, unique = True, nullable = False)
    password = Column(String, nullable = False)
