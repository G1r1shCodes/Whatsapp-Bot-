import pandas as pd
import db

def ingest_excel(file_path):
    print(f"Reading Excel file: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return

    # Replace NaNs with None
    df = df.where(pd.notnull(df), None)

    updated_count = 0
    created_count = 0

    for index, row in df.iterrows():
        name = row.get("name")
        if not name or pd.isna(name):
            continue

        try:
            core_val = int(row.get("core"))
        except (ValueError, TypeError):
            core_val = None

        try:
            price_val = float(row.get("price_per_meter"))
        except (ValueError, TypeError):
            price_val = None

        def clean_str(val):
            return str(val).strip() if pd.notnull(val) else ""

        product_data = {
            "name": clean_str(name),
            "category": clean_str(row.get("category")),
            "conductor": clean_str(row.get("conductor")),
            "size": clean_str(row.get("size")),
            "core": core_val,
            "insulation": clean_str(row.get("insulation")),
            "price_per_meter": price_val,
            "stock_status": clean_str(row.get("stock_status")),
            "specifications": clean_str(row.get("specifications"))
        }

        status = db.upsert_product(product_data)
        if status == "updated":
            updated_count += 1
            print(f"Updated: {name}")
        elif status == "created":
            created_count += 1
            print(f"Created: {name}")

    print(f"Ingestion complete! Created: {created_count}, Updated: {updated_count}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ingest_excel(sys.argv[1])
    else:
        print("Usage: python ingest_excel.py <path_to_excel_file>")
