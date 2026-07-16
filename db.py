import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
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

from logger import get_logger
logger = get_logger(__name__)

load_env()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def request_supabase(endpoint, method="GET", data=None, params=None):
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning(f"SUPABASE_URL or SUPABASE_KEY is missing. Returning mock data for {endpoint}.")
        if endpoint == "leads":
            return [
                {"id": 1, "phone": "1234567890", "name": "John Doe", "company": "Acme Corp", "product_interest": "Power Cables", "status": "New", "created_at": datetime.utcnow().isoformat()},
                {"id": 2, "phone": "0987654321", "name": "Jane Smith", "company": "Tech Solutions", "product_interest": "House Wires", "status": "Quoted", "created_at": datetime.utcnow().isoformat()}
            ]
        elif endpoint == "products":
            return [
                {"name": "1.5 sq mm House Wire", "category": "House Wires", "conductor": "Copper", "size": "1.5 sq mm", "core": 1, "insulation": "PVC", "price_per_meter": 12.5, "stock_status": "In Stock", "specifications": "Flame retardant house wire"},
                {"name": "2.5 sq mm Power Cable", "category": "Power Cables", "conductor": "Aluminium", "size": "2.5 sq mm", "core": 3, "insulation": "XLPE", "price_per_meter": 45.0, "stock_status": "In Stock", "specifications": "Heavy duty power cable"}
            ]
        return []

    try:
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
        
        with urllib.request.urlopen(req) as res:
            res_content = res.read().decode("utf-8")
            if res_content:
                return json.loads(res_content)
            return []
    except Exception as e:
        logger.error(f"Supabase API error on {endpoint} [{method}]: {e}")
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

DUMMY_STATUS_OVERRIDES = {}
DUMMY_PRODUCT_OVERRIDES = {}

