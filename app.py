from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import db
import ai
import re
import json

# Initialize Database on Startup
db.init_db()

app = FastAPI(title="KDI Power AI WhatsApp Assistant")

from routes import whatsapp, dashboard
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
import os

# Create static directories if they don't exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/images/kdi-logo-90x90.png")

# Include Routers
app.include_router(whatsapp.router)
app.include_router(dashboard.router)