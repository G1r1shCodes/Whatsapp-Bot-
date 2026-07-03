import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
import re

# Helper to load .env variables manually
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

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def request_supabase(endpoint, method="GET", data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
        
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_data, method=method)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    
    try:
        with urllib.request.urlopen(req) as res:
            res_content = res.read().decode("utf-8")
            if res_content:
                return json.loads(res_content)
            return []
    except Exception as e:
        print(f"Supabase API error on {endpoint} [{method}]: {e}")
        return []

def init_db():
    # Database tables are initialized on Supabase via MCP SQL execute
    pass

# Session Management helpers
def get_session(phone):
    res = request_supabase("sessions", "GET", params={"phone": f"eq.{phone}"})
    if res:
        row = res[0]
        # Parse data JSON
        state_data = row["data"]
        if isinstance(state_data, str):
            state_data = json.loads(state_data)
        return {
            "current_state": row["state"],
            "state_data": state_data,
            "last_active": row["updated_at"]
        }
    return None

def save_session(phone, current_state, state_data):
    exists = get_session(phone)
    data = {
        "phone": phone,
        "state": current_state,
        "step": state_data.get("step", 0),
        "data": state_data,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    if exists:
        request_supabase("sessions", "PATCH", data=data, params={"phone": f"eq.{phone}"})
    else:
        request_supabase("sessions", "POST", data=data)

def delete_session(phone):
    request_supabase("sessions", "DELETE", params={"phone": f"eq.{phone}"})

# Lead Management helpers
def create_lead(phone, name, company, email, location, product_interest, quantity, requirements):
    data = {
        "phone": phone,
        "name": name,
        "company": company,
        "email": email,
        "location": location,
        "product_interest": product_interest,
        "quantity": quantity,
        "requirements": requirements,
        "status": "New",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    res = request_supabase("leads", "POST", data=data)
    if res:
        return res[0]["id"]
    return None

def get_leads(status_filter=None, search_query=None):
    params = {"order": "created_at.desc"}
    if status_filter:
        params["status"] = f"eq.{status_filter}"
    if search_query:
        search_escaped = f"%{search_query}%"
        params["or"] = f"(name.ilike.{search_escaped},phone.ilike.{search_escaped},company.ilike.{search_escaped},requirements.ilike.{search_escaped})"
        
    return request_supabase("leads", "GET", params=params)

def update_lead_status(lead_id, status):
    data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    request_supabase("leads", "PATCH", data=data, params={"id": f"eq.{lead_id}"})

def get_lead_by_phone(phone):
    params = {
        "phone": f"eq.{phone}",
        "order": "created_at.desc",
        "limit": "1"
    }
    res = request_supabase("leads", "GET", params=params)
    return res[0] if res else None

# Product Catalog Management helpers
def get_all_products(category_filter=None):
    params = {}
    if category_filter:
        params["category"] = f"eq.{category_filter}"
    return request_supabase("products", "GET", params=params)

def get_product_by_id(product_name):
    res = request_supabase("products", "GET", params={"name": f"eq.{product_name}"})
    return res[0] if res else None

def update_product_price_and_stock(product_name, price, stock_status):
    data = {
        "price_per_meter": price,
        "stock_status": stock_status
    }
    request_supabase("products", "PATCH", data=data, params={"name": f"eq.{product_name}"})

def upsert_product(product_data):
    name = product_data.get("name")
    if not name:
        return None
    
    existing = get_product_by_id(name)
    if existing:
        request_supabase("products", "PATCH", data=product_data, params={"name": f"eq.{name}"})
        return "updated"
    else:
        request_supabase("products", "POST", data=product_data)
        return "created"

def get_product_categories():
    products = get_all_products()
    categories = list(set([p["category"] for p in products]))
    return categories

# Chat History loggers
def log_chat_message(phone, direction, body):
    data = {
        "phone": phone,
        "direction": direction,
        "body": body,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    request_supabase("chat_history", "POST", data=data)

def get_chat_history(phone):
    params = {
        "phone": f"eq.{phone}",
        "order": "created_at.asc"
    }
    res = request_supabase("chat_history", "GET", params=params)
    for row in res:
        row["timestamp"] = row["created_at"]
    return res
