from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
import db
import ai
import re
import json
import auth
import io
import csv
import config_manager

router = APIRouter()

class TestChatMessage(BaseModel):
    phone: str
    message: str
    profile_name: str = "Tester"

@router.get("/dashboard")
async def get_dashboard(request: Request):
    if not auth.verify_auth(request):
        return RedirectResponse(url="/login")
    return FileResponse("templates/dashboard.html")

@router.get("/test-chat")
async def get_test_chat(request: Request):
    if not auth.verify_auth(request):
        return RedirectResponse(url="/login")
    return FileResponse("templates/test_chat.html")

@router.post("/api/test-chat")
async def api_test_chat(msg: TestChatMessage, request: Request):
    """Bypasses Meta API and interacts directly with AI for testing."""
    auth.require_auth(request)
    incoming_msg = msg.message.strip()
    if not incoming_msg:
        return {"error": "Message is empty"}
        
    db.log_chat_message(msg.phone, "inbound", incoming_msg)
    
    ai_response = ai.get_ai_response(msg.phone, msg.profile_name)
    reply_text = ai_response
    image_file = None
    
    submit_match = re.search(r'\[LEAD_SUBMIT:\s*(\{.*?\})\s*\]', ai_response, re.DOTALL)
    status_match = "[LEAD_STATUS_CHECK]" in ai_response
    image_match = re.search(r'\[IMAGE:\s*(.+?)\s*\]', ai_response)
    
    if image_match:
        image_file = image_match.group(1).strip()
        reply_text = re.sub(r'\[IMAGE:\s*.+?\s*\]', '', reply_text).strip()

    if submit_match:
        try:
            lead_data = json.loads(submit_match.group(1))
            # Validate required fields
            if not lead_data.get("name") or not lead_data.get("product"):
                raise ValueError("Missing required lead fields: name and product")
            lead_id = db.create_lead(
                phone=msg.phone,
                name=lead_data.get("name", "Unknown")[:200],
                company=lead_data.get("company", "Individual")[:200],
                email="",
                location=lead_data.get("location", "Unknown")[:200],
                product_interest=lead_data.get("product", "Unknown")[:200],
                quantity=lead_data.get("quantity", "Unknown")[:100],
                requirements=f"Captured via AI chatbot. Qty: {lead_data.get('quantity')}. Loc: {lead_data.get('location')}."
            )
            cleaned_text = re.sub(r'\[LEAD_SUBMIT:\s*\{.*?\}\s*\]', '', ai_response, flags=re.DOTALL).strip()
            success_msg = "🎉 *Inquiry Submitted Successfully!*\n\nOur sales representatives are reviewing your requirements and will reach out shortly."
            reply_text = f"{cleaned_text}\n\n{success_msg}" if cleaned_text else success_msg
        except Exception:
            reply_text = "I encountered an error submitting your quote request. Please try again."
            
    elif status_match:
        lead = db.get_lead_by_phone(msg.phone)
        cleaned_text = ai_response.replace("[LEAD_STATUS_CHECK]", "").strip()
        if lead:
            reply_text = f"{cleaned_text}\n\n📄 *Inquiry #{lead['id']} Status:* {lead['status']}" if cleaned_text else f"📄 *Inquiry #{lead['id']} Status:* {lead['status']}"
        else:
            reply_text = f"{cleaned_text}\n\n❌ No active inquiry found." if cleaned_text else "❌ No active inquiry found."

    reply_text = reply_text.replace("**", "*")
    reply_text = re.sub(r'\n{3,}', '\n\n', reply_text).strip()
    db.log_chat_message(msg.phone, "outbound", reply_text)
    
    return {"reply": reply_text, "image": image_file}

@router.get("/api/leads")
async def get_leads_api(request: Request, status: str = None, search: str = None):
    auth.require_auth(request)
    return db.get_leads(status_filter=status, search_query=search)

