from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.models import User, Customer, Product
from app.security import get_current_user, scope_filter
from app.services.analytics_service import query_revenue, rows_to_dicts

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]


def common_filters(
    fy: Optional[str] = Query(None, alias="fy"),
    division: Optional[str] = None,
    region: Optional[str] = None,
    office: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
    quarter: Optional[str] = None,
    category: Optional[str] = None,
):
    return dict(financial_year=fy, division=division, region=region, office=office,
                product=product, month=month, quarter=quarter, category=category)


@router.get("/executive")
def executive_summary(
    filters: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)

    total_revenue = sum(d["revenue"] for d in data)
    total_target = sum(d["target"] for d in data)
    customers_in_scope = {d["customer"] for d in data}

    by_month = defaultdict(float)
    for d in data:
        by_month[d["mIdx"]] += d["revenue"]
    months_present = sorted(by_month.keys())
    growth = 0.0
    if len(months_present) >= 2:
        last, prev = by_month[months_present[-1]], by_month[months_present[-2]]
        if prev > 0:
            growth = (last - prev) / prev * 100

    by_customer = defaultdict(float)
    for d in data:
        by_customer[d["customer"]] += d["revenue"]
    top10 = sorted(by_customer.items(), key=lambda x: -x[1])[:10]
    top10_out = [{"customer": name, "revenue": round(rev, 2)} for name, rev in top10]

    by_product = defaultdict(float)
    for d in data:
        by_product[d["product"]] += d["revenue"]

    # naive active/new/lost: active = booked in last month present, new = only in last month,
    # lost = booked earlier but not in last month
    last_m = months_present[-1] if months_present else None
    prev_m = months_present[-2] if len(months_present) >= 2 else None
    cust_last = {d["customer"] for d in data if d["mIdx"] == last_m} if last_m is not None else set()
    cust_prev = {d["customer"] for d in data if d["mIdx"] == prev_m} if prev_m is not None else set()
    new_customers = len(cust_last - cust_prev) if prev_m is not None else len(cust_last)
    lost_customers = len(cust_prev - cust_last) if prev_m is not None else 0

    return {
        "total_revenue": round(total_revenue, 2),
        "total_customers": len(customers_in_scope),
        "active_customers": len(cust_last),
        "new_customers": new_customers,
        "lost_customers": lost_customers,
        "growth_pct": round(growth, 2),
        "achievement_pct": round((total_revenue / total_target * 100) if total_target else 0, 2),
        "top10": top10_out,
        "product_share": {k: round(v, 2) for k, v in by_product.items()},
    }


@router.get("/kpi")
def kpi(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    return executive_summary(filters, db, user)


@router.get("/monthly")
def monthly_trend(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)
    revenue = [0.0] * 12
    target = [0.0] * 12
    articles = [0] * 12
    for d in data:
        revenue[d["mIdx"]] += d["revenue"]
        target[d["mIdx"]] += d["target"]
        articles[d["mIdx"]] += d["articles"]
    return {"months": MONTHS, "revenue": [round(x, 2) for x in revenue],
            "target": [round(x, 2) for x in target], "articles": articles}


@router.get("/quarterly")
def quarterly_trend(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)
    out = {q: {"revenue": 0.0, "target": 0.0, "articles": 0} for q in ["Q1", "Q2", "Q3", "Q4"]}
    for d in data:
        out[d["quarter"]]["revenue"] += d["revenue"]
        out[d["quarter"]]["target"] += d["target"]
        out[d["quarter"]]["articles"] += d["articles"]
    for q in out:
        out[q]["revenue"] = round(out[q]["revenue"], 2)
        out[q]["target"] = round(out[q]["target"], 2)
    return out


@router.get("/bootstrap")
def bootstrap(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    """
    Returns raw customer + revenue rows in the exact shape the existing
    frontend's CUSTOMERS/DATA arrays used, scoped to the logged-in user's
    role. This lets every existing chart-rendering function in the
    dashboard run unchanged against live database data instead of the
    client-side mock generator.
    """
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)

    cust_q = db.query(Customer)
    if scope.get("region"):
        cust_q = cust_q.filter(Customer.region == scope["region"])
    if scope.get("division"):
        cust_q = cust_q.filter(Customer.division == scope["division"])
    if scope.get("office"):
        cust_q = cust_q.filter(Customer.office == scope["office"])
    customers = [{
        "id": c.id, "code": c.customer_code, "name": c.customer_name,
        "division": c.division, "region": c.region, "office": c.office,
        "category": c.category, "gst": c.gst_number, "mobile": c.mobile,
    } for c in cust_q.all()]

    products = [p.product_name for p in db.query(Product).all()]

    return {"customers": customers, "revenue": data, "products": products, "months": MONTHS}
