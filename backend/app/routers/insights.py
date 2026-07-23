from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import User
from app.security import get_current_user, scope_filter
from app.services.analytics_service import query_revenue, rows_to_dicts
from app.routers.dashboard import common_filters

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
def insights(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    """
    Rule-based business insights computed directly from live revenue data:
    top growing / declining customers (last vs previous month), product
    growth, at-risk customers (no booking in the latest month despite prior
    activity), and a plain-language auto summary.

    This is deterministic and free to run on every request. To layer in an
    LLM-written narrative on top of these same numbers, call the Anthropic
    API from here with the computed stats as context — the numbers
    themselves should still come from this function, not be invented by
    the model.
    """
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)

    by_cust_month = defaultdict(lambda: defaultdict(float))
    for d in data:
        by_cust_month[d["customer"]][d["mIdx"]] += d["revenue"]

    growing, declining, risk = [], [], []
    for cust, months in by_cust_month.items():
        idxs = sorted(months.keys())
        if len(idxs) < 2:
            continue
        last, prev = months[idxs[-1]], months[idxs[-2]]
        pct = ((last - prev) / prev * 100) if prev > 0 else 0
        entry = {"customer": cust, "last_month_revenue": round(last, 2), "growth_pct": round(pct, 2)}
        if pct >= 15:
            growing.append(entry)
        elif pct <= -15:
            declining.append(entry)
        if last == 0 and prev > 0:
            risk.append({"customer": cust, "last_active_revenue": round(prev, 2)})

    growing.sort(key=lambda x: -x["growth_pct"])
    declining.sort(key=lambda x: x["growth_pct"])

    by_product_month = defaultdict(lambda: defaultdict(float))
    for d in data:
        by_product_month[d["product"]][d["mIdx"]] += d["revenue"]
    product_growth = []
    for prod, months in by_product_month.items():
        idxs = sorted(months.keys())
        if len(idxs) < 2:
            continue
        last, prev = months[idxs[-1]], months[idxs[-2]]
        pct = ((last - prev) / prev * 100) if prev > 0 else 0
        product_growth.append({"product": prod, "growth_pct": round(pct, 2)})
    product_growth.sort(key=lambda x: -x["growth_pct"])

    total_revenue = sum(d["revenue"] for d in data)
    opportunity = sum(e["last_active_revenue"] for e in risk)

    summary_parts = []
    if growing:
        summary_parts.append(f"{len(growing)} customers grew 15%+ month-on-month, led by {growing[0]['customer']}.")
    if declining:
        summary_parts.append(f"{len(declining)} customers declined 15%+, notably {declining[0]['customer']}.")
    if risk:
        summary_parts.append(f"{len(risk)} previously active customers booked nothing last month "
                              f"(₹{round(opportunity,1)} lakh at risk).")
    if not summary_parts:
        summary_parts.append("Revenue is broadly stable across customers this period.")

    return {
        "top_growing_customers": growing[:10],
        "declining_customers": declining[:10],
        "product_growth": product_growth,
        "risk_customers": risk[:10],
        "revenue_opportunity_lakh": round(opportunity, 2),
        "total_revenue_lakh": round(total_revenue, 2),
        "auto_summary": " ".join(summary_parts),
    }
