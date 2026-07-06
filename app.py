from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
import db
import ai
import re
import json

# Initialize Database on Startup
db.init_db()

app = FastAPI(title="KDI Power AI WhatsApp Assistant")

class WhatsAppMessage(BaseModel):
    From: str
    Body: str
    ProfileName: str = "Sir/Mam"

@app.post("/whatsapp")
async def whatsapp(msg: WhatsAppMessage):
    # Node.js whatsapp-web.js fields
    from_number = msg.From.replace("@c.us", "").strip()
    incoming_msg = msg.Body.strip()
    profile_name = msg.ProfileName.strip()
    if not profile_name or profile_name.lower() in ["customer", "unknown", "guest", "someone"]:
        profile_name = "Sir/Mam"
    
    if not from_number or not incoming_msg:
        return Response(content="Missing sender or body", status_code=400)
    
    # Log incoming message
    db.log_chat_message(from_number, "inbound", incoming_msg)
    
    # Get response from Groq AI
    ai_response = ai.get_ai_response(from_number, profile_name)
    
    # Parse responses for special command tags
    reply_text = ai_response
    
    # Check for LEAD_SUBMIT tag: [LEAD_SUBMIT: {"name": "...", "company": "...", "product": "...", "quantity": "...", "location": "..."}]
    submit_match = re.search(r'\[LEAD_SUBMIT:\s*(\{.*?\})\s*\]', ai_response, re.DOTALL)
    status_match = "[LEAD_STATUS_CHECK]" in ai_response
    
    image_match = re.search(r'\[IMAGE:\s*(.+?)\s*\]', ai_response)
    image_file = None
    if image_match:
        image_file = image_match.group(1).strip()
        reply_text = re.sub(r'\[IMAGE:\s*.+?\s*\]', '', reply_text).strip()

    
    if submit_match:
        try:
            lead_data = json.loads(submit_match.group(1))
            lead_id = db.create_lead(
                phone=from_number,
                name=lead_data.get("name", "Unknown"),
                company=lead_data.get("company", "Individual"),
                email="",
                location=lead_data.get("location", "Unknown"),
                product_interest=lead_data.get("product", "Unknown"),
                quantity=lead_data.get("quantity", "Unknown"),
                requirements=f"Captured via AI chatbot. Qty: {lead_data.get('quantity')}. Loc: {lead_data.get('location')}."
            )
            
            # Remove the tag and build confirmation text
            cleaned_text = re.sub(r'\[LEAD_SUBMIT:\s*\{.*?\}\s*\]', '', ai_response, flags=re.DOTALL).strip()
            success_msg = (
                f"🎉 *Inquiry Submitted Successfully!*\n\n"
                f"🔹 *Inquiry ID:* #{lead_id}\n\n"
                f"Our sales representatives are reviewing your requirements and will reach out shortly."
            )
            if cleaned_text:
                reply_text = f"{cleaned_text}\n\n{success_msg}"
            else:
                reply_text = success_msg
                
        except Exception as e:
            print(f"Error parsing LEAD_SUBMIT tag: {e}")
            reply_text = "I encountered an error submitting your quote request. Please try again."
            
    elif status_match:
        # Check latest lead status
        lead = db.get_lead_by_phone(from_number)
        cleaned_text = ai_response.replace("[LEAD_STATUS_CHECK]", "").strip()
        
        if lead:
            status_emoji = {
                "New": "🆕",
                "Contacted": "📞",
                "Quoted": "💰",
                "Won": "🎉",
                "Lost": "❌"
            }.get(lead["status"], "ℹ️")
            
            status_msg = (
                f"📄 *Your Inquiry Status*\n\n"
                f"🔹 *Inquiry ID:* #{lead['id']}\n"
                f"🔹 *Product:* {lead['product_interest']}\n"
                f"🔹 *Quantity:* {lead['quantity']}\n"
                f"🔹 *Status:* {status_emoji} *{lead['status']}*\n"
                f"🔹 *Updated:* {lead['updated_at'][:16]}"
            )
        else:
            status_msg = "❌ No active inquiry found for your number. Feel free to request a quote by chatting with me!"
            
        if cleaned_text:
            reply_text = f"{cleaned_text}\n\n{status_msg}"
        else:
            reply_text = status_msg
            
    # Format markdown for WhatsApp (convert ** to *)
    reply_text = reply_text.replace("**", "*")
    
    # Log outbound response
    db.log_chat_message(from_number, "outbound", reply_text)
    
    # Send WhatsApp response via JSON back to Node.js bot
    response_payload = {"reply": reply_text}
    if image_file:
        response_payload["image"] = image_file
    return response_payload

# --- Dashboard API & Page Routes ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Create static directories if they don't exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/dashboard")
async def get_dashboard():
    return FileResponse("templates/dashboard.html")

@app.get("/api/leads")
async def get_leads_api(status: str = None, search: str = None):
    return db.get_leads(status_filter=status, search_query=search)

@app.patch("/api/leads/{lead_id}/status")
async def update_lead_status_api(lead_id: int, request: Request):
    payload = await request.json()
    status = payload.get("status")
    db.update_lead_status(lead_id, status)
    return {"success": True, "lead_id": lead_id, "status": status}

@app.get("/api/leads/{phone}/history")
async def get_lead_history_api(phone: str):
    return db.get_chat_history(phone)

@app.get("/api/dashboard/stats")
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

@app.get("/api/products")
async def get_products_api():
    return db.get_all_products()

@app.patch("/api/products/{product_name}")
async def update_product_api(product_name: str, request: Request):
    payload = await request.json()
    price = payload.get("price")
    stock_status = payload.get("stock_status")
    db.update_product_price_and_stock(product_name, price, stock_status)
    return {"success": True, "product": product_name}