from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = None  # optional hint, actual role comes from stored user


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    scope: Dict[str, Optional[str]]


class CustomerOut(BaseModel):
    id: int
    customer_code: str
    customer_name: str
    gst_number: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    division: Optional[str] = None
    region: Optional[str] = None
    office: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


class RevenueRow(BaseModel):
    month: str
    mIdx: int
    quarter: str
    customer: str
    code: str
    division: str
    region: str
    office: str
    category: str
    product: str
    revenue: float
    articles: int
    target: float


class ExecutiveSummary(BaseModel):
    total_revenue: float
    total_customers: int
    active_customers: int
    new_customers: int
    lost_customers: int
    growth_pct: float
    achievement_pct: float
    top10: List[Dict[str, Any]]
    product_share: Dict[str, float]


class UploadResult(BaseModel):
    rows_uploaded: int
    rows_failed: int
    duplicate_rows: int
    inserted_rows: int
    validation_errors: List[str]
