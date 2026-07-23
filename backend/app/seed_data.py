"""
Seeds the database with data shaped exactly like the dashboard's original
client-side mock generator (same divisions, products, corporate/govt
customer names, month range) so every chart on the frontend gets numbers
in the ranges it was designed for.

Run with:  python -m app.seed_data
"""
import random
from datetime import datetime, timedelta

from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password

random.seed(42)

MONTHS = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
QUARTER_OF = {"Apr": "Q1", "May": "Q1", "Jun": "Q1", "Jul": "Q2", "Aug": "Q2", "Sep": "Q2",
              "Oct": "Q3", "Nov": "Q3", "Dec": "Q3", "Jan": "Q4", "Feb": "Q4", "Mar": "Q4"}
FY = "FY 2025-26"

PRODUCTS = [
    ("Speed Post", "#B01E28"), ("Business Parcel", "#F0A500"), ("Express Parcel", "#2E7D4F"),
    ("Logistics Post", "#3E6FB0"), ("Registered Post", "#8A5CB0"), ("Parcel", "#C1666B"),
    ("EMS", "#4FA5A0"), ("Other Products", "#9C7D2E"),
]

DIVISIONS = [
    {"name": "Bengaluru City", "region": "Bengaluru", "offices": ["Bengaluru GPO", "MG Road HO", "Koramangala SO", "Whitefield SO"]},
    {"name": "Bengaluru Rural", "region": "Bengaluru", "offices": ["Devanahalli SO", "Doddaballapur HO", "Hosakote SO"]},
    {"name": "Mysuru", "region": "Mysuru", "offices": ["Mysuru HO", "Nazarbad SO", "Hebbal SO"]},
    {"name": "Mangaluru", "region": "Coastal", "offices": ["Mangaluru HO", "Kadri SO", "Surathkal SO"]},
    {"name": "Hubballi", "region": "North Karnataka", "offices": ["Hubballi HO", "Dharwad SO", "Gokul Road SO"]},
    {"name": "Belagavi", "region": "North Karnataka", "offices": ["Belagavi HO", "Tilakwadi SO", "Camp SO"]},
    {"name": "Kalaburagi", "region": "North Karnataka", "offices": ["Kalaburagi HO", "Jewargi Road SO"]},
    {"name": "Shivamogga", "region": "Malnad", "offices": ["Shivamogga HO", "Bhadravathi SO"]},
]

CORP_NAMES = ["Karnataka Bank Ltd", "Infosys BPM", "Wipro Enterprises", "Biocon Ltd", "TVS Motor Co",
    "Titan Company", "MTR Foods", "Coffee Day Enterprises", "Bosch Ltd", "ABB India", "Toyota Kirloskar",
    "Ashok Leyland", "Jubilant FoodWorks", "Flipkart Internet", "Amazon Seller Services", "Myntra Designs",
    "Meesho Inc", "BigBasket Supply", "Zomato Logistics", "Practo Technologies", "Manipal Hospitals",
    "Narayana Health", "Apollo Diagnostics Ktka", "Reliance Retail Ktka", "Tata Elxsi", "L&T Technology",
    "Mindtree Digital", "HAL Employees Union", "BEL Corporate Office", "ISRO Satellite Centre",
    "KSRTC Head Office", "BESCOM Divisional", "BWSSB Head Office", "Canara Bank HO",
    "Corporation Bank Regional", "Vijaya Bank Zonal", "Syndicate Bank Circle", "LIC Divisional Office",
    "New India Assurance", "Karnataka State Financial Corp", "KIADB Regional", "Deputy Commissioner Office",
    "District Treasury", "Municipal Corporation", "Karnataka Milk Federation", "Coffee Board of India",
    "Silk Board Karnataka", "Spices Board Regional", "Karnataka Soaps & Detergents",
    "MysoreSales International", "KSIC Silk Weaving"]

GOV = {"HAL Employees Union", "BEL Corporate Office", "ISRO Satellite Centre", "KSRTC Head Office",
    "BESCOM Divisional", "BWSSB Head Office", "LIC Divisional Office", "Karnataka State Financial Corp",
    "KIADB Regional", "Deputy Commissioner Office", "District Treasury", "Municipal Corporation",
    "Karnataka Milk Federation", "Coffee Board of India", "Silk Board Karnataka", "Spices Board Regional",
    "Karnataka Soaps & Detergents", "MysoreSales International", "KSIC Silk Weaving"}

