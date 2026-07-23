import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, dashboard, customers, products, geo, forecast, insights, upload, reports

app = FastAPI(
    title="India Post — Karnataka Circle Revenue Intelligence API",
    version="1.0.0",
    description="Backend for the Karnataka Circle Revenue Intelligence Dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimpleRateLimiter(BaseHTTPMiddleware):
    """Minimal in-memory rate limiter (per-process). Swap for a Redis-backed
    limiter (e.g. slowapi + redis) behind a load balancer in production."""
    _hits: dict = {}
    LIMIT = 300
    WINDOW = 60

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._hits.setdefault(ip, [])
        self._hits[ip] = [t for t in bucket if now - t < self.WINDOW]
        if len(self._hits[ip]) >= self.LIMIT:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        self._hits[ip].append(now)
        return await call_next(request)


app.add_middleware(SimpleRateLimiter)

Base.metadata.create_all(bind=engine)  # no-op once seed_data has run; safe on boot

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(geo.router)
app.include_router(forecast.router)
app.include_router(insights.router)
app.include_router(upload.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
