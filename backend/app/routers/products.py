from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import User
from app.security import get_current_user, scope_filter
from app.services.analytics_service import query_revenue, rows_to_dicts
from app.routers.dashboard import common_filters

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
def product_revenue(filters: dict = Depends(common_filters), db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)
    by_product = defaultdict(lambda: {"revenue": 0.0, "articles": 0, "target": 0.0})
    for d in data:
        p = by_product[d["product"]]
        p["revenue"] += d["revenue"]
        p["articles"] += d["articles"]
        p["target"] += d["target"]
    return [{"product": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}}
            for k, v in sorted(by_product.items(), key=lambda x: -x[1]["revenue"])]
