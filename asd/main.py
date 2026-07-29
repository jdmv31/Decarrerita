import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import auth, pasajeros, choferes, viajes, admin

app = FastAPI(title="Decarrerita API")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(auth.router)
app.include_router(pasajeros.router)
app.include_router(choferes.router)
app.include_router(viajes.router)
app.include_router(admin.router)
