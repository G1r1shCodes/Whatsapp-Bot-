"""
Parse scraped product pages from data/products/ and bulk-upload to Supabase products table.
Extracts product name, category, conductor, size, core, insulation, price, stock status.
"""
import os
import sys
import re

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
from logger import get_logger

logger = get_logger(__name__)

PRODUCTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "products")

# Map filenames to categories
CATEGORY_MAP = {
    "electric-house-wire": "House Wires",
    "electrical-wire": "Electrical Wires",
    "flexible-pvc-insulated-cord-cable": "Flexible Cables",
    "multi-core-wire": "Multi Core Wires",
    "copper-armoured-cable": "Copper Armoured Cables",
    "copper-unarmoured-cable": "Copper Unarmoured Cables",
    "copper-conductor-xlpe-armoured-cable": "Copper XLPE Armoured Cables",
    "copper-conductor-xlpe-unarmoured-cable": "Copper XLPE Unarmoured Cables",
    "aluminium-conductor-xlpe-armoured-cable": "Aluminium XLPE Armoured Cables",
    "aluminum-unarmoured-cable": "Aluminium Unarmoured Cables",
    "armoured-cable": "Armoured Cables",
    "control-cable": "Control Cables",
    "ht-cables": "HT Cables",
    "insulated-cables": "Insulated Cables",
    "industrial-wires": "Industrial Wires",
    "solar-cable": "Solar Cables",
    "submersible-cable": "Submersible Cables",
    "thermocouple-compensating-cables": "Thermocouple Cables",
    "triple-coating-cable": "Triple Coating Cables",
    "wind-power-cable": "Wind Power Cables",
    "cable-and-wire": "General Cables",
}


def parse_product_block(block_text, default_category):
    """Parse a single product block from the scraped text."""
    lines = [l.strip() for l in block_text.strip().split("\n") if l.strip()]
    if len(lines) < 3:
        return None

    product = {
        "name": "",
        "category": default_category,
        "conductor": "",
        "size": "",
        "core": None,
        "insulation": "",
        "price_per_meter": None,
        "stock_status": "In Stock",
        "specifications": "",
    }

    # First line is usually the product name
    product["name"] = lines[0]

    specs = []
    i = 1
    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        # Price detection: "₹ 100" or "₹ 49"
        price_match = re.match(r'₹\s*([\d,.]+)', line)
        if price_match:
            try:
                product["price_per_meter"] = float(price_match.group(1).replace(",", ""))
            except ValueError:
                pass
            i += 1
            continue

        # Key-value pairs
        key_lower = line.lower()

        if key_lower in ("conductor material", "conductor") and next_line and len(next_line) < 30:
            if next_line.lower() in ("copper", "aluminium", "aluminum"):
                product["conductor"] = next_line.title()
                if next_line.lower() == "aluminum":
                    product["conductor"] = "Aluminium"
                i += 2
                continue

        if key_lower in ("conductor size", "size") and next_line:
            size_match = re.match(r'([\d.]+)', next_line)
            if size_match:
                product["size"] = next_line.strip()
                # Check if next-next line has "sq mm"
                nn = lines[i + 2] if i + 2 < len(lines) else ""
                if "sq" in nn.lower():
                    product["size"] = next_line.strip() + " " + nn.strip()
                    i += 3
                    continue
                i += 2
                continue

        if key_lower in ("number of core", "number of cores") and next_line:
            core_match = re.match(r'([\d.]+)', next_line)
            if core_match:
                try:
                    product["core"] = int(float(core_match.group(1)))
                except ValueError:
                    pass
                i += 2
                continue

        if key_lower in ("insulation material", "insulation") and next_line and len(next_line) < 30:
            product["insulation"] = next_line.strip()
            i += 2
            continue

        if key_lower == "voltage" and next_line:
            specs.append(f"Voltage: {next_line}")
            i += 2
            continue

        if key_lower == "rated voltage" and next_line:
            specs.append(f"Rated Voltage: {next_line}")
            i += 2
            continue

        if key_lower == "voltage grade" and next_line:
            specs.append(f"Voltage Grade: {next_line}")
            i += 2
            continue

        i += 1

    product["specifications"] = "; ".join(specs) if specs else ""

    # Infer conductor from name if not found
    if not product["conductor"]:
        name_lower = product["name"].lower()
        if "copper" in name_lower or "cu " in name_lower:
            product["conductor"] = "Copper"
        elif "aluminium" in name_lower or "aluminum" in name_lower:
            product["conductor"] = "Aluminium"

    # Infer size from name if not found
    if not product["size"]:
        size_match = re.search(r'([\d.]+)\s*(?:sq\s*mm|sqmm)', product["name"], re.IGNORECASE)
        if size_match:
            product["size"] = size_match.group(1) + " sq mm"

    # Infer core from name if not found
    if product["core"] is None:
        core_match = re.search(r'(\d+)\s*core', product["name"], re.IGNORECASE)
        if core_match:
            try:
                product["core"] = int(core_match.group(1))
            except ValueError:
                pass

    # Infer insulation from name if not found
    if not product["insulation"]:
        name_lower = product["name"].lower()
        if "xlpe" in name_lower:
            product["insulation"] = "XLPE"
        elif "pvc" in name_lower:
            product["insulation"] = "PVC"
        elif "epr" in name_lower:
            product["insulation"] = "EPR"
        elif "frls" in name_lower:
            product["insulation"] = "FRLS"

    # Skip garbage entries
    if len(product["name"]) < 5 or product["name"].lower() in ("view more", "yes! i am interested", "get best quote"):
        return None

    return product