@router.get("/api/leads/export")
async def export_leads_csv(request: Request):
    auth.require_auth(request)
    leads = db.get_leads()
    
    # Create an in-memory string buffer for the CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Lead ID", "Phone Number", "Name", "Company", "Location", 
        "Product Interest", "Quantity", "Status", "Created At", "Updated At"
    ])
    
    # Write data
    for lead in leads:
        writer.writerow([
            lead.get("id"),
            lead.get("phone_number"),
            lead.get("name"),
            lead.get("company"),
            lead.get("location"),
            lead.get("product_interest"),
            lead.get("quantity"),
            lead.get("status"),
            lead.get("created_at"),
            lead.get("updated_at")
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kdi_leads_export.csv"}
    )

@router.patch("/api/leads/{lead_id}/status")
async def update_lead_status_api(lead_id: int, request: Request):
    auth.require_auth(request)
    payload = await request.json()
    status = payload.get("status")
    ALLOWED_STATUSES = {"New", "Contacted", "Quoted", "Won", "Lost"}
    if status not in ALLOWED_STATUSES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {', '.join(ALLOWED_STATUSES)}")
    db.update_lead_status(lead_id, status)
    return {"success": True, "lead_id": lead_id, "status": status}

@router.get("/api/leads/{phone}/history")
async def get_lead_history_api(phone: str, request: Request):
    auth.require_auth(request)
    return db.get_chat_history(phone)

@router.get("/api/dashboard/stats")
async def get_stats_api(request: Request):
    auth.require_auth(request)
    leads = db.get_leads()
    
    total_leads = len(leads)
    new_leads = sum(1 for l in leads if l.get("status") == "New")
    contacted_leads = sum(1 for l in leads if l.get("status") == "Contacted")
    quoted_leads = sum(1 for l in leads if l.get("status") == "Quoted")
    won_leads = sum(1 for l in leads if l.get("status") == "Won")
    lost_leads = sum(1 for l in leads if l.get("status") == "Lost")
    
    # Category / Product interest distribution for charts
    categories = {}
    for l in leads:
        prod = l.get("product_interest")
        if not prod:
            continue
        prod_lower = prod.lower()
        if "solar" in prod_lower:
            cat = "Solar Cables"
        elif "submersible" in prod_lower or "sub " in prod_lower:
            cat = "Submersible Cables"
        elif "control" in prod_lower:
            cat = "Control Cables"
        elif "flexible" in prod_lower or "cord" in prod_lower:
            cat = "Flexible Cables"
        elif "ht cable" in prod_lower or "high tension" in prod_lower or "11kv" in prod_lower or "33kv" in prod_lower:
            cat = "HT Cables"
        elif "armoured" in prod_lower or "armored" in prod_lower:
            if "copper" in prod_lower:
                cat = "Copper Armoured Cables"
            elif "aluminium" in prod_lower or "aluminum" in prod_lower:
                cat = "Aluminium Armoured Cables"
            else:
                cat = "Armoured Cables"
        elif "unarmoured" in prod_lower or "unarmored" in prod_lower:
            if "copper" in prod_lower:
                cat = "Copper Unarmoured Cables"
            else:
                cat = "Aluminium Unarmoured Cables"
        elif "thermocouple" in prod_lower:
            cat = "Thermocouple Cables"
        elif "wind" in prod_lower:
            cat = "Wind Power Cables"
        elif "triple" in prod_lower:
            cat = "Triple Coating Cables"
        elif "house" in prod_lower or "fr" in prod_lower or "wire" in prod_lower:
            cat = "House Wires"
        else:
            cat = "Power Cables"
        
        categories[cat] = categories.get(cat, 0) + 1
        
    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "contacted_leads": contacted_leads,
        "quoted_leads": quoted_leads,
        "won_leads": won_leads,
        "lost_leads": lost_leads,
        "category_distribution": categories
    }

@router.get("/api/products")
async def get_products_api(request: Request):
    auth.require_auth(request)
    return db.get_all_products()

@router.patch("/api/products/{product_name}")
async def update_product_api(product_name: str, request: Request):
    auth.require_auth(request)
    payload = await request.json()
    price = payload.get("price")
    stock_status = payload.get("stock_status")
    if price is not None and (not isinstance(price, (int, float)) or price < 0):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Price must be a non-negative number.")
    db.update_product_price_and_stock(product_name, price, stock_status)
    return {"success": True, "product": product_name}

@router.get("/api/settings")
async def get_settings_api(request: Request):
    auth.require_auth(request)
    return config_manager.get_config()

@router.put("/api/settings")
async def update_settings_api(request: Request):
    auth.require_auth(request)
    payload = await request.json()
    success = config_manager.save_config(payload)
    if success:
        return {"success": True}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Failed to save configuration.")
