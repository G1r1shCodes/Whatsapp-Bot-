from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import db
import ai
import re
import json

router = APIRouter()

class TestChatMessage(BaseModel):
    phone: str
    message: str
    profile_name: str = "Tester"

@router.get("/dashboard")
async def get_dashboard():
    return FileResponse("templates/dashboard.html")

@router.get("/test-chat")
async def get_test_chat():
    return FileResponse("templates/test_chat.html")

@router.post("/api/test-chat")
async def api_test_chat(msg: TestChatMessage):
    """Bypasses Meta API and interacts directly with AI for testing."""
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
            lead_id = db.create_lead(
                phone=msg.phone,
                name=lead_data.get("name", "Unknown"),
                company=lead_data.get("company", "Individual"),
                email="",
                location=lead_data.get("location", "Unknown"),
                product_interest=lead_data.get("product", "Unknown"),
                quantity=lead_data.get("quantity", "Unknown"),
                requirements=f"Captured via AI chatbot. Qty: {lead_data.get('quantity')}. Loc: {lead_data.get('location')}."
            )
            cleaned_text = re.sub(r'\[LEAD_SUBMIT:\s*\{.*?\}\s*\]', '', ai_response, flags=re.DOTALL).strip()
            success_msg = f"🎉 *Inquiry Submitted Successfully!*\n\n🔹 *Inquiry ID:* #{lead_id}"
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
    db.log_chat_message(msg.phone, "outbound", reply_text)
    
    return {"reply": reply_text, "image": image_file}

@router.get("/api/leads")
async def get_leads_api(status: str = None, search: str = None):
    return db.get_leads(status_filter=status, search_query=search)

@router.patch("/api/leads/{lead_id}/status")
async def update_lead_status_api(lead_id: int, request: Request):
    payload = await request.json()
    status = payload.get("status")
    db.update_lead_status(lead_id, status)
    return {"success": True, "lead_id": lead_id, "status": status}

@router.get("/api/leads/{phone}/history")
async def get_lead_history_api(phone: str):
    return db.get_chat_history(phone)

@router.get("/api/dashboard/stats")
async def get_stats_api():
    leads = db.get_leads()
    
    total_leads = len(leads)
    new_leads = sum(1 for l in leads if l.get("status") == "New")
    quoted_leads = sum(1 for l in leads if l.get("status") == "Quoted")
    won_leads = sum(1 for l in leads if l.get("status") == "Won")
    
    # Category / Product interest distribution for charts
    categories = {}
    for l in leads:
        prod = l.get("product_interest")
        if not prod:
            continue
        # Extract general category or use the product interest itself
        cat = "Custom Inquiry"
        if "FR" in prod or "wire" in prod.lower() or "house" in prod.lower():
            cat = "House Wires"
        elif "armoured" in prod.lower() or "power" in prod.lower() or "xlpe" in prod.lower():
            cat = "Power Cables"
        elif "submersible" in prod.lower() or "sub" in prod.lower():
            cat = "Submersible Cables"
        elif "control" in prod.lower():
            cat = "Control Cables"
        
        categories[cat] = categories.get(cat, 0) + 1
        
    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "quoted_leads": quoted_leads,
        "won_leads": won_leads,
        "category_distribution": categories
    }

@router.get("/api/products")
async def get_products_api():
    return db.get_all_products()

@router.patch("/api/products/{product_name}")
async def update_product_api(product_name: str, request: Request):
    payload = await request.json()
    price = payload.get("price")
    stock_status = payload.get("stock_status")
    db.update_product_price_and_stock(product_name, price, stock_status)
    return {"success": True, "product": product_name}
