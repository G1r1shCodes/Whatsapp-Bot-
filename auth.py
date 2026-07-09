import os
import hashlib
import secrets
from functools import wraps
from fastapi import Request, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from logger import get_logger

logger = get_logger(__name__)

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

load_env()

DASHBOARD_SECRET = os.environ.get("DASHBOARD_SECRET", "")
COOKIE_NAME = "kdi_auth"

def _hash_secret(secret: str) -> str:
    """Hash the secret for secure comparison."""
    return hashlib.sha256(secret.encode()).hexdigest()

def verify_auth(request: Request) -> bool:
    """Check if the request has a valid auth cookie or header."""
    if not DASHBOARD_SECRET:
        # No secret configured — allow access (dev mode)
        return True
    
    # Check cookie first
    cookie_val = request.cookies.get(COOKIE_NAME, "")
    if cookie_val and cookie_val == _hash_secret(DASHBOARD_SECRET):
        return True
    
    # Check Authorization header (for API calls)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token == DASHBOARD_SECRET:
            return True
    
    # Check query parameter (for initial login)
    query_token = request.query_params.get("token", "")
    if query_token and query_token == DASHBOARD_SECRET:
        return True
    
    return False

def require_auth(request: Request):
    """Raise 403 if not authenticated. Call this at the start of protected routes."""
    if not verify_auth(request):
        raise HTTPException(status_code=403, detail="Unauthorized. Please log in.")

LOGIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KDI Power - Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e2e8f0;
        }
        .login-card {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 40px;
            width: 380px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            text-align: center;
        }
        .login-card h1 {
            font-size: 1.5rem;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #06b6d4, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .login-card p {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 30px;
        }
        .login-card input {
            width: 100%;
            padding: 12px 20px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.3);
            color: white;
            font-size: 1rem;
            outline: none;
            margin-bottom: 15px;
            transition: border-color 0.3s;
        }
        .login-card input:focus {
            border-color: #06b6d4;
            box-shadow: 0 0 10px rgba(6,182,212,0.2);
        }
        .login-card button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 10px;
            background: linear-gradient(135deg, #06b6d4, #6366f1);
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .login-card button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(6,182,212,0.4);
        }
        .error {
            color: #f87171;
            font-size: 0.85rem;
            margin-top: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>🔒 KDI Power Dashboard</h1>
        <p>Enter your access password to continue</p>
        <form onsubmit="return handleLogin(event)">
            <input type="password" id="password" placeholder="Dashboard password..." autofocus>
            <button type="submit">Login</button>
        </form>
        <p class="error" id="error-msg">Invalid password. Please try again.</p>
    </div>
    <script>
        async function handleLogin(e) {
            e.preventDefault();
            const pw = document.getElementById('password').value;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password: pw})
            });
            if (res.ok) {
                window.location.href = '/dashboard';
            } else {
                document.getElementById('error-msg').style.display = 'block';
            }
            return false;
        }
    </script>
</body>
</html>"""