def get_static_dummy_leads():
    leads = []
    
    product_pool = [
        {"product": "KDI 1.5 sq mm FR House Wire (Copper)", "category": "House Wires"},
        {"product": "KDI 2.5 sq mm FRLS House Wire", "category": "House Wires"},
        {"product": "KDI 1.0 sq mm PVC Insulated Wire", "category": "House Wires"},
        {"product": "Single Core 4.0 sq mm House Wire", "category": "House Wires"},
        {"product": "KDI Solar Cable 4 sq mm DC", "category": "Solar Cables"},
        {"product": "KDI Solar Cable 6 sq mm UV Resistant", "category": "Solar Cables"},
        {"product": "KDI Submersible Cable 3 Core 2.5 sq mm", "category": "Submersible Cables"},
        {"product": "KDI 3 Core Flat Submersible Cable 4 sq mm", "category": "Submersible Cables"},
        {"product": "Copper Control Cable 4 Core 1.5 sq mm", "category": "Control Cables"},
        {"product": "Copper Control Cable 10 Core 2.5 sq mm", "category": "Control Cables"},
        {"product": "Copper Flexible Cable 3 Core 1.5 sq mm", "category": "Flexible Cables"},
        {"product": "Flexible PVC Insulated Cord Cable 2 Core", "category": "Flexible Cables"},
        {"product": "11kV HT Armoured Cable 3C x 95 sq mm", "category": "HT Cables"},
        {"product": "33kV HT Armoured Cable XLPE", "category": "HT Cables"},
        {"product": "Copper Conductor XLPE Armoured Cable 4C x 16 sq mm", "category": "Copper Armoured Cables"},
        {"product": "Copper Armoured Cable 3 Core 35 sq mm", "category": "Copper Armoured Cables"},
        {"product": "Aluminium XLPE Armoured Cable 4C x 50 sq mm", "category": "Aluminium Armoured Cables"},
        {"product": "Aluminium Power Cable 3.5 Core 120 sq mm", "category": "Aluminium Armoured Cables"},
        {"product": "Thermocouple Extension Cable KX Type", "category": "Thermocouple Cables"},
        {"product": "Compensating Cable J Type Shielded", "category": "Thermocouple Cables"},
        {"product": "Wind Power Energy Cable 3C x 150 sq mm", "category": "Wind Power Cables"},
        {"product": "Triple Coated Multistrand House Wire 1.5 sq mm", "category": "Triple Coating Cables"},
    ]
    
    names = [
        "Rajesh Kumar", "Amit Sharma", "Sanjay Gupta", "Priya Patel", "Vikram Singh",
        "Sunita Rao", "Deepak Mehta", "Anil Joshi", "Rahul Verma", "Sneha Reddy",
        "Arjun Nair", "Manish Pandey", "Vijay Chawla", "Karan Malhotra", "Neha Gupta",
        "Rohan Sobti", "Suresh Iyer", "Divya Deshmukh", "Abhishek Tiwari", "Pooja Hegde",
        "Nitin Saxena", "Anjali Desai", "Rakesh Mishra", "Shweta Kapoor", "Harish Patel",
        "Gaurav Sen", "Meera Krishnan", "Varun Dhawan", "Kiran Mazumdar", "Aditya Birla",
        "Sandip Bose", "Kunal Kamra", "Rohit Shetty", "Ajay Devgn", "Siddharth Malhotra",
        "Shraddha Kapoor", "Alia Bhatt", "Ranbir Kapoor", "Deepika Padukone", "Ranveer Singh",
        "Pankaj Tripathi", "Manoj Bajpayee", "Nawazuddin Siddiqui", "Rajkummar Rao", "Ayushmann Khurrana",
        "Vicky Kaushal", "Katrina Kaif", "Priyanka Chopra", "Nick Jonas", "Mahendra Singh Dhoni",
        "Virat Kohli", "Sachin Tendulkar", "Rohit Sharma", "Jasprit Bumrah", "Hardik Pandya",
        "Rishabh Pant", "Ravindra Jadeja", "Shikhar Dhawan", "Cheteshwar Pujara"
    ]
    
    companies = [
        "Apex Builders", "L&T Construction", "Tata Power", "Adani Energy", "Reliance Infrastructure",
        "Siemens India", "Anchor Electricals", "Havells Distributor", "Sterling & Wilson", "Voltas Ltd",
        "Bajaj Electricals", "KEC International", "Kalpataru Power", "Godrej Properties", "DLF Limited",
        "Individual Contractor", "Local Retailer", "Electro Controls", "Power Grid Corp", "ABB India",
        "GMR Infrastructure", "Shapoorji Pallonji", "JMC Projects", "NCC Limited", "Dilip Buildcon",
        "Hindustan Construction", "Larsen & Toubro", "Tata Projects", "Engineers India", "BHEL"
    ]
    
    locations = [
        "Mumbai", "Delhi NCR", "Bangalore", "Chennai", "Hyderabad",
        "Pune", "Ahmedabad", "Kolkata", "Noida Sector 62", "Gurgaon Phase 3",
        "Jaipur", "Lucknow", "Coimbatore", "Surat", "Bhopal",
        "Visakhapatnam", "Chandigarh", "Patna", "Indore", "Bhubaneswar",
        "Nagpur", "Vadodara", "Thane", "Kochi", "Nashik",
        "Faridabad", "Ghaziabad", "Rajkot", "Amritsar", "Jabalpur"
    ]
    
    statuses = (
        ["New"] * 15 +
        ["Contacted"] * 12 +
        ["Quoted"] * 10 +
        ["Won"] * 8 +
        ["Lost"] * 6 +
        ["Partial"] * 8
    )
    
    for i in range(59):
        name = names[i % len(names)]
        company = companies[(i * 3) % len(companies)]
        location = locations[(i * 7) % len(locations)]
        prod_info = product_pool[i % len(product_pool)]
        status = statuses[i]
        
        # Override status if it exists
        lead_id = 1000 + i
        if lead_id in DUMMY_STATUS_OVERRIDES:
            status = DUMMY_STATUS_OVERRIDES[lead_id]
            
        phone = f"9198765{i:03d}"
        
        qty_val = (i % 5 + 1) * 50
        qty_unit = "coils" if "wire" in prod_info["product"].lower() else "meters"
        quantity = f"{qty_val} {qty_unit}"
        
        requirements = f"Demo Lead {i+1}. Inquired for {prod_info['product']} ({quantity}) for site delivery at {location}."
        
        created_dt = datetime.utcnow() - timedelta(days=(59 - i) * 0.25)
        created_at = created_dt.isoformat() + "Z"
        updated_at = (created_dt + timedelta(hours=2)).isoformat() + "Z"
        
        leads.append({
            "id": lead_id,
            "phone": phone,
            "name": name,
            "company": company,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "location": location,
            "product_interest": prod_info["product"],
            "quantity": quantity,
            "requirements": requirements,
            "status": status,
            "created_at": created_at,
            "updated_at": updated_at
        })
    return leads

