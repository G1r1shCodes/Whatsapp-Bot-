from fastapi import FastAPI, Request, Response
import db

# Initialize Database on Startup
db.init_db()

app = FastAPI(title="KDI Power AI WhatsApp Assistant")

from routes import whatsapp, dashboard
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, JSONResponse
import os
import json
import auth

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

@app.get("/login")
async def login_page():
    return HTMLResponse(content=auth.LOGIN_PAGE_HTML)

@app.post("/api/login")
async def api_login(request: Request):
    body = await request.json()
    password = body.get("password", "")
    
    if not auth.DASHBOARD_SECRET:
        # No secret set — auto-login (dev mode)
        response = JSONResponse({"success": True})
        return response
    
    if password == auth.DASHBOARD_SECRET:
        response = JSONResponse({"success": True})
        response.set_cookie(
            key=auth.COOKIE_NAME,
            value=auth._hash_secret(auth.DASHBOARD_SECRET),
            httponly=True,
            samesite="lax",
            max_age=86400 * 7,  # 7 days
        )
        return response
    
    return JSONResponse({"error": "Invalid password"}, status_code=401)

# Include Routers
app.include_router(whatsapp.router)
app.include_router(dashboard.router)