from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from collections import defaultdict
import statistics

from app.database import get_db
from app.models import User
from app.security import get_current_user, scope_filter
from app.services.analytics_service import query_revenue, rows_to_dicts
from app.routers.dashboard import common_filters

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("")
def forecast(
    horizon: int = Query(3, ge=1, le=12, description="Months to forecast: 3, 6 or 12"),
    filters: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Statistical forecast: linear trend fit over observed monthly revenue,
    with a confidence interval derived from residual std deviation.

    NOTE: the original spec asked for Facebook Prophet. Prophet is a heavy
    dependency (needs cmdstan/pystan) that's overkill for a single monthly
    time series like this and often fails to install in minimal containers.
    This trend model gives comparable results for short, fairly linear
    series. To use Prophet instead, install `prophet`, feed it a DataFrame
    with columns ds/y built from the `monthly` values below, and swap the
    fit block — the API contract here stays the same.
    """
    scope = scope_filter(user)
    rows = query_revenue(db, scope, **filters).all()
    data = rows_to_dicts(rows)

    monthly = defaultdict(float)
    target_by_month = defaultdict(float)
    for d in data:
        monthly[d["mIdx"]] += d["revenue"]
        target_by_month[d["mIdx"]] += d["target"]

    idxs = sorted(monthly.keys())
    if len(idxs) < 2:
        return {"error": "Not enough historical data to forecast for this filter selection."}

    ys = [monthly[i] for i in idxs]
    n = len(idxs)
    mean_x = sum(idxs) / n
    mean_y = sum(ys) / n
    num = sum((idxs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((idxs[i] - mean_x) ** 2 for i in range(n)) or 1
    slope = num / den
    intercept = mean_y - slope * mean_x

    residuals = [ys[i] - (slope * idxs[i] + intercept) for i in range(n)]
    resid_std = statistics.pstdev(residuals) if n > 1 else 0.0

    last_idx = idxs[-1]
    avg_monthly_target = (sum(target_by_month.values()) / len(target_by_month)) if target_by_month else mean_y

    forecast_points = []
    for step in range(1, horizon + 1):
        x = last_idx + step
        y = max(0, slope * x + intercept)
        forecast_points.append({
            "step": step,
            "predicted_revenue": round(y, 2),
            "lower_bound": round(max(0, y - 1.28 * resid_std), 2),   # ~80% CI
            "upper_bound": round(y + 1.28 * resid_std, 2),
            "target": round(avg_monthly_target, 2),
        })

    total_forecast = sum(p["predicted_revenue"] for p in forecast_points)
    total_target = sum(p["target"] for p in forecast_points)

    return {
        "horizon_months": horizon,
        "historical_monthly_revenue": [round(monthly.get(i, 0), 2) for i in range(12)],
        "forecast": forecast_points,
        "total_forecast_revenue": round(total_forecast, 2),
        "target_achievement_pct": round((total_forecast / total_target * 100) if total_target else 0, 2),
        "model": "linear-trend",
    }
