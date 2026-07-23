import io
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import pandas as pd

from app.database import get_db
from app.models import User, Customer, Product, Revenue, UploadBatch
from app.security import get_current_user

router = APIRouter(prefix="/api/upload", tags=["upload"])

REQUIRED_COLUMNS = [
    "Customer Code", "Customer Name", "Division", "Office", "Product",
    "Revenue", "Articles", "Month", "Quarter", "FY",
]

MONTH_INDEX = {m: i for i, m in enumerate(
    ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"])}


@router.post("/excel")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    if user.role not in ("Circle", "Division", "Office"):
        raise HTTPException(status_code=403, detail="You do not have permission to upload data")

    filename = file.filename or "upload"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ("xlsx", "xls", "csv"):
        raise HTTPException(status_code=400, detail="Only .xlsx, .xls or .csv files are accepted")

    raw = await file.read()
    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(raw))
        else:
            df = pd.read_excel(io.BytesIO(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_cols)}")

    errors = []
    inserted = 0
    failed = 0
    duplicates = 0
    seen_keys = set()

    # cache lookups
    products = {p.product_name: p for p in db.query(Product).all()}

    for idx, row in df.iterrows():
        row_no = idx + 2  # account for header row
        try:
            code = str(row["Customer Code"]).strip()
            name = str(row["Customer Name"]).strip()
            division = str(row["Division"]).strip()
            office = str(row["Office"]).strip()
            product_name = str(row["Product"]).strip()
            revenue = float(row["Revenue"])
            articles = int(row["Articles"])
            month = str(row["Month"]).strip()
            quarter = str(row["Quarter"]).strip()
            fy = str(row["FY"]).strip()

            if not code or not name:
                errors.append(f"Row {row_no}: Customer Code / Customer Name is required")
                failed += 1
                continue
            if month not in MONTH_INDEX:
                errors.append(f"Row {row_no}: '{month}' is not a valid month (expected Apr..Mar)")
                failed += 1
                continue
            if product_name not in products:
                errors.append(f"Row {row_no}: unknown product '{product_name}'")
                failed += 1
                continue
            if revenue < 0 or articles < 0:
                errors.append(f"Row {row_no}: revenue/articles cannot be negative")
                failed += 1
                continue

            key = (code, product_name, month, fy)
            if key in seen_keys:
                duplicates += 1
                continue
            seen_keys.add(key)

            cust = db.query(Customer).filter(Customer.customer_code == code).first()
            if not cust:
                cust = Customer(
                    customer_code=code, customer_name=name, division=division,
                    office=office, region=None, category="Corporate",
                )
                db.add(cust)
                db.flush()

            existing = db.query(Revenue).join(Product).filter(
                Revenue.customer_id == cust.id, Product.product_name == product_name,
                Revenue.month == month, Revenue.financial_year == fy,
            ).first()
            if existing:
                duplicates += 1
                continue

            db.add(Revenue(
                customer_id=cust.id, product_id=products[product_name].id,
                month=month, month_index=MONTH_INDEX[month], quarter=quarter, financial_year=fy,
                articles=articles, revenue=revenue, target=revenue,
            ))
            inserted += 1
        except Exception as e:
            errors.append(f"Row {row_no}: {e}")
            failed += 1

    db.commit()

    batch = UploadBatch(
        filename=filename, uploaded_by=user.username, rows_uploaded=len(df),
        rows_failed=failed, duplicate_rows=duplicates, inserted_rows=inserted,
        errors_json=json.dumps(errors[:200]),
    )
    db.add(batch)
    db.commit()

    return {
        "rows_uploaded": len(df), "rows_failed": failed, "duplicate_rows": duplicates,
        "inserted_rows": inserted, "validation_errors": errors[:50],
    }
