import os
import json
import re
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
import db
import ai
import httpx
from logger import get_logger

http_client = httpx.Client(timeout=10.0)

logger = get_logger(__name__)

router = APIRouter()

META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "default_verify_token")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID")

def send_whatsapp_message(to_phone: str, text: str, image_url: str = None, show_menu: bool = False, show_categories_menu: bool = False, show_call_cta: bool = False):
    """Sends a message to the user via Meta Cloud API."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        logger.error("Missing Meta API credentials in environment variables.")
        return
        
    url = f"https://graph.facebook.com/v21.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Send Image if present (but NOT if we are showing the main menu, since it will be embedded)
    if image_url and not show_menu:
        payload_img = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "image",
            "image": {
                "link": image_url
            }
        }
        # If no menu follows, put the text in the caption
        if not show_categories_menu and text:
            payload_img["image"]["caption"] = text
            
        try:
            response = http_client.post(url, json=payload_img, headers=headers)
            response.raise_for_status()
            logger.info("Sent image successfully")
        except Exception as e:
            logger.error(f"Error sending Meta image: {e}")

    # 2. Send Main Menu if requested
    if show_menu:
        payload_menu = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": text if text else "How can we assist you today?"
                },
                "footer": {
                    "text": "Please choose an option below:"
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": "menu_browse",
                                "title": "Browse Products"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "menu_quote",
                                "title": "Request a Quote"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": "menu_contact",
                                "title": "Call Us"
                            }
                        }
                    ]
                }
            }
        }
        
        # Embed the image directly into the menu header
        if image_url:
            payload_menu["interactive"]["header"] = {
                "type": "image",
                "image": {
                    "link": image_url
                }
            }
            
        try:
            response = http_client.post(url, json=payload_menu, headers=headers)
            response.raise_for_status()
            logger.info("Sent menu successfully")
        except httpx.HTTPStatusError as he:
            logger.error(f"Error sending Meta menu (HTTP {he.response.status_code}): {he.response.text}")
        except Exception as e:
            logger.error(f"Error sending Meta menu: {e}")

    # 3. Send Categories Menu if requested
    if show_categories_menu:
        payload_cat = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": "KDI Products"
                },
                "body": {
                    "text": text if text else "Browse our product categories:"
                },
                "footer": {
                    "text": "Tap the button below"
                },
                "action": {
                    "button": "Categories",
                    "sections": [
                        {
                            "title": "Select a Category",
                            "rows": [
                                {"id": "cat_power", "title": "Power Cables"},
                                {"id": "cat_wires", "title": "Electrical Wires"},
                                {"id": "cat_armour", "title": "Armoured Cables"},
                                {"id": "cat_unarmour", "title": "Unarmoured Cables"},
                                {"id": "cat_control", "title": "Control Cables"}
                            ]
                        }
                    ]
                }
            }
        }
        try:
            response = http_client.post(url, json=payload_cat, headers=headers)
            response.raise_for_status()
            logger.info("Sent categories menu successfully")
        except httpx.HTTPStatusError as he:
            logger.error(f"Error sending Meta cat menu (HTTP {he.response.status_code}): {he.response.text}")
        except Exception as e:
            logger.error(f"Error sending Meta cat menu: {e}")
            


    # 5. If neither, just send text
    if not image_url and not show_menu and not show_categories_menu and not show_call_cta and text:
        payload_text = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }
        try:
            response = http_client.post(url, json=payload_text, headers=headers)
            response.raise_for_status()
            logger.info("Sent text successfully")
        except httpx.HTTPStatusError as he:
            logger.error(f"Error sending Meta text (HTTP {he.response.status_code}): {he.response.text}")
        except Exception as e:
            logger.error(f"Error sending Meta text: {e}")

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

def process_incoming_message(from_number: str, incoming_msg: str, profile_name: str):
    """Processes the message in the background to avoid Meta webhook timeouts."""
    try:
        # Process Message
        db.log_chat_message(from_number, "inbound", incoming_msg)
        
        # Intercept static buttons to save API calls
        lower_msg = incoming_msg.lower()
        image_file = None
        menu_match = False
        cat_match = False
        call_match = False
        
        if lower_msg in ["contact sales", "call us"]:
            reply_text = "📞 *Sales & Support*\nTap the number below to call us directly:\n\n*+91-9205333843*\n👤 Vipul Kumar — Marketing Manager\n\n📍 *Factory Address*\nH-1243, DSIDC Industrial Area, Narela, New Delhi"
            call_match = False
        elif lower_msg == "track my inquiry":
            lead = db.get_lead_by_phone(from_number)
            if lead:
                status_emoji = {"New": "🆕", "Contacted": "📞", "Quoted": "💰", "Won": "🎉", "Lost": "❌"}.get(lead["status"], "ℹ️")
                reply_text = f"📄 *Your Inquiry Status*\n\n🔹 *Inquiry ID:* #{lead['id']}\n🔹 *Product:* {lead['product_interest']}\n🔹 *Quantity:* {lead['quantity']}\n🔹 *Status:* {status_emoji} *{lead['status']}*\n🔹 *Updated:* {lead['updated_at'][:16]}"
            else:
                reply_text = "❌ No active inquiry found for your number. Feel free to request a quote by chatting with me!"
        elif lower_msg == "browse products":
            reply_text = ""
            cat_match = True
        elif lower_msg in ["main menu", "menu"]:
            reply_text = ""
            menu_match = True
        else:
            # Get response from Groq AI
            ai_response = ai.get_ai_response(from_number, profile_name)
            
            reply_text = ai_response
            
            # Parse specific tags
            submit_match = re.search(r'\[LEAD_SUBMIT:\s*(\{.*?\})\s*\]', ai_response, re.DOTALL)
            partial_match = re.search(r'\[LEAD_PARTIAL:\s*(\{.*?\})\s*\]', ai_response, re.DOTALL)
            status_match = "[LEAD_STATUS_CHECK]" in ai_response
            menu_match = "[SHOW_MAIN_MENU]" in ai_response
            image_match = re.search(r'\[IMAGE:\s*(.+?)\s*\]', ai_response)
            
            if menu_match:
                reply_text = reply_text.replace("[SHOW_MAIN_MENU]", "").strip()
                
            if image_match:
                image_file = image_match.group(1).strip()
                reply_text = re.sub(r'\[IMAGE:\s*.+?\s*\]', '', reply_text).strip()

            if partial_match:
                try:
                    lead_data = json.loads(partial_match.group(1))
                    db.upsert_lead_from_chat(phone=from_number, profile_name=profile_name, lead_data=lead_data, status="Partial")
                    reply_text = re.sub(r'\[LEAD_PARTIAL:\s*\{.*?\}\s*\]', '', reply_text, flags=re.DOTALL).strip()
                except Exception as e:
                    logger.error(f"Error parsing LEAD_PARTIAL tag: {e}")

            if submit_match:
                try:
                    lead_data = json.loads(submit_match.group(1))
                    db.upsert_lead_from_chat(phone=from_number, profile_name=profile_name, lead_data=lead_data, status="New")
                    cleaned_text = re.sub(r'\[LEAD_SUBMIT:\s*\{.*?\}\s*\]', '', reply_text, flags=re.DOTALL).strip()
                    success_msg = f"🎉 *Inquiry Submitted Successfully!*\n\nOur sales representatives are reviewing your requirements and will reach out shortly."
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
            
        send_whatsapp_message(from_number, reply_text, image_url=image_url, show_menu=menu_match, show_categories_menu=cat_match, show_call_cta=call_match)
    except Exception as e:
        logger.error(f"Error in background task: {e}")

@router.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
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
                    
                    incoming_msg = ""
                    if msg_type == "text":
                        incoming_msg = msg.get("text", {}).get("body", "").strip()
                    elif msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        if interactive.get("type") == "list_reply":
                            incoming_msg = interactive.get("list_reply", {}).get("title", "").strip()
                        elif interactive.get("type") == "button_reply":
                            incoming_msg = interactive.get("button_reply", {}).get("title", "").strip()
                    
                    if not incoming_msg:
                        continue
                        
                    # Process Message in Background
                    background_tasks.add_task(process_incoming_message, from_number, incoming_msg, profile_name)
                    
        return Response(status_code=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return Response(status_code=500)
