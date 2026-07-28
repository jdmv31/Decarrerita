# Decarrerita

## 📑 Tabla de Contenidos

- [Descripción](#-descripcion)
- [Características Clave](#-caracteristicas-clave)
- [Tecnologías Empleadas](#️-tecnologias-empleadas)
- [Dependencias Empleadas](#-dependencias-empleadas)
- [Estructura del Proyecto](#-estructura-del-proyecto)

## 📝 Descripción

Decarrerita es una aplicación backend en Python desarrollada con el framework FastAPI. Ofrece una base estructurada para construir servicios de API respaldados por bases de datos relacionales utilizando PostgreSQL. La aplicación utiliza Uvicorn como servidor ASGI para gestionar las peticiones HTTP entrantes y servir las rutas de FastAPI. Las interacciones con la base de datos y la evolución de los esquemas se gestionan mediante Alembic, lo que permite flujos de trabajo de migración de bases de datos sistemáticos.

## ✨ Características Clave

- **⚡ Framework Web FastAPI** — Implementa rutas y controladores de API en el backend utilizando Python y FastAPI.
- **🐘 Integración con Base de Datos PostgreSQL** — Almacena y gestiona los datos de la aplicación mediante una base de datos relacional PostgreSQL.
- **🔄 Migraciones de Esquema con Alembic** — Rastrea y ejecuta cambios en el esquema de la base de datos mediante scripts de migración de Alembic.
- **🚀 Servidor ASGI Uvicorn** — Ejecuta la aplicación de FastAPI utilizando Uvicorn como interfaz de servidor asíncrono.

## 🛠️ Tecnologías Empleadas

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white) ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

## 📦 Dependencias Empleadas

```
alembic: 1.18.5
annotated-doc: 0.0.4
annotated-types: 0.7.0
anyio: 4.13.0
click: 8.4.1
colorama: 0.4.6
fastapi: 0.136.3
greenlet: 3.5.1
h11: 0.16.0
idna: 3.18
Jinja2: 3.1.6
Mako: 1.3.12
MarkupSafe: 3.0.3
psycopg2-binary: 2.9.12
pydantic: 2.13.4
```
## 📁 Estructura del Proyecto
```
carrerita
├── database.py
├── dependencies.py
├── main.py
├── models.py
├── requirements.txt
├── root.py
├── routers
│   ├── admin.py
│   ├── auth.py
│   ├── choferes.py
│   ├── pasajeros.py
│   └── viajes.py
├── static
│   ├── css
│   │   └── style.css
│   ├── images
│   │   ├── fondo.jpg
│   │   ├── fondobanner.png
│   │   ├── fondomapa.png
│   │   └── usuario.png
│   └── js
│       ├── mapa.js
│       └── script.js
├── templates
│   ├── aceptar_viaje.html
│   ├── administrador.html
│   ├── base.html
│   ├── choferes.html
│   ├── contactos.html
│   ├── datos_bancarios.html
│   ├── evaluaciones_psicologicas.html
│   ├── historial_chofer.html
│   ├── historial_pagos_admin.html
│   ├── historial_recargas.html
│   ├── historial_viajes.html
│   ├── index.html
│   ├── informacion_chofer.html
│   ├── informacion_pasajero.html
│   ├── lista_personal.html
│   ├── pagos_pendientes.html
│   ├── panel_administracion.html
│   ├── panel_chofer.html
│   ├── panel_pasajero.html
│   ├── panel_saldo.html
│   ├── pasajeros.html
│   ├── recarga_saldo.html
│   ├── registro_vehiculo.html
│   ├── reporte.html
│   ├── revisiones_vehiculares.html
│   ├── revisiones_vencimiento.html
│   ├── solicitar_viaje.html
│   ├── viaje_chofer.html
│   └── viaje_pasajero.html
└── vercel.json
```