def parse_product_file(filepath, category):
    """Parse a scraped product page and extract individual products."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    products = []

    # Split by "Get Best Quote" or "Request Callback" markers — each one starts a product block
    # The product name is typically the line before "Get Best Quote"
    blocks = re.split(r'(?=Get Best Quote)', content)

    for block in blocks:
        if "₹" not in block and "Conductor" not in block:
            continue
        # Find the product name: it's the last non-empty line before "Get Best Quote"
        pre_lines = block.split("Get Best Quote")[0].strip().split("\n")
        pre_lines = [l.strip() for l in pre_lines if l.strip()]

        if not pre_lines:
            continue

        # The product name is the last meaningful line before "Get Best Quote"
        product_name = pre_lines[-1] if pre_lines else ""

        # Now parse the rest of the block
        product = parse_product_block(block, category)
        if product:
            # Override name with what we found before the marker
            if product_name and len(product_name) > 5 and product_name.lower() not in ("view more",):
                product["name"] = product_name
            products.append(product)

    return products


def ingest_all():
    """Parse all product files and upload to Supabase."""
    if not os.path.isdir(PRODUCTS_DIR):
        logger.error(f"Products directory not found: {PRODUCTS_DIR}")
        return

    all_products = []
    files = sorted(os.listdir(PRODUCTS_DIR))

    for filename in files:
        if not filename.endswith(".txt"):
            continue

        base = filename.replace(".txt", "")
        category = CATEGORY_MAP.get(base, base.replace("-", " ").title())
        filepath = os.path.join(PRODUCTS_DIR, filename)

        logger.info(f"Parsing: {filename} -> Category: {category}")
        products = parse_product_file(filepath, category)
        logger.info(f"  Found {len(products)} products")
        all_products.extend(products)

    # Deduplicate by name
    seen = {}
    unique_products = []
    for p in all_products:
        name = p["name"]
        if name not in seen:
            seen[name] = True
            unique_products.append(p)

    logger.info(f"\nTotal unique products to upload: {len(unique_products)}")

    created = 0
    updated = 0
    for p in unique_products:
        status = db.upsert_product(p)
        if status == "created":
            created += 1
            print(f"  [OK] Created: {p['name']}")
        elif status == "updated":
            updated += 1
            print(f"  [UP] Updated: {p['name']}")
        else:
            print(f"  [--] Skipped: {p['name']}")

    print(f"\nDone! Created: {created}, Updated: {updated}, Total: {created + updated}")


if __name__ == "__main__":
    ingest_all()
