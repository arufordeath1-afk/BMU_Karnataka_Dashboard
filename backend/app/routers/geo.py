from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import User
from app.security import get_current_user, scope_filter
from app.services.analytics_service import query_revenue, rows_to_dicts
from app.routers.dashboard import common_filters

router = APIRouter(prefix="/api", tags=["geography"])


def _aggregate_by(db, user, filters, key):
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)
    out = defaultdict(lambda: {"revenue": 0.0, "articles": 0, "target": 0.0, "customers": set()})
    for d in data:
        g = out[d[key]]
        g["revenue"] += d["revenue"]
        g["articles"] += d["articles"]
        g["target"] += d["target"]
        g["customers"].add(d["customer"])
    result = []
    for name, g in out.items():
        ach = round((g["revenue"] / g["target"] * 100) if g["target"] else 0, 2)
        result.append({
            "name": name, "revenue": round(g["revenue"], 2), "articles": g["articles"],
            "target": round(g["target"], 2), "achievement_pct": ach, "customer_count": len(g["customers"]),
        })
    result.sort(key=lambda x: -x["revenue"])
    return result


@router.get("/divisions")
def divisions(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    return _aggregate_by(db, user, filters, "division")


@router.get("/offices")
def offices(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    return _aggregate_by(db, user, filters, "office")


@router.get("/regions")
def regions(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    return _aggregate_by(db, user, filters, "region")