def get_static_dummy_products():
    return [
        {
            "name": "KDI 1.5 sq mm FR House Wire (Copper)",
            "category": "House Wires",
            "conductor": "Copper",
            "size": "1.5 sq mm",
            "core": 1,
            "insulation": "PVC",
            "price_per_meter": 24.50,
            "stock_status": "In Stock",
            "specifications": "Flame Retardant, Lead Free"
        },
        {
            "name": "KDI 2.5 sq mm FRLS House Wire",
            "category": "House Wires",
            "conductor": "Copper",
            "size": "2.5 sq mm",
            "core": 1,
            "insulation": "FRLS PVC",
            "price_per_meter": 42.00,
            "stock_status": "In Stock",
            "specifications": "Flame Retardant Low Smoke"
        },
        {
            "name": "KDI Solar Cable 4 sq mm DC",
            "category": "Solar Cables",
            "conductor": "Copper",
            "size": "4.0 sq mm",
            "core": 1,
            "insulation": "XLPE",
            "price_per_meter": 55.00,
            "stock_status": "In Stock",
            "specifications": "UV Resistant, DC Solar Application"
        },
        {
            "name": "KDI Solar Cable 6 sq mm UV Resistant",
            "category": "Solar Cables",
            "conductor": "Copper",
            "size": "6.0 sq mm",
            "core": 1,
            "insulation": "XLPE",
            "price_per_meter": 82.50,
            "stock_status": "In Stock",
            "specifications": "TUV certified, UV Resistant"
        },
        {
            "name": "KDI Submersible Cable 3 Core 2.5 sq mm",
            "category": "Submersible Cables",
            "conductor": "Copper",
            "size": "2.5 sq mm",
            "core": 3,
            "insulation": "PVC",
            "price_per_meter": 115.00,
            "stock_status": "In Stock",
            "specifications": "Flat pump cable"
        },
        {
            "name": "KDI 3 Core Flat Submersible Cable 4 sq mm",
            "category": "Submersible Cables",
            "conductor": "Copper",
            "size": "4.0 sq mm",
            "core": 3,
            "insulation": "PVC",
            "price_per_meter": 168.00,
            "stock_status": "In Stock",
            "specifications": "Heavy duty flat pump cable"
        },
        {
            "name": "Copper Control Cable 4 Core 1.5 sq mm",
            "category": "Control Cables",
            "conductor": "Copper",
            "size": "1.5 sq mm",
            "core": 4,
            "insulation": "PVC",
            "price_per_meter": 95.00,
            "stock_status": "In Stock",
            "specifications": "Industrial control applications"
        },
        {
            "name": "Copper Control Cable 10 Core 2.5 sq mm",
            "category": "Control Cables",
            "conductor": "Copper",
            "size": "2.5 sq mm",
            "core": 10,
            "insulation": "PVC",
            "price_per_meter": 280.00,
            "stock_status": "Custom Only",
            "specifications": "Multi-core industrial signal cable"
        },
        {
            "name": "Copper Flexible Cable 3 Core 1.5 sq mm",
            "category": "Flexible Cables",
            "conductor": "Copper",
            "size": "1.5 sq mm",
            "core": 3,
            "insulation": "PVC",
            "price_per_meter": 72.00,
            "stock_status": "In Stock",
            "specifications": "Multistrand flexible cord"
        },
        {
            "name": "Flexible PVC Insulated Cord Cable 2 Core",
            "category": "Flexible Cables",
            "conductor": "Copper",
            "size": "1.0 sq mm",
            "core": 2,
            "insulation": "PVC",
            "price_per_meter": 38.00,
            "stock_status": "In Stock",
            "specifications": "Light duty twin flat cord"
        },
        {
            "name": "11kV HT Armoured Cable 3C x 95 sq mm",
            "category": "HT Cables",
            "conductor": "Aluminium",
            "size": "95 sq mm",
            "core": 3,
            "insulation": "XLPE",
            "price_per_meter": 1250.00,
            "stock_status": "Custom Only",
            "specifications": "11kV high voltage power distribution"
        },
        {
            "name": "33kV HT Armoured Cable XLPE",
            "category": "HT Cables",
            "conductor": "Aluminium",
            "size": "240 sq mm",
            "core": 3,
            "insulation": "XLPE",
            "price_per_meter": 3450.00,
            "stock_status": "Custom Only",
            "specifications": "33kV HT power transmission"
        },
        {
            "name": "Copper Conductor XLPE Armoured Cable 4C x 16 sq mm",
            "category": "Copper Armoured Cables",
            "conductor": "Copper",
            "size": "16 sq mm",
            "core": 4,
            "insulation": "XLPE",
            "price_per_meter": 890.00,
            "stock_status": "In Stock",
            "specifications": "Low voltage copper armoured"
        },
        {
            "name": "Aluminium XLPE Armoured Cable 4C x 50 sq mm",
            "category": "Aluminium Armoured Cables",
            "conductor": "Aluminium",
            "size": "50 sq mm",
            "core": 4,
            "insulation": "XLPE",
            "price_per_meter": 320.00,
            "stock_status": "In Stock",
            "specifications": "Low voltage aluminium armoured"
        },
        {
            "name": "Thermocouple Extension Cable KX Type",
            "category": "Thermocouple Cables",
            "conductor": "Chromel/Alumel",
            "size": "1.5 sq mm",
            "core": 2,
            "insulation": "PVC",
            "price_per_meter": 145.00,
            "stock_status": "In Stock",
            "specifications": "KX Type extension wire"
        },
        {
            "name": "Wind Power Energy Cable 3C x 150 sq mm",
            "category": "Wind Power Cables",
            "conductor": "Copper",
            "size": "150 sq mm",
            "core": 3,
            "insulation": "EPR",
            "price_per_meter": 4200.00,
            "stock_status": "Custom Only",
            "specifications": "Flexible torsion-resistant wind cable"
        },
        {
            "name": "Triple Coated Multistrand House Wire 1.5 sq mm",
            "category": "Triple Coating Cables",
            "conductor": "Copper",
            "size": "1.5 sq mm",
            "core": 1,
            "insulation": "Triple Layer PVC",
            "price_per_meter": 28.50,
            "stock_status": "In Stock",
            "specifications": "Extra safety triple sheath"
        }
    ]

