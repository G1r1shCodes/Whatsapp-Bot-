import os
import shutil
import glob
import fitz

# Folders to create
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

# PDF Extraction
pdfs = {
    "KDI CATALOGUE/CATALOUGE.pdf": "data/catalog/catalog.txt",
    "KDI CATALOGUE/CONTROL_CABLE_PRICE.pdf": "data/prices/price_control.txt",
    "KDI CATALOGUE/CU_FLEXIBLE_PRICES.pdf": "data/prices/price_cu_flexible.txt",
    "KDI CATALOGUE/POWER_CABLE_PRICE.pdf": "data/prices/price_power.txt"
}

for pdf_path, txt_path in pdfs.items():
    if os.path.exists(pdf_path):
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)

# Combine into kdi_knowledge.txt
with open("kdi_knowledge.txt", "w", encoding="utf-8") as output:
    for root_dir, _, files in os.walk("data"):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root_dir, file)
                
                # Create a nice header
                category = os.path.basename(root_dir).upper()
                name = os.path.splitext(file)[0].upper().replace("_", " ")
                
                output.write(f"\n\n===== {category} - {name} =====\n\n")
                
                with open(file_path, "r", encoding="utf-8") as f:
                    output.write(f.read())

print("Data processing complete. Final kdi_knowledge.txt generated.")
