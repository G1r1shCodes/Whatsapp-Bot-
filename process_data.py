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

# File mappings (useful ones)
useful_files = {
    # Website
    "kdipower.com_about-us_.txt": "data/website/about.txt",
    "kdipower.com_faq.txt": "data/website/faq.txt",
    "kdipower.com_faq_.txt": "data/website/faq.txt", # sometimes it comes as this
    "kdipower.com_our-contacts_.txt": "data/website/contact.txt",
    "kdipower.com_our-team_.txt": "data/website/team.txt",
    "kdipower.com_solutions_.txt": "data/website/solutions.txt",
    "kdipower.com_certifications_.txt": "data/website/certifications.txt",
    "kdipower.com_apply-as-a-vendor-procurement-division_.txt": "data/website/vendor.txt",
    "kdipower.com_career_.txt": "data/website/career.txt",
    "kdipower.com_dealership-enquiry_.txt": "data/website/dealership.txt",
    "kdipower.com_life-at-kdi-power_.txt": "data/website/life.txt",
    
    # Products
    "kdipower.com_our-products_.txt": "data/products/our_products.txt",
    "kdipower.com_conductors_.txt": "data/products/conductors.txt",
    "kdipower.com_control-cables_.txt": "data/products/control_cables.txt",
    "kdipower.com_power-cable_.txt": "data/products/power_cable.txt",
    "kdipower.com_rubber-cables_.txt": "data/products/rubber_cables.txt",
    "kdipower.com_solar-cable_.txt": "data/products/solar_cable.txt",
    "kdipower.com_submersible-cables_.txt": "data/products/submersible_cables.txt",
    "kdipower.com_aerial-bunched-cables_.txt": "data/products/aerial_bunched_cables.txt",
    "kdipower.com_instrumentation-wires_.txt": "data/products/instrumentation_wires.txt",
    "kdipower.com_house-wires-cables_.txt": "data/products/house_wires_cables.txt",
    "kdipower.com_single-core-multicore-flexible-cables_.txt": "data/products/single_core_flexible_cables.txt",
    "kdipower.com_marine-offshore-cables_.txt": "data/products/marine_offshore_cables.txt"
}

# Move files
for src, dst in useful_files.items():
    if os.path.exists(src):
        # We use copy so we can delete all scraped files cleanly later
        shutil.copy(src, dst)

# Delete scraped txt files from the root
for f in glob.glob("*.txt"):
    if f not in ["requirements.txt"]:
        os.remove(f)

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
