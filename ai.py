import os
import urllib.request
import urllib.parse
import json
import time
import re
import db

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

# Load env variables on module import
load_env()

GROQ_API_KEY = os.environ.get("GROQ_API")
GROQ_MODEL = "llama-3.1-8b-instant"

def get_ai_response(phone, profile_name):
    # Fetch chat history
    history = db.get_chat_history(phone)
    
    # Check if last message is a standalone greeting to reset context for LLM
    last_msg = ""
    if history:
        inbound_history = [m for m in history if m["direction"] == "inbound"]
        if inbound_history:
            last_msg = inbound_history[-1]["body"].strip().lower()
            
    last_msg_clean = re.sub(r'[^\w\s]', '', last_msg).strip()
    is_greeting = last_msg_clean in ["hi", "hello", "hey", "hii", "yoo", "greetings", "dear", "sup", "hi there", "hello there"]
    
    if is_greeting:
        # Keep only the last message (the user's latest greeting) and clear older history
        history = history[-1:]
    
    # Get all products to populate knowledge base
    products = db.get_all_products()
    products_txt = ""
    for p in products:
        products_txt += (
            f"- Category: {p['category']}\n"
            f"  Name: {p['name']}\n"
            f"  Specs: Conductor={p['conductor']}, Size={p['size']}, Cores={p['core']}, Insulation={p['insulation']}\n"
            f"  Est. Price: INR {p['price_per_meter']}/meter\n"
            f"  Stock: {p['stock_status']}\n"
            f"  Description: {p['specifications']}\n\n"
        )

    system_prompt = f"""You are the official KDI Power AI Assistant on WhatsApp. 
KDI Power is a premier manufacturer of high-quality electrical cables and wires.

KDI Power Product Catalog:
{products_txt}

Guidelines:
1. GREETING STRUCTURE: When the user starts a conversation or sends a greeting (like 'hi', 'hello', or similar), you MUST start your response with EXACTLY:
   "Hi {profile_name}" (replacing {profile_name} with their name, or using "Hi Sir/Mam" if the name is not known)
   "Welcome to KDI Power"
   (Note: "Welcome to KDI Power" MUST start on the very next line right after the greeting, with no empty lines in between). Follow this immediately with the standard options menu template.
2. PRODUCT & SPECIFICATION INQUIRIES: Answer inquiries about product specifications, materials (Copper/Aluminium), stock status, and estimated pricing based ONLY on the catalog above. If the customer mentions a specific wire size (e.g. '1.5 sq mm' or '2.5 sq mm' or cores) in their first message, do NOT show the standard options menu template. Directly answer their technical query or offer to start the quote request. If they ask to browse standard products generally, show the 4 categories (House Wires, Power Cables, Submersible Cables, Control Cables) and ask them which category they are interested in.
3. If they inquire about pricing, ALWAYS remind them that cable prices fluctuate daily with copper/aluminum metal market rates and the quoted prices are indicative estimations.
4. If the customer wants to request a quote, conversationally gather the following details step-by-step:
   - Full Name
   - Company Name (if they are buying as an individual, they can say 'skip' or 'personal use')
   - Cable product model or technical specification they need
   - Quantity (meters, coils, or drums)
   - Delivery Location
5. Do not ask for all details at once. Ask for them conversationally, one or two at a time. Do not ask for details the user has already provided in previous messages (e.g. if they already said they need '1.5 sq mm copper wire', skip asking for the product).
6. Once you have collected all 5 details, output a summary and ask for their final confirmation (e.g. 'Please confirm if this is correct').
7. When the user confirms (e.g., they say 'Yes', 'Correct', 'Submit'), you MUST trigger the lead submission by outputting the EXACT tag:
   [LEAD_SUBMIT: {{"name": "NAME", "company": "COMPANY", "product": "PRODUCT", "quantity": "QTY", "location": "LOCATION"}} ]
   Replace the fields with the gathered data. Ensure it is valid JSON inside the tag. Do not output anything else on that line.
8. If they want to check their lead/inquiry status, output the tag:
   [LEAD_STATUS_CHECK]
9. STRICT ANTI-HALLUCINATION RULE: If the customer asks about any cable size, cores, pricing, or product that is NOT explicitly listed in the KDI Power Catalog above, do NOT make up or guess any specifications, availability, or prices. Politely explain that it is not in our standard catalog, but state that we can manufacture custom cables to their specifications, and proceed to gather their details to submit as a custom sales lead.
10. CHAT RESPONSES FORMATTING: WhatsApp is a mobile chat application. Never send a "wall of text" message. Keep all responses brief and under 150 words. Use emojis, spacing, and bold text headers to format lists clean and readable.
11. INITIAL OPTIONS MENU TEMPLATE: When displaying the initial greeting template, present the options exactly like this:
    Hi {profile_name}
    Welcome to KDI Power

    Please select an option to proceed:
    1️⃣ *Browse Cables Catalog*
    2️⃣ *Request a Customized Quote*
    3️⃣ *Track Inquiry Status*
    4️⃣ *Contact Sales Team*

    Simply reply with the number of your choice (e.g. 1, 2).
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Append conversation history (limit to last 15 messages to stay within limits)
    for msg in history[-15:]:
        role = "user" if msg["direction"] == "inbound" else "assistant"
        # Skip internal tags if they were sent to the user, or clean them
        content = msg["body"]
        if "[LEAD_SUBMIT:" in content:
            content = "Your inquiry has been submitted successfully."
        elif "[LEAD_STATUS_CHECK]" in content:
            content = "Checking your lead status..."
        messages.append({"role": role, "content": content})
        
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.5
    }
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {GROQ_API_KEY}")
    req.add_header("User-Agent", "Mozilla/5.0")
    
    retries = 4
    delay = 3.0
    
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req) as res:
                res_data = json.loads(res.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as he:
            if he.code == 429 and attempt < retries - 1:
                print(f"Rate limited (429) by Groq. Retrying in {delay} seconds (attempt {attempt+1}/{retries})...")
                time.sleep(delay)
                delay *= 2.0  # Exponential backoff
                continue
            print(f"Groq API HTTPError {he.code}: {he.reason}")
            break
        except Exception as e:
            print(f"Unexpected error calling Groq API: {e}")
            break
            
    return "Sorry, I am experiencing a temporary technical issue. Please try again shortly or contact KDI Power support directly at +91 98765 43210."
