import os
import shutil
import glob
import fitz
import re
folders = [
    "data/website",
    "data/products",
    "data/catalog",
    "data/prices"
]
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# Website files are now scraped directly into data/website/ and data/products/
# by scrape_site.py, so we don't need to manually map or move them anymore.

def _strip_boilerplate(text: str) -> str:
    """Removes standard website header/footer noise from scraped text."""
    if not text or not text.strip():
        return ""
    
    # Remove footer starting at "Enquire Now" or "Facebook Instagram Linkedin" or "USEFULL LINKS"
    footer_patterns = [
        r"Enquire Now\s+Connect Us",
        r"Facebook Instagram Linkedin USEFULL LINKS.*",
        r"USEFULL LINKS.*",
        r"Facebook Instagram Linkedin Home About Us Our Products CONTACT US.*"
    ]
    for p in footer_patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE | re.DOTALL)
        
    # Remove header up to "Introduction" or first real content
    # The header usually ends with "X [Category] Home [Category] Introduction"
    # or just has a bunch of social links and email/phone.
    # A generic approach: remove everything before "Introduction" if "Introduction" exists.
    # Or remove standard header strings.
    header_regex = r".*?(?:Facebook Instagram Linkedin Home About Us Our Products\s+X\s+[\w\s&]+\s+Home\s+[\w\s&]+\s+)?Introduction"
    match = re.search(header_regex, text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = "Introduction" + text[match.end():]
        
    return text.strip()

# PDF Extraction
pdfs = {
    "data/raw_catalogues/CATALOUGE.pdf": "data/catalog/catalog.txt",
    "data/raw_catalogues/CONTROL_CABLE_PRICE.pdf": "data/prices/price_control.txt",
    "data/raw_catalogues/CU_FLEXIBLE_PRICES.pdf": "data/prices/price_cu_flexible.txt",
    "data/raw_catalogues/POWER_CABLE_PRICE.pdf": "data/prices/price_power.txt"
}

for pdf_path, txt_path in pdfs.items():
    if os.path.exists(pdf_path):
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

# Combine into data/kdi_knowledge.txt
with open("data/kdi_knowledge.txt", "w", encoding="utf-8") as output:
    for root_dir, _, files in os.walk("data"):
        for file in files:
            if file == "kdi_knowledge.txt":
                continue
            if file.endswith(".txt"):
                file_path = os.path.join(root_dir, file)
                
                # Create a nice header
                category = os.path.basename(root_dir).upper()
                name = os.path.splitext(file)[0].upper().replace("_", " ")
                
                output.write(f"\n\n===== {category} - {name} =====\n\n")
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if file_path.startswith("data\\website") or file_path.startswith("data/website") or file_path.startswith("data\\products") or file_path.startswith("data/products"):
                        content = _strip_boilerplate(content)
                    output.write(content)

import os
import sys
# Add parent dir to path to import logger
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import get_logger
logger = get_logger(__name__)

logger.info("Data processing complete. Final kdi_knowledge.txt generated.")
