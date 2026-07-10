import os
import sys
import math

# Add parent dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db
from logger import get_logger

logger = get_logger(__name__)

PRICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "prices")

def is_number(s):
    try:
        float(s.replace(',', ''))
        return True
    except ValueError:
        return False

def extract_power_cables(lines):
    products = []
    i = 0
    while i < len(lines):
        if is_number(lines[i]) and i+1 < len(lines) and is_number(lines[i+1]) and i+2 < len(lines) and not is_number(lines[i+2]):
            size = lines[i]
            core = lines[i+1]
            code = lines[i+2]
            
            j = i + 3
            block_lines = []
            # Gather lines until the next size/core pair
            while j < len(lines):
                if is_number(lines[j]) and j+1 < len(lines) and is_number(lines[j+1]) and j+2 < len(lines) and not is_number(lines[j+2]):
                    break
                block_lines.append(lines[j])
                j += 1
                
            # block_lines should contain List Price (opt), Armd/UnArmd, Discount, Net Price
            numbers = [float(x.replace(',', '')) for x in block_lines if is_number(x)]
            strings = [x for x in block_lines if not is_number(x)]
            
            armd_unarmd = strings[0] if strings else ""
            net_price = numbers[-1] if numbers else 0.0
            
            if net_price > 0:
                name = f"Aluminium Power Cable {size} sq mm {core}C {armd_unarmd}"
                products.append({
                    "name": name.strip(),
                    "category": "Power Cables",
                    "conductor": "Aluminium",
                    "size": f"{size} sq mm",
                    "core": int(float(core)),
                    "insulation": "XLPE/PVC",
                    "price_per_meter": net_price,
                    "stock_status": "In Stock",
                    "specifications": f"Code: {code}"
                })
            i = j
        else:
            i += 1
    return products

def extract_control_cables(lines):
    products = []
    i = 0
    while i < len(lines):
        if is_number(lines[i]) and i+1 < len(lines) and is_number(lines[i+1]) and i+2 < len(lines) and not is_number(lines[i+2]):
            size = lines[i]
            core = lines[i+1]
            code = lines[i+2]
            
            j = i + 3
            block_lines = []
            while j < len(lines):
                if is_number(lines[j]) and j+1 < len(lines) and is_number(lines[j+1]) and j+2 < len(lines) and not is_number(lines[j+2]):
                    break
                block_lines.append(lines[j])
                j += 1
                
            numbers = [float(x.replace(',', '')) for x in block_lines if is_number(x)]
            strings = [x for x in block_lines if not is_number(x)]
            
            armd_unarmd = strings[0] if strings else ""
            net_price = numbers[-1] if numbers else 0.0
            
            if net_price > 0:
                name = f"Copper Control Cable {size} sq mm {core}C {armd_unarmd}"
                products.append({
                    "name": name.strip(),
                    "category": "Control Cables",
                    "conductor": "Copper",
                    "size": f"{size} sq mm",
                    "core": int(float(core)),
                    "insulation": "PVC",
                    "price_per_meter": net_price,
                    "stock_status": "In Stock",
                    "specifications": f"Code: {code}"
                })
            i = j
        else:
            i += 1
    return products

def extract_flexible_cables(lines):
    products = []
    i = 0
    while i < len(lines):
        if is_number(lines[i]) and i+1 < len(lines) and is_number(lines[i+1]) and i+2 < len(lines) and not is_number(lines[i+2]):
            size = lines[i]
            core = lines[i+1]
            code = lines[i+2]
            
            j = i + 3
            block_lines = []
            while j < len(lines):
                if is_number(lines[j]) and j+1 < len(lines) and is_number(lines[j+1]) and j+2 < len(lines) and not is_number(lines[j+2]):
                    break
                block_lines.append(lines[j])
                j += 1
                
            numbers = [float(x.replace(',', '')) for x in block_lines if is_number(x)]
            
            net_price_mtr = numbers[-1] if numbers else 0.0
            
            if net_price_mtr > 0:
                name = f"Copper Flexible Cable {size} sq mm {core}C"
                products.append({
                    "name": name.strip(),
                    "category": "Flexible Cables",
                    "conductor": "Copper",
                    "size": f"{size} sq mm",
                    "core": int(float(core)),
                    "insulation": "PVC",
                    "price_per_meter": net_price_mtr,
                    "stock_status": "In Stock",
                    "specifications": f"Code: {code}"
                })
            i = j
        else:
            i += 1
    return products

def main():
    logger.info("Starting structured price ingestion...")
    all_products = []
    
    # 1. Power Cables
    power_file = os.path.join(PRICES_DIR, "price_power.txt")
    if os.path.exists(power_file):
        with open(power_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        power_prods = extract_power_cables(lines)
        all_products.extend(power_prods)
        logger.info(f"Extracted {len(power_prods)} Power Cables")
        
    # 2. Control Cables
    control_file = os.path.join(PRICES_DIR, "price_control.txt")
    if os.path.exists(control_file):
        with open(control_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        control_prods = extract_control_cables(lines)
        all_products.extend(control_prods)
        logger.info(f"Extracted {len(control_prods)} Control Cables")
        
    # 3. Flexible Cables
    flexible_file = os.path.join(PRICES_DIR, "price_cu_flexible.txt")
    if os.path.exists(flexible_file):
        with open(flexible_file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        flex_prods = extract_flexible_cables(lines)
        all_products.extend(flex_prods)
        logger.info(f"Extracted {len(flex_prods)} Flexible Cables")
        
    logger.info(f"Total structured products extracted: {len(all_products)}")
    
    if all_products:
        logger.info("Clearing existing products table...")
        from supabase import create_client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE credentials")
            return
            
        supabase = create_client(supabase_url, supabase_key)
        
        try:
            supabase.table("products").delete().neq("name", "").execute()
        except Exception as e:
            logger.error(f"Error clearing products: {e}")
            
        logger.info("Inserting new products...")
        # Chunk the insertion to avoid payload size limits
        chunk_size = 100
        for i in range(0, len(all_products), chunk_size):
            chunk = all_products[i:i+chunk_size]
            supabase.table("products").upsert(chunk).execute()
            logger.info(f"Inserted chunk {i//chunk_size + 1}")
        logger.info("Successfully populated complete product catalog.")
    else:
        logger.warning("No products extracted.")

if __name__ == "__main__":
    main()
