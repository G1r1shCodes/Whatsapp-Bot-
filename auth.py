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
    <title>KDI Power - System Auth</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0A0A0A;
            --surface-color: #111111;
            --copper-accent: #E86A33;
            --copper-dim: rgba(232, 106, 51, 0.2);
            --text-primary: #FFFFFF;
            --text-secondary: #888888;
            --border-color: #222222;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                linear-gradient(var(--border-color) 1px, transparent 1px),
                linear-gradient(90deg, var(--border-color) 1px, transparent 1px);
            background-size: 40px 40px;
            background-position: center center;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
        }
        .auth-container {
            width: 100%;
            max-width: 440px;
            padding: 2rem;
        }
        .brand-header {
            margin-bottom: 3rem;
            position: relative;
        }
        .brand-header::before {
            content: '';
            position: absolute;
            left: -2rem;
            top: 50%;
            width: 1rem;
            height: 2px;
            background: var(--copper-accent);
        }
        .brand-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }
        .brand-header span {
            display: block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            margin-top: 0.5rem;
            letter-spacing: 0.1em;
        }
        .auth-card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-top: 3px solid var(--copper-accent);
            padding: 2.5rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            position: relative;
        }
        .auth-card::after {
            content: '';
            position: absolute;
            bottom: -1px;
            right: -1px;
            width: 15px;
            height: 15px;
            border-bottom: 1px solid var(--copper-accent);
            border-right: 1px solid var(--copper-accent);
        }
        .input-group {
            margin-bottom: 2rem;
        }
        .input-group label {
            display: block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            text-transform: uppercase;
        }
        .input-group input {
            width: 100%;
            background: transparent;
            border: none;
            border-bottom: 1px solid var(--border-color);
            padding: 0.75rem 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.2rem;
            color: var(--text-primary);
            outline: none;
            transition: all 0.2s ease;
        }
        .input-group input:focus {
            border-bottom-color: var(--copper-accent);
            background: linear-gradient(to top, var(--copper-dim) 0%, transparent 100%);
        }
        .auth-card button {
            width: 100%;
            background: var(--copper-accent);
            color: #000;
            border: none;
            padding: 1rem;
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        .auth-card button:hover {
            background: #fff;
        }
        .error {
            font-family: 'JetBrains Mono', monospace;
            color: var(--copper-accent);
            font-size: 0.8rem;
            margin-top: 1rem;
            display: none;
            border-left: 2px solid var(--copper-accent);
            padding-left: 0.75rem;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="brand-header">
            <h1>KDI POWER</h1>
            <span>Command Center • Auth Required</span>
        </div>
        <div class="auth-card">
            <form onsubmit="return handleLogin(event)">
                <div class="input-group">
                    <label for="password">System Access Key</label>
                    <input type="password" id="password" autocomplete="current-password" autofocus>
                </div>
                <button type="submit">Authenticate</button>
            </form>
            <div class="error" id="error-msg">ACCESS DENIED. INVALID KEY.</div>
        </div>
    </div>
    <script>
        async function handleLogin(e) {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            const originalText = btn.textContent;
            btn.textContent = 'VERIFYING...';
            
            const pw = document.getElementById('password').value;
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password: pw})
                });
                if (res.ok) {
                    btn.textContent = 'ACCESS GRANTED';
                    setTimeout(() => window.location.href = '/dashboard', 300);
                } else {
                    document.getElementById('error-msg').style.display = 'block';
                    btn.textContent = originalText;
                }
            } catch (err) {
                document.getElementById('error-msg').style.display = 'block';
                btn.textContent = originalText;
            }
            return false;
        }
    </script>
</body>
</html>"""
