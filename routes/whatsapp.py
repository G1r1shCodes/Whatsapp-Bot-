import os
import json
import urllib.request
import re
from fastapi import APIRouter, Request, Response, HTTPException
import db
import ai
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "default_verify_token")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID")

def send_whatsapp_message(to_phone: str, text: str, image_url: str = None):
    """Sends a message to the user via Meta Cloud API."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        logger.error("Missing Meta API credentials in environment variables.")
        return
        
    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone
    }
    
    if image_url:
        payload["type"] = "image"
        payload["image"] = {
            "link": image_url,
            "caption": text
        }
    else:
        payload["type"] = "text"
        payload["text"] = {
            "preview_url": False,
            "body": text
        }
        
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            logger.info(f"Meta API Response: {res_data}")
    except Exception as e:
        logger.error(f"Error sending Meta API message: {e}")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Handles Meta Webhook Verification Challenge."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("Webhook verified successfully!")
            return Response(content=challenge, status_code=200)
        else:
            raise HTTPException(status_code=403, detail="Verification token mismatch")
    
    return Response(content="Hello from Webhook", status_code=200)

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Handles incoming WhatsApp messages from Meta API."""
    try:
        body = await request.json()
        
        if body.get("object") != "whatsapp_business_account":
            return Response(status_code=404)
            
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # We only process if it contains messages
                if "messages" in value and value["messages"]:
                    msg = value["messages"][0]
                    from_number = msg.get("from")
                    msg_type = msg.get("type")
                    
                    contacts = value.get("contacts", [])
                    profile_name = contacts[0].get("profile", {}).get("name", "Sir/Mam") if contacts else "Sir/Mam"
                    
                    # For now we only handle text
                    if msg_type != "text":
                        continue
                        
                    incoming_msg = msg.get("text", {}).get("body", "").strip()
                    
                    if not incoming_msg:
                        continue
                        
                    # Process Message
                    db.log_chat_message(from_number, "inbound", incoming_msg)
                    
                    # Get response from Groq AI
                    ai_response = ai.get_ai_response(from_number, profile_name)
                    
                    reply_text = ai_response
                    image_file = None
                    
                    # Parse specific tags
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
                                phone=from_number,
                                name=lead_data.get("name", "Unknown")[:200],
                                company=lead_data.get("company", "Individual")[:200],
                                email="",
                                location=lead_data.get("location", "Unknown")[:200],
                                product_interest=lead_data.get("product", "Unknown")[:200],
                                quantity=lead_data.get("quantity", "Unknown")[:100],
                                requirements=f"Captured via AI chatbot. Qty: {lead_data.get('quantity')}. Loc: {lead_data.get('location')}."
                            )
                            cleaned_text = re.sub(r'\[LEAD_SUBMIT:\s*\{.*?\}\s*\]', '', ai_response, flags=re.DOTALL).strip()
                            success_msg = f"🎉 *Inquiry Submitted Successfully!*\n\n🔹 *Inquiry ID:* #{lead_id}\n\nOur sales representatives are reviewing your requirements and will reach out shortly."
                            reply_text = f"{cleaned_text}\n\n{success_msg}" if cleaned_text else success_msg
                        except Exception as e:
                            logger.error(f"Error parsing LEAD_SUBMIT tag: {e}")
                            reply_text = "I encountered an error submitting your quote request. Please try again."
                            
                    elif status_match:
                        lead = db.get_lead_by_phone(from_number)
                        cleaned_text = ai_response.replace("[LEAD_STATUS_CHECK]", "").strip()
                        if lead:
                            status_emoji = {"New": "🆕", "Contacted": "📞", "Quoted": "💰", "Won": "🎉", "Lost": "❌"}.get(lead["status"], "ℹ️")
                            status_msg = f"📄 *Your Inquiry Status*\n\n🔹 *Inquiry ID:* #{lead['id']}\n🔹 *Product:* {lead['product_interest']}\n🔹 *Quantity:* {lead['quantity']}\n🔹 *Status:* {status_emoji} *{lead['status']}*\n🔹 *Updated:* {lead['updated_at'][:16]}"
                        else:
                            status_msg = "❌ No active inquiry found for your number. Feel free to request a quote by chatting with me!"
                        reply_text = f"{cleaned_text}\n\n{status_msg}" if cleaned_text else status_msg

                    reply_text = reply_text.replace("**", "*")
                    reply_text = re.sub(r'\n{3,}', '\n\n', reply_text).strip()
                    db.log_chat_message(from_number, "outbound", reply_text)
                    
                    # Send image to Meta API if one was requested
                    image_url = None
                    if image_file:
                        image_url = f"https://whatsapp-bot-m3u1.onrender.com/static/images/{image_file}"
                        
                    send_whatsapp_message(from_number, reply_text, image_url=image_url)
                    
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)
