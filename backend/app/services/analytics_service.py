from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models import Revenue, Customer, Product


def query_revenue(
    db: Session,
    scope: Dict[str, Optional[str]],
    financial_year: Optional[str] = None,
    division: Optional[str] = None,
    region: Optional[str] = None,
    office: Optional[str] = None,
    product: Optional[str] = None,
    month: Optional[str] = None,
    quarter: Optional[str] = None,
    category: Optional[str] = None,
):
    q = (
        db.query(Revenue)
        .join(Customer, Revenue.customer_id == Customer.id)
        .join(Product, Revenue.product_id == Product.id)
        .options(joinedload(Revenue.customer_rel), joinedload(Revenue.product_rel))
    )
    # role-based scoping (hard constraint, cannot be overridden by filters)
    if scope.get("region"):
        q = q.filter(Customer.region == scope["region"])
    if scope.get("division"):
        q = q.filter(Customer.division == scope["division"])
    if scope.get("office"):
        q = q.filter(Customer.office == scope["office"])

    if financial_year:
        q = q.filter(Revenue.financial_year == financial_year)
    if division:
        q = q.filter(Customer.division == division)
    if region:
        q = q.filter(Customer.region == region)
    if office:
        q = q.filter(Customer.office == office)
    if product:
        q = q.filter(Product.product_name == product)
    if month:
        q = q.filter(Revenue.month == month)
    if quarter:
        q = q.filter(Revenue.quarter == quarter)
    if category:
        q = q.filter(Customer.category == category)
    return q


def rows_to_dicts(rows: List[Revenue]) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        c = r.customer_rel
        out.append({
            "month": r.month, "mIdx": r.month_index, "quarter": r.quarter,
            "customer": c.customer_name, "code": c.customer_code,
            "division": c.division, "region": c.region, "office": c.office,
            "category": c.category, "product": r.product_rel.product_name,
            "revenue": r.revenue, "articles": r.articles, "target": r.target,
        })
    return out
