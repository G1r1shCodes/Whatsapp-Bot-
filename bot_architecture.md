# KDI Power AI WhatsApp Assistant – Knowledge Base Architecture

## Objective

Build an AI-powered WhatsApp assistant that can:

- Answer customer queries.
- Provide product information.
- Answer technical questions.
- Recommend products.
- Share product images.
- Capture sales leads.
- Maintain conversation history.
- Support sales teams.

---

# Data Sources

The company may provide:

- Product Catalog PDFs
- Excel Files
- Product Images
- Brochures
- Technical Documents
- Price Lists
- Internal Documents

---

# 1. PDF Knowledge Base

Catalog PDFs may contain:

- Product descriptions
- Specifications
- Features
- Applications
- Technical details
- Product images
- Tables

---

## Processing Pipeline

```text
PDF
    ↓
Text Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Database
```

Recommended tools:

- PyMuPDF
- MinerU
- LangChain
- FAISS
- ChromaDB

---

## Example Queries

User:
> Which cable is suitable for industrial applications?

System:
1. Search vector database.
2. Retrieve relevant information.
3. Send context to the LLM.
4. Generate response.

---

# 2. Excel Files

Excel files may contain:

- Product information
- Pricing data
- Stock details
- Internal records
- Specifications
- Customer information

The actual structure will depend on the company data.

The system should:

- Read the Excel files.
- Understand available columns.
- Convert useful information into searchable knowledge.
- Store structured information when possible.

---

# 3. Product Images

Catalog PDFs may contain product images.

Images can later be associated with products.

Example:

- Product photo
- Cable image
- Equipment image

---

## Example Query

User:
> Show me the image of this cable.

System:
- Retrieve associated image.
- Send image through WhatsApp.

---

# System Architecture

```text
Customer
    ↓
WhatsApp Business
    ↓
WhatsApp Web
    ↓
FastAPI Backend
    ↓
Intent Detection
    ↓

Structured Information?
        ↓
    Company Data

Technical Question?
        ↓
    Vector Database

Image Request?
        ↓
    Product Images

    ↓
Groq / Gemini
    ↓
Response
    ↓
WhatsApp
```

---

# Types of Responses

## 1. Information Retrieval

Examples:
- Product details
- Availability
- Specifications

---

## 2. AI Responses

Examples:
- Product recommendations
- Technical explanations
- Application guidance

---

## 3. Visual Responses

Examples:
- Product images
- Catalog pages

---

# Example Conversations

Customer:
> Which cable is suitable for underground applications?

Bot:
> Based on the product catalog, the XLPE armoured cable is recommended for underground applications due to its insulation and protection properties.

---

Customer:
> Show me its image.

Bot:
> Sends the product image.

---

# Storage Components

## Supabase

- Leads
- Conversations
- Product information (if structured)

---

## Vector Database

Stores:

- Catalog PDFs
- Brochures
- Specifications
- Technical documents
- FAQs

---

## Image Storage

Stores:

- Product images
- Catalog images

---

# Future Features

- Voice message support
- Multi-language support
- Quotation generation
- PDF sharing
- Human handoff
- Follow-up reminders

---

# Final Goal

The assistant should act as a digital sales representative that can:

- Answer customer questions.
- Provide technical information.
- Recommend products.
- Share product images.
- Capture leads.
- Assist customers 24/7.
