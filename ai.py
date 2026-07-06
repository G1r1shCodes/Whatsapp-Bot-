import os
import urllib.request
import urllib.parse
import json
import time
import re
import db
import warnings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Suppress some of the verbose langchain warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Initialize Vector DB globally to avoid reloading models per request
try:
    hf_embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory="data/chroma_db", embedding_function=hf_embeddings)
except Exception as e:
    print("Warning: Could not initialize ChromaDB vectorstore.", e)
    vectorstore = None

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

    retrieved_context = ""
    if not is_greeting and last_msg_clean and vectorstore is not None:
        try:
            docs = vectorstore.similarity_search(last_msg, k=4)
            if docs:
                retrieved_context = "\n[KNOWLEDGE BASE CONTEXT]\nBelow is technical information from the KDI Catalog and Website. Use this to accurately answer the user:\n"
                for i, doc in enumerate(docs):
                    retrieved_context += f"--- Source {i+1} ---\n{doc.page_content}\n\n"
        except Exception as e:
            print("Vector search error:", e)

    # Get available images
    images_txt = ""
    try:
        image_files = os.listdir("data/images")
        valid_images = [f for f in image_files if f.endswith(('.jpg', '.jpeg', '.png'))]
        if valid_images:
            images_txt = "\n[AVAILABLE IMAGES]\nHere are the images currently available in the system:\n"
            for img in valid_images:
                images_txt += f"- {img}\n"
    except Exception as e:
        print("Error reading images directory:", e)

    system_prompt = f"""You are the official KDI Power AI Assistant on WhatsApp. 
KDI Power Private Limited is a premier manufacturer of high-quality electrical cables and wires based in Narela, New Delhi, India. We pride ourselves on industrial-grade manufacturing and reliable B2B supply.
{retrieved_context}
KDI Power Product Catalog (Structured Pricing & Stock Database):
{products_txt}
{images_txt}

Guidelines:
1. GREETING STRUCTURE: ONLY greet the user on the FIRST message of a conversation. If the user's message is a greeting, you MUST start your response with EXACTLY:
   "Hi {profile_name}" (replacing {profile_name} with their name, or using "Hi Sir/Mam" if the name is not known)
   "Welcome to KDI Power"
   (Note: "Welcome to KDI Power" MUST start on the very next line right after the greeting, with no empty lines in between). Follow this immediately with the standard options menu template. Do NOT include this greeting if they are asking a follow-up question.
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
9. CONTACT SALES TEAM: If the user selects the option to "Contact Sales Team" or wants to speak to a human, provide our head office address (H-1243, DSIDC Industrial Area, Narela, New Delhi - 110040) and inform them they will be connected with Vipul Kumar (Marketing Manager) shortly, or they can call +91-8043863456.
10. STRICT ANTI-HALLUCINATION RULE: If the customer asks about any cable size, cores, pricing, or product that is NOT explicitly listed in the KDI Power Catalog above, do NOT make up or guess any specifications, availability, or prices. Politely explain that it is not in our standard catalog, but state that we can manufacture custom cables to their specifications, and proceed to gather their details to submit as a custom sales lead.
11. CHAT RESPONSES FORMATTING: WhatsApp is a mobile chat application. Never send a "wall of text" message. Keep all responses brief and under 150 words. Use emojis, spacing, and bold text headers to format lists clean and readable. Maintain a professional and polite B2B tone appropriate for industrial buyers.
12. INITIAL OPTIONS MENU TEMPLATE: When displaying the initial greeting template, present the options exactly like this:
    Hi {profile_name}
    Welcome to KDI Power

    Please select an option to proceed:
    1️⃣ *Browse Cables Catalog*
    2️⃣ *Request a Customized Quote*
    3️⃣ *Track Inquiry Status*
    4️⃣ *Contact Sales Team*

    Simply reply with the number of your choice (e.g. 1, 2).
13. IMAGE ATTACHMENTS: If the user explicitly asks for a picture of a product, or if it would be highly relevant and helpful to show a picture of the product you are discussing, choose the best matching image from the [AVAILABLE IMAGES] list above. To send the image, include the following EXACT tag on a new line in your response:
    [IMAGE: filename.jpg]
    (Replace filename.jpg with the exact name of the image from the list). Do not invent image names.
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