def is_dummy_phone(phone):
    if not phone:
        return False
    cleaned = phone.replace("+", "").strip()
    return cleaned.startswith("9198765") and len(cleaned) == 10

def get_dummy_chat_history(phone):
    cleaned = phone.replace("+", "").strip()
    try:
        idx = int(cleaned[-3:])
    except Exception:
        idx = 0
        
    dummies = get_static_dummy_leads()
    lead = dummies[idx] if idx < len(dummies) else dummies[0]
    
    name = lead["name"]
    product = lead["product_interest"]
    qty = lead["quantity"]
    loc = lead["location"]
    status = lead["status"]
    
    history = []
    base_time = datetime.fromisoformat(lead["created_at"].replace("Z", ""))
    
    history.append({
        "phone": phone,
        "direction": "inbound",
        "body": "Hello, I am interested in purchasing some cables.",
        "created_at": base_time.isoformat() + "Z"
    })
    
    history.append({
        "phone": phone,
        "direction": "outbound",
        "body": f"Hello {name}! 👋\nWelcome to *KDI Power*!\nI would be happy to help you with your query. Could you please specify which cable/wire you are looking for?",
        "created_at": (base_time + timedelta(minutes=1)).isoformat() + "Z"
    })
    
    history.append({
        "phone": phone,
        "direction": "inbound",
        "body": f"I need {product}.",
        "created_at": (base_time + timedelta(minutes=2)).isoformat() + "Z"
    })
    
    history.append({
        "phone": phone,
        "direction": "outbound",
        "body": f"Got it! What quantity of *{product}* do you require?",
        "created_at": (base_time + timedelta(minutes=3)).isoformat() + "Z"
    })
    
    history.append({
        "phone": phone,
        "direction": "inbound",
        "body": f"We require around {qty}.",
        "created_at": (base_time + timedelta(minutes=4)).isoformat() + "Z"
    })
    
    history.append({
        "phone": phone,
        "direction": "outbound",
        "body": "Understood. Please share your delivery location and company name if applicable.",
        "created_at": (base_time + timedelta(minutes=5)).isoformat() + "Z"
    })
    
    if status == "Partial":
        return history
        
    history.append({
        "phone": phone,
        "direction": "inbound",
        "body": f"Delivery is at {loc}. Company name is {lead['company']}.",
        "created_at": (base_time + timedelta(minutes=6)).isoformat() + "Z"
    })
    
    history.append({
        "phone": phone,
        "direction": "outbound",
        "body": f"Thank you for the details, {name}. Your inquiry has been logged successfully with ID #{lead['id']}.\n\nOur sales representative will reach out to you shortly to provide the quote.",
        "created_at": (base_time + timedelta(minutes=7)).isoformat() + "Z"
    })
    
    if status == "New":
        return history
        
    history.append({
        "phone": phone,
        "direction": "outbound",
        "body": "📞 *Sales Representative Update*\nOur sales team has reviewed your inquiry and is preparing your quotation.",
        "created_at": (base_time + timedelta(hours=1)).isoformat() + "Z"
    })
    
    if status == "Contacted":
        return history
        
    history.append({
        "phone": phone,
        "direction": "outbound",
        "body": f"📄 *Quotation Sent*\nWe have emailed the quotation to {lead['email']}.\n\n*Summary:*\nProduct: {product}\nQuantity: {qty}\nPrice: Special Project Pricing applied.",
        "created_at": (base_time + timedelta(hours=2)).isoformat() + "Z"
    })
    
    if status == "Quoted":
        return history
        
    if status == "Won":
        history.append({
            "phone": phone,
            "direction": "inbound",
            "body": "Thank you, we accept the quote and have processed the purchase order.",
            "created_at": (base_time + timedelta(hours=3)).isoformat() + "Z"
        })
        history.append({
            "phone": phone,
            "direction": "outbound",
            "body": "🎉 *Deal Closed!*\nPayment received. Dispatch is being scheduled. Thank you for doing business with KDI Power!",
            "created_at": (base_time + timedelta(hours=3, minutes=10)).isoformat() + "Z"
        })
        return history
        
    if status == "Lost":
        history.append({
            "phone": phone,
            "direction": "inbound",
            "body": "Sorry, we have selected another vendor with a lower price.",
            "created_at": (base_time + timedelta(hours=4)).isoformat() + "Z"
        })
        history.append({
            "phone": phone,
            "direction": "outbound",
            "body": "Thank you for the update. We hope to work with you on future projects.",
            "created_at": (base_time + timedelta(hours=4, minutes=5)).isoformat() + "Z"
        })
        return history
        
    return history

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

