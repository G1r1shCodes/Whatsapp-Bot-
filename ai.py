import os
import urllib.parse
import json
import time
import re
import db
import warnings
import prompts
import httpx
import warnings
import prompts
from collections import defaultdict
from logger import get_logger

logger = get_logger(__name__)
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client

# Suppress some of the verbose langchain warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

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
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

http_client = httpx.Client(timeout=30.0)


# Initialize Vector DB globally to avoid reloading models per request
try:
    # threads=1 limits ONNX runtime memory footprint to avoid 512MB limit on Render
    embeddings = FastEmbedEmbeddings(threads=1)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    vectorstore = SupabaseVectorStore(
        client=supabase,
        embedding=embeddings,
        table_name="documents",
        query_name="match_documents"
    )
except Exception as e:
    logger.warning(f"Could not initialize Supabase vectorstore. {e}")
    vectorstore = None

def get_ai_response(phone, profile_name):
    # Fetch chat history
    history = db.get_chat_history(phone)

    # Determine the last inbound user message
    last_msg = ""
    inbound_history = [m for m in history if m["direction"] == "inbound"]
    if inbound_history:
        last_msg = inbound_history[-1]["body"].strip().lower()

    last_msg_clean = re.sub(r'[^\w\s]', '', last_msg).strip()
    greeting_words = {"hi", "hello", "hey", "hii", "helo", "yoo", "greetings", "dear", "sup", "hi there", "hello there", "good morning", "good evening", "good afternoon", "namaste", "namaskar", "pranam"}
    is_greeting = last_msg_clean in greeting_words

    # conversation_start = True means this is the very first message (no prior history)
    # OR user sent a greeting (restart flow)
    is_first_message = len(inbound_history) <= 1
    conversation_start = is_first_message or is_greeting

    if conversation_start:
        # Trim history to just the most recent message — no need for context on greetings
        history = history[-1:]

    # --- RAG: Retrieve relevant chunks for the user's query ---
    retrieved_context = ""
    if not conversation_start and last_msg_clean and vectorstore is not None:
        try:
            docs = vectorstore.similarity_search(last_msg, k=3)
            if docs:
                raw_context = "\n".join(doc.page_content for doc in docs)
                # Clean up raw website UI button/navigation phrases
                phrases_to_remove = [
                    r"(?i)get\s+best\s+quote",
                    r"(?i)request\s+callback",
                    r"(?i)get\s+latest\s+price",
                    r"(?i)yes!\s+i\s+am\s+interested",
                    r"(?i)add\s+to\s+inquiry",
                    r"(?i)send\s+inquiry",
                ]
                cleaned = raw_context
                for pattern in phrases_to_remove:
                    cleaned = re.sub(pattern, "", cleaned)
                # Clean up double linebreaks or trailing whitespace
                cleaned = "\n".join(line.strip() for line in cleaned.split("\n") if line.strip())
                retrieved_context = cleaned
        except Exception as e:
            logger.error(f"Vector search error: {e}")

    # --- Products: Only inject relevant products (or all if catalog is small) ---
    all_products = db.get_all_products()
    products_txt = ""
    # Filter products by keyword match to keep prompt lean
    relevant_products = [
        p for p in all_products
        if not last_msg_clean
        or any(kw in last_msg_clean for kw in [
            p.get('name', '').lower(),
            p.get('category', '').lower(),
            p.get('conductor', '').lower(),
            p.get('size', '').lower(),
        ])
    ] or all_products  # fallback to all products if no keyword match
    
    # Limit to top 15 to avoid Groq 413 Payload Too Large error
    relevant_products = relevant_products[:15]

    for p in relevant_products:
        products_txt += (
            f"🔹 *{p['name']}*\n"
            f"   ▫️ Category: {p['category']}\n"
            f"   ▫️ Specs: {p['conductor']} {p['size']} {p['core']}C {p['insulation']}\n"
            f"   ▫️ Price: ~INR {p['price_per_meter']}/m\n"
            f"   ▫️ Status: {p['stock_status']}\n\n"
        )

    # --- Available images ---
    images_txt = ""
    try:
        image_files = os.listdir("data/images")
        valid_images = [f for f in image_files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if valid_images:
            images_txt = "\n".join(valid_images)
    except Exception as e:
        logger.error(f"Error reading images directory: {e}")

    system_prompt = prompts.get_system_prompt(
        retrieved_context=retrieved_context,
        products_txt=products_txt,
        images_txt=images_txt,
        profile_name=profile_name,
        conversation_start=conversation_start,
    )

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
        
    if not GROQ_API_KEY:
        print("GROQ_API is missing. Returning mock AI response.")
        time.sleep(1) # Simulate network delay
        return "*(Mock AI Response)* Hello! I see you are testing the KDI Power Bot. We currently have *1.5 sq mm House Wire* and *2.5 sq mm Power Cable* in stock. Let me know if you need a quote or have any other questions!"

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.5
    }
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    
    retries = 4
    delay = 3.0
    
    for attempt in range(retries):
        try:
            response = http_client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            return res_data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as he:
            if he.response.status_code == 429 and attempt < retries - 1:
                logger.warning(f"Rate limited (429) by Groq. Retrying in {delay} seconds (attempt {attempt+1}/{retries})...")
                time.sleep(delay)
                delay *= 2.0  # Exponential backoff
                continue
            logger.error(f"Groq API HTTPStatusError {he.response.status_code}: {he.response.text}")
            break
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            break
            
    return "Sorry, I am experiencing a temporary technical issue. Please try again shortly or contact KDI Power support directly at +91-9205333843."
