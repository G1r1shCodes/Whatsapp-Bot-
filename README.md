# KDI Power AI WhatsApp Assistant & Sales Dashboard

![KDI Power Dashboard](dashboard_initial_view.png) <!-- Note: Replace with actual path if needed when viewing on GitHub -->

A state-of-the-art WhatsApp Assistant and Sales Dashboard built for **KDI Power**. 
It features a conversational AI bot (powered by Groq Llama-3) that interacts with customers on WhatsApp, captures structured sales leads, and persists them to a Supabase PostgreSQL database. The repository also includes a premium, glassmorphic dark-mode Sales Dashboard to visualize analytics, manage the leads inbox, and update the cable products catalog in real-time.

## 🚀 Features
- **AI WhatsApp Bot:** Understands natural language, answers catalog queries, and captures complex lead details conversationally.
- **Supabase Cloud DB:** Completely serverless database connection for Leads, Chat History, and Product Catalog.
- **Glassmorphic SPA Dashboard:** Built with HTML/CSS/JS and Chart.js for beautiful, real-time analytics and lead management.
- **Real-Time Catalog Manager:** Inline price and stock editing that immediately updates the bot's knowledge base.

## 🛠️ Tech Stack
- **Backend:** Python, FastAPI, Uvicorn
- **AI Engine:** Groq API (Llama-3.1-8b-instant)
- **Database:** Supabase (PostgreSQL / PostgREST)
- **Messaging:** Twilio WhatsApp API
- **Frontend:** HTML, Vanilla CSS (CSS Variables, Glassmorphism), Vanilla JS, Chart.js

## 💻 Local Setup

1. **Clone the repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up Environment Variables (`.env`):**
   ```env
   GROQ_API=your_groq_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   ```
4. **Run the server:**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```
5. **Access the Dashboard:** Open `http://localhost:8000/dashboard` in your browser.

## ☁️ Deployment on Render

This application is fully ready to be deployed on [Render.com](https://render.com/).

1. Create a new **Web Service** on Render and connect this GitHub repository.
2. **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Start Command:**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```
4. **Environment Variables:** Add `GROQ_API`, `SUPABASE_URL`, and `SUPABASE_KEY` in the Render dashboard.
5. **Twilio Webhook:** Once deployed, copy your Render URL (e.g., `https://kdi-power-bot.onrender.com/whatsapp`) and paste it into your Twilio Sandbox settings under "When a message comes in".

---
*Tags: python, fastapi, twilio, whatsapp-bot, ai-agent, groq, llama3, supabase, dashboard, sales-crm*
