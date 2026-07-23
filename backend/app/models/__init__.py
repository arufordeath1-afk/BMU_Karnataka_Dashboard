from app.database import Base
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # Circle | Region | Division | Office
    region = Column(String(64), nullable=True)
    division = Column(String(64), nullable=True)
    office = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    divisions = relationship("Division", back_populates="region_rel")


class Division(Base):
    __tablename__ = "divisions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"))
    region_rel = relationship("Region", back_populates="divisions")
    offices = relationship("Office", back_populates="division_rel")


class Office(Base):
    __tablename__ = "offices"
    office_id = Column(Integer, primary_key=True, index=True)
    office_name = Column(String(100), nullable=False)
    division_id = Column(Integer, ForeignKey("divisions.id"))
    office_type = Column(String(20), default="SO")  # HO / GPO / SO
    division_rel = relationship("Division", back_populates="offices")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(64), unique=True, nullable=False)
    color_hex = Column(String(8), nullable=True)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    customer_code = Column(String(32), unique=True, index=True, nullable=False)
    customer_name = Column(String(150), nullable=False, index=True)
    gst_number = Column(String(20), nullable=True)
    mobile = Column(String(15), nullable=True)
    email = Column(String(120), nullable=True)
    division = Column(String(64), index=True)
    region = Column(String(64), index=True)
    office = Column(String(100), index=True)
    category = Column(String(20), default="Corporate")  # Corporate | Government
    created_date = Column(DateTime, default=datetime.utcnow)

    revenues = relationship("Revenue", back_populates="customer_rel")


class Revenue(Base):
    __tablename__ = "revenue"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    month = Column(String(3), index=True)          # Apr..Mar
    month_index = Column(Integer, index=True)       # 0..11 (Apr=0)
    quarter = Column(String(2), index=True)          # Q1..Q4
    financial_year = Column(String(10), index=True)  # FY 2025-26
    articles = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)   # in lakh INR, matches frontend units
    target = Column(Float, default=0.0)
    booking_date = Column(DateTime, default=datetime.utcnow)

    customer_rel = relationship("Customer", back_populates="revenues")
    product_rel = relationship("Product")


class UploadBatch(Base):
    __tablename__ = "upload_batches"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    uploaded_by = Column(String(64))
    rows_uploaded = Column(Integer, default=0)
    rows_failed = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    inserted_rows = Column(Integer, default=0)
    errors_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64))
    action = Column(String(255))
    endpoint = Column(String(255))
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