DEMO_USERS = [
    ("karnataka.circle.rm", "circle123", "Circle", None, None, None),
    ("bengaluru.region.rm", "region123", "Region", "Bengaluru", None, None),
    ("mysuru.division.rm", "division123", "Division", "Mysuru", "Mysuru", None),
    ("mysuru.ho.user", "office123", "Office", "Mysuru", "Mysuru", "Mysuru HO"),
]


def run(force: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        has_data = db.query(models.Customer).first() is not None
        if has_data and not force:
            print("Database already has data — skipping seed (use --force to wipe and reseed).")
            return
        if has_data and force:
            db.close()
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
        # Regions / Divisions / Offices
        region_objs = {}
        for d in DIVISIONS:
            if d["region"] not in region_objs:
                region_objs[d["region"]] = models.Region(name=d["region"])
                db.add(region_objs[d["region"]])
        db.flush()

        division_objs = {}
        for d in DIVISIONS:
            div = models.Division(name=d["name"], region_id=region_objs[d["region"]].id)
            db.add(div)
            db.flush()
            division_objs[d["name"]] = div
            for i, office_name in enumerate(d["offices"]):
                otype = "HO" if "HO" in office_name or "GPO" in office_name else "SO"
                db.add(models.Office(office_name=office_name, division_id=div.id, office_type=otype))

        # Products
        product_objs = {}
        for name, color in PRODUCTS:
            p = models.Product(product_name=name, color_hex=color)
            db.add(p)
            db.flush()
            product_objs[name] = p

        # Users
        for username, pw, role, region, division, office in DEMO_USERS:
            db.add(models.User(
                username=username, password_hash=hash_password(pw), role=role,
                region=region, division=division, office=office,
            ))

        db.commit()

        # Customers + Revenue (mirrors the frontend's original random-walk generator)
        customers = []
        for i, name in enumerate(CORP_NAMES):
            d = random.choice(DIVISIONS)
            office = random.choice(d["offices"])
            base = 2 + random.random() * 38
            growth_bias = (random.random() - 0.4) * 0.12
            weights = [0.4 + random.random() for _ in PRODUCTS]
            cust = models.Customer(
                customer_code=f"KTK{10234 + i}",
                customer_name=name,
                gst_number=f"29{str(1000 + i * 37).zfill(5)}AZP{i % 9}Z{i % 9}",
                mobile=f"9{str(700000000 + (i * 913571) % 99999999).zfill(9)[:9]}",
                email=name.lower().replace(' ', '.').replace('&', 'and') + "@corp.example.in",
                division=d["name"], region=d["region"], office=office,
                category="Government" if name in GOV else "Corporate",
            )
            db.add(cust)
            db.flush()
            customers.append((cust, base, growth_bias, weights, d))

        base_date = datetime(2025, 4, 1)
        for cust, base, growth_bias, weights, d in customers:
            level = base
            total_w = sum(weights)
            for mi, month in enumerate(MONTHS):
                level = max(0.5, level * (1 + growth_bias + (random.random() - 0.5) * 0.10))
                for pi, (pname, _) in enumerate(PRODUCTS):
                    share = weights[pi] / total_w
                    rev = round(level * share * (0.85 + random.random() * 0.3), 2)
                    if rev <= 0.05:
                        continue
                    articles = round(rev * (18 + random.random() * 22))
                    target = round(rev * (0.9 + random.random() * 0.25), 2)
                    booking_date = base_date + timedelta(days=30 * mi + random.randint(0, 27))
                    db.add(models.Revenue(
                        customer_id=cust.id, product_id=product_objs[pname].id,
                        month=month, month_index=mi, quarter=QUARTER_OF[month], financial_year=FY,
                        articles=articles, revenue=rev, target=target, booking_date=booking_date,
                    ))
        db.commit()
        print(f"Seeded {len(customers)} customers across {len(DIVISIONS)} divisions, "
              f"{len(PRODUCTS)} products, {len(MONTHS)} months.")
        print("Demo logins (username / password / role):")
        for u in DEMO_USERS:
            print(f"  {u[0]} / {u[1]} / {u[2]}")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    run(force="--force" in sys.argv)
