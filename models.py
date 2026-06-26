from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum

class EstadoViaje(enum.Enum):
    CANCELADO = "cancelado"
    PAGO = "pago"
    EN_ESPERA = "en espera de pago"

class RevisionVehiculo(Base):
    __tablename__ = "revisionvehiculo"
    id = Column(Integer,primary_key = True, index = True)
    id_vehiculo = Column(String,ForeignKey("vehiculos.matricula"))
    puntuacion = Column(Float,nullable = False)
    fecha_revision = Column(Date,nullable = False)
    
class Vehiculos (Base):
    __tablename__ = "vehiculos"
    matricula = Column(String,primary_key = True, index = True)
    id_chofer = Column(Integer,ForeignKey("choferes.id"))
    marca = Column(String, nullable = False)
    modelo = Column(String, nullable = False)
    annio = Column(Integer, nullable = False)
    color = Column(String, nullable = False)

class Choferes(Base):
    __tablename__ = "choferes"
    id = Column(Integer,ForeignKey("usuarios.id"),primary_key = True)
    calificacion = Column(Float, default = 0.0)
    saldo_pendiente = Column(Float, default = 0.0)

class Pasajeros(Base):
    __tablename__ = "pasajeros"
    id = Column(Integer,ForeignKey("usuarios.id"),primary_key = True)
    saldo_disponible = Column(Float, default = 0.0)
    calificacion = Column(Float, default = 0.0)    

class Banco (Base):
    __tablename__ = "banco"
    id = Column(Integer, primary_key = True)
    nombre = Column(String, nullable = False)

class HistorialRecargas(Base):
    __tablename__ = "historialrecargas"
    id = Column(Integer,primary_key = True)
    id_pasajero = Column(Integer,ForeignKey("pasajeros.id"))
    id_banco = Column(Integer,ForeignKey("banco.id"))
    fecha = Column(Date, nullable = False)
    numero_referencia = Column(Integer, unique = True)
    monto_recargado = Column(Float, nullable = False)

class Viajes (Base):
    __tablename__ = "viajes"
    id = Column(Integer, primary_key = True)
    id_vehiculo = Column(String,ForeignKey("vehiculos.matricula"))
    id_chofer = Column(Integer,ForeignKey("choferes.id"))
    id_pasajero = Column(Integer,ForeignKey("pasajeros.id"))
    duracion = Column(Float, nullable = False)
    distancia = Column (Float, nullable = False)
    lugar_inicio = Column(String, nullable = False)
    lugar_destino = Column(String, nullable = False)
    fecha_viaje = Column(Date, nullable = False)
    estado_viaje = Column(Enum(EstadoViaje), nullable = False, default = EstadoViaje.EN_ESPERA)
    costo_viaje = Column(Float, nullable = False)


class EvaluacionChofer(Base):
    __tablename__ = "evaluacionchofer"
    id = Column(Integer,primary_key = True)
    id_chofer = Column(Integer, ForeignKey("choferes.id"))
    puntuacion = Column(Integer, nullable = False)
    fecha_evaluacion = Column(Date, nullable = False)

class ContactosEmergencia(Base):
    __tablename__ = "contactosemergencia"
    id = Column(Integer,primary_key = True)
    id_chofer = Column(Integer, ForeignKey("choferes.id"))
    numero_telefonico = Column(String, nullable = False)
    nombre_contacto = Column(String, nullable = False)

class DatosBancarios(Base):
    __tablename__ = "datosbancarios"
    id = Column(Integer,primary_key = True)
    id_chofer = Column(Integer, ForeignKey("choferes.id"))
    id_banco = Column(Integer,ForeignKey("banco.id"))
    numero_cuenta = Column(Integer, unique = True, nullable = False)

class PagosChoferes(Base):
    __tablename__ = "pagoschoferes"
    id = Column(Integer,primary_key = True)
    id_viaje = Column(Integer,ForeignKey("viajes.id"))
    id_administrador = Column(Integer,ForeignKey("usuarios.id"))
    id_chofer = Column (Integer,ForeignKey("choferes.id"))
    fecha_pago = Column (Date,nullable = False)
    numero_referencia = Column (Integer, unique = True, nullable = False)
    monto_cancelado = Column (Float, nullable = False)

class Usuarios(Base):
    __tablename__ = "usuarios"
    id = Column(Integer,primary_key = True)
    nombre = Column(String,nullable = False)
    apellido = Column(String, nullable = False)
    direccion = Column(String, nullable = False)
    rol = Column(String, nullable = False)
    cedula = Column(Integer,unique = True, nullable = False)
    correo = Column(String, unique = True, nullable = False)
    password = Column(String, nullable = False)