def upsert_lead_from_chat(phone, profile_name, lead_data, status):
    existing = get_lead_by_phone(phone)
    
    if existing and existing.get("status") in ["New", "Partial"]:
        data = {
            "name": lead_data.get("name", existing.get("name", profile_name))[:200],
            "company": lead_data.get("company", existing.get("company", "Unknown"))[:200],
            "location": lead_data.get("location", existing.get("location", "Unknown"))[:200],
            "product_interest": lead_data.get("product", existing.get("product_interest", "Unknown"))[:200],
            "quantity": lead_data.get("quantity", existing.get("quantity", "Unknown"))[:100],
            "status": status,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        request_supabase("leads", "PATCH", data=data, params={"id": f"eq.{existing['id']}"})
        return existing["id"]
    else:
        data = {
            "phone": phone,
            "name": lead_data.get("name", profile_name)[:200],
            "company": lead_data.get("company", "Unknown")[:200],
            "email": "",
            "location": lead_data.get("location", "Unknown")[:200],
            "product_interest": lead_data.get("product", "Unknown")[:200],
            "quantity": lead_data.get("quantity", "Unknown")[:100],
            "requirements": "Captured via AI chatbot.",
            "status": status,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        res = request_supabase("leads", "POST", data=data)
        if res:
            return res[0]["id"]
        return None

def get_leads(status_filter=None, search_query=None):
    real_leads = request_supabase("leads", "GET", params={"order": "created_at.desc"})
    if not real_leads:
        real_leads = []
        
    num_dummies = max(0, 59 - len(real_leads))
    dummy_leads = get_static_dummy_leads()[:num_dummies]
    
    combined = real_leads + dummy_leads
    combined.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    if status_filter:
        combined = [l for l in combined if l.get("status") == status_filter]
        
    if search_query:
        q = search_query.lower()
        combined = [
            l for l in combined if (
                q in (l.get("name") or "").lower() or
                q in (l.get("phone") or "").lower() or
                q in (l.get("company") or "").lower() or
                q in (l.get("requirements") or "").lower() or
                q in (l.get("product_interest") or "").lower() or
                q in (l.get("location") or "").lower()
            )
        ]
    return combined

def update_lead_status(lead_id, status):
    if lead_id >= 1000:
        DUMMY_STATUS_OVERRIDES[lead_id] = status
        return
        
    data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }
    request_supabase("leads", "PATCH", data=data, params={"id": f"eq.{lead_id}"})

def get_lead_by_phone(phone):
    if is_dummy_phone(phone):
        cleaned = phone.replace("+", "").strip()
        try:
            idx = int(cleaned[-3:])
        except Exception:
            idx = 0
        dummies = get_static_dummy_leads()
        return dummies[idx] if idx < len(dummies) else dummies[0]

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
    
    products = request_supabase("products", "GET", params=params)
    if not products:
        dummy_products = get_static_dummy_products()
        # Apply in-memory overrides
        for dp in dummy_products:
            name = dp["name"]
            if name in DUMMY_PRODUCT_OVERRIDES:
                overrides = DUMMY_PRODUCT_OVERRIDES[name]
                if "price" in overrides:
                    dp["price_per_meter"] = overrides["price"]
                if "stock_status" in overrides:
                    dp["stock_status"] = overrides["stock_status"]
        # Apply category filter
        if category_filter:
            dummy_products = [p for p in dummy_products if p["category"] == category_filter]
        return dummy_products
    return products

def get_product_by_id(product_name):
    res = request_supabase("products", "GET", params={"name": f"eq.{product_name}"})
    if not res:
        dummy_products = get_static_dummy_products()
        matches = [p for p in dummy_products if p["name"] == product_name]
        if matches:
            dp = matches[0]
            if product_name in DUMMY_PRODUCT_OVERRIDES:
                overrides = DUMMY_PRODUCT_OVERRIDES[product_name]
                if "price" in overrides:
                    dp["price_per_meter"] = overrides["price"]
                if "stock_status" in overrides:
                    dp["stock_status"] = overrides["stock_status"]
            return dp
        return None
    return res[0] if res else None

def update_product_price_and_stock(product_name, price, stock_status):
    # Store in-memory override
    DUMMY_PRODUCT_OVERRIDES[product_name] = {
        "price": price,
        "stock_status": stock_status
    }
    
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

def get_chat_history(phone, limit=30):
    if is_dummy_phone(phone):
        res = get_dummy_chat_history(phone)
        for row in res:
            row["timestamp"] = row["created_at"]
        return res

    params = {
        "phone": f"eq.{phone}",
        "order": "created_at.desc",
        "limit": str(limit)
    }
    res = request_supabase("chat_history", "GET", params=params)
    # Reverse to get chronological order (oldest first)
    res = list(reversed(res))
    for row in res:
        row["timestamp"] = row["created_at"]
    return res
