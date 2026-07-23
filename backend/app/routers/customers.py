from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from collections import defaultdict

from app.database import get_db
from app.models import User, Customer, Revenue, Product
from app.security import get_current_user, scope_filter
from app.services.analytics_service import query_revenue, rows_to_dicts

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _scoped_customers(db: Session, user: User):
    scope = scope_filter(user)
    q = db.query(Customer)
    if scope.get("region"):
        q = q.filter(Customer.region == scope["region"])
    if scope.get("division"):
        q = q.filter(Customer.division == scope["division"])
    if scope.get("office"):
        q = q.filter(Customer.office == scope["office"])
    return q


@router.get("")
def list_customers(
    page: int = 1, page_size: int = 25,
    sort_by: str = "customer_name", sort_dir: str = "asc",
    search: Optional[str] = None,
    division: Optional[str] = None, region: Optional[str] = None,
    office: Optional[str] = None, category: Optional[str] = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    q = _scoped_customers(db, user)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Customer.customer_name.ilike(like), Customer.customer_code.ilike(like),
                          Customer.gst_number.ilike(like)))
    if division:
        q = q.filter(Customer.division == division)
    if region:
        q = q.filter(Customer.region == region)
    if office:
        q = q.filter(Customer.office == office)
    if category:
        q = q.filter(Customer.category == category)

    sort_col = getattr(Customer, sort_by, Customer.customer_name)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [{
            "id": c.id, "customer_code": c.customer_code, "customer_name": c.customer_name,
            "gst_number": c.gst_number, "mobile": c.mobile, "division": c.division,
            "region": c.region, "office": c.office, "category": c.category,
        } for c in items],
    }


@router.get("/search")
def search_customers(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    like = f"%{q}%"
    query = _scoped_customers(db, user).filter(or_(
        Customer.customer_name.ilike(like), Customer.customer_code.ilike(like),
        Customer.gst_number.ilike(like), Customer.mobile.ilike(like),
        Customer.division.ilike(like), Customer.office.ilike(like),
    )).limit(50)
    return [{
        "id": c.id, "customer_code": c.customer_code, "customer_name": c.customer_name,
        "division": c.division, "office": c.office, "gst_number": c.gst_number, "mobile": c.mobile,
    } for c in query.all()]


@router.get("/{customer_id}")
def customer_profile(customer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cust = _scoped_customers(db, user).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found or out of your access scope")

    rows = db.query(Revenue).join(Product).filter(Revenue.customer_id == customer_id).all()
    monthly = defaultdict(float)
    quarterly = defaultdict(float)
    by_product = defaultdict(float)
    total_revenue = 0.0
    total_articles = 0
    for r in rows:
        monthly[r.month_index] += r.revenue
        quarterly[r.quarter] += r.revenue
        by_product[r.product_rel.product_name] += r.revenue
        total_revenue += r.revenue
        total_articles += r.articles

    idxs = sorted(monthly.keys())
    trend_growth = 0.0
    if len(idxs) >= 2:
        last, prev = monthly[idxs[-1]], monthly[idxs[-2]]
        if prev > 0:
            trend_growth = round((last - prev) / prev * 100, 2)

    # simple 3-month forward forecast via linear trend on last 3 points
    forecast = []
    if len(idxs) >= 2:
        recent = [monthly[i] for i in idxs[-3:]]
        avg_delta = (recent[-1] - recent[0]) / max(1, len(recent) - 1)
        last_val = recent[-1]
        for i in range(1, 4):
            forecast.append(round(max(0, last_val + avg_delta * i), 2))

    return {
        "customer": {
            "id": cust.id, "customer_code": cust.customer_code, "customer_name": cust.customer_name,
            "gst_number": cust.gst_number, "mobile": cust.mobile, "email": cust.email,
            "division": cust.division, "region": cust.region, "office": cust.office,
            "category": cust.category,
        },
        "total_revenue": round(total_revenue, 2),
        "total_articles": total_articles,
        "monthly_trend": [round(monthly.get(i, 0), 2) for i in range(12)],
        "quarterly_trend": {q: round(v, 2) for q, v in quarterly.items()},
        "products": {k: round(v, 2) for k, v in by_product.items()},
        "growth_pct": trend_growth,
        "forecast_next_3_months": forecast,
        "retention_status": "Active" if trend_growth > -30 else "At Risk",
    }
