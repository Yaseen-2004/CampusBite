from __future__ import annotations

import os
import secrets
import sqlite3
import string
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CAMPUSBITE_DB", str(BASE_DIR / "campusbite.db")))

app = FastAPI(title="CampusBite API", version="1.0.0", description="Campus cafeteria ordering and pickup API")
origins = os.getenv("CAMPUSBITE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins], allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Content-Type"])

SEED_MENU = [
    (1, "Paneer Tikka Bowl", "Smoky paneer, jeera rice, crunchy greens & mint yoghurt.", 149, "Meals", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=900&q=85", 1, 1, 1, 12),
    (2, "Classic Masala Dosa", "Golden crisp dosa, potato masala, sambar & chutneys.", 89, "Quick bites", "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=900&q=85", 1, 1, 1, 10),
    (3, "Grilled Veg Sandwich", "Toasted sourdough, garden vegetables & house spread.", 99, "Quick bites", "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=900&q=85", 1, 1, 0, 8),
    (4, "Campus Cold Coffee", "Chilled coffee, creamy milk and a little pick-me-up.", 79, "Beverages", "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=900&q=85", 1, 1, 1, 4),
    (5, "South Indian Meals", "A comforting daily special with rice, dal, sabzi & sides.", 129, "Meals", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=85", 1, 1, 0, 12),
    (6, "Chocolate Brownie", "A rich, fudgy chocolate square for your sweet break.", 69, "Desserts", "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=900&q=85", 1, 1, 0, 2),
    (7, "Crispy Chicken Wrap", "Spiced crispy chicken, fresh slaw and a creamy sauce.", 139, "Quick bites", "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=900&q=85", 0, 1, 0, 10),
    (8, "Fresh Lime Cooler", "Fresh lime, mint and sparkling refreshment.", 49, "Beverages", "https://images.unsplash.com/photo-1513558161293-cd1c3c2a4d5f?auto=format&fit=crop&w=900&q=85", 1, 1, 0, 3),
]

@contextmanager
def db():
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
            price INTEGER NOT NULL CHECK(price >= 0), category TEXT NOT NULL,
            image TEXT NOT NULL, vegetarian INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1, popular INTEGER NOT NULL DEFAULT 0,
            prep_minutes INTEGER NOT NULL DEFAULT 5
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, pickup_code TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL, campus_id TEXT NOT NULL,
            total INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'confirmed',
            payment_status TEXT NOT NULL DEFAULT 'demo_paid', payment_method TEXT NOT NULL DEFAULT 'UPI',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            food_id INTEGER NOT NULL, name TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0),
            price INTEGER NOT NULL CHECK(price >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_orders_pickup_code ON orders(pickup_code);
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
        """)
        count = conn.execute("SELECT COUNT(*) FROM menu").fetchone()[0]
        if count == 0:
            conn.executemany("INSERT INTO menu VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", SEED_MENU)

@app.on_event("startup")
def startup() -> None:
    init_db()


def menu_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "description": row["description"], "price": row["price"], "category": row["category"], "image": row["image"], "vegetarian": bool(row["vegetarian"]), "available": bool(row["available"]), "popular": bool(row["popular"]), "prep_minutes": row["prep_minutes"]}


def order_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    items = conn.execute("SELECT name, quantity, price FROM order_items WHERE order_id=? ORDER BY id", (row["id"],)).fetchall()
    return {"id": row["id"], "pickup_code": row["pickup_code"], "customer_name": row["customer_name"], "campus_id": row["campus_id"], "items": [dict(item) for item in items], "total": row["total"], "status": row["status"], "payment_status": row["payment_status"], "payment_method": row["payment_method"], "created_at": row["created_at"]}

class OrderItemIn(BaseModel):
    food_id: int
    quantity: int = Field(ge=1, le=30)

class CreateOrderIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    campus_id: str = Field(min_length=2, max_length=60)
    payment_method: Literal["UPI", "Card", "At counter"] = "UPI"
    items: list[OrderItemIn] = Field(min_length=1, max_length=30)

class AvailabilityUpdate(BaseModel):
    available: bool

class OrderStatusUpdate(BaseModel):
    status: Literal["confirmed", "preparing", "ready", "collected"]

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "CampusBite API", "database": "sqlite", "payment_mode": "demo_only"}

@app.get("/api/menu")
def get_menu() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM menu ORDER BY id").fetchall()
        return [menu_dict(row) for row in rows]

@app.post("/api/orders", status_code=201)
def create_order(payload: CreateOrderIn) -> dict:
    if not payload.customer_name.strip() or not payload.campus_id.strip():
        raise HTTPException(status_code=422, detail="Name and campus ID are required")
    with db() as conn:
        # Consolidate duplicate item IDs before validating stock and computing price server-side.
        quantities: dict[int, int] = {}
        for item in payload.items:
            quantities[item.food_id] = quantities.get(item.food_id, 0) + item.quantity
        if any(q > 30 for q in quantities.values()):
            raise HTTPException(status_code=422, detail="Maximum 30 of each item per order")
        resolved = []
        total = 0
        for food_id, quantity in quantities.items():
            food = conn.execute("SELECT * FROM menu WHERE id=?", (food_id,)).fetchone()
            if not food:
                raise HTTPException(status_code=404, detail=f"Menu item {food_id} was not found")
            if not food["available"]:
                raise HTTPException(status_code=409, detail=f"{food['name']} is sold out")
            resolved.append((food_id, food["name"], quantity, food["price"]))
            total += food["price"] * quantity
        code = "CB" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        for _ in range(5):
            if not conn.execute("SELECT 1 FROM orders WHERE pickup_code=?", (code,)).fetchone():
                break
            code = "CB" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        # Payment is deliberately a simulation. No real payment provider is called.
        payment_status = "pending_counter" if payload.payment_method == "At counter" else "demo_paid"
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute("INSERT INTO orders (pickup_code, customer_name, campus_id, total, status, payment_status, payment_method, created_at) VALUES (?, ?, ?, ?, 'confirmed', ?, ?, ?)", (code, payload.customer_name.strip(), payload.campus_id.strip(), total, payment_status, payload.payment_method, created_at))
        order_id = cursor.lastrowid
        conn.executemany("INSERT INTO order_items (order_id, food_id, name, quantity, price) VALUES (?, ?, ?, ?, ?)", [(order_id, *item) for item in resolved])
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return order_dict(conn, row)

@app.get("/api/orders/{pickup_code}")
def get_order(pickup_code: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE pickup_code=?", (pickup_code.upper(),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No order found for this pickup code")
        return order_dict(conn, row)

@app.get("/api/staff/orders")
def get_staff_orders() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 200").fetchall()
        return [order_dict(conn, row) for row in rows]

@app.patch("/api/staff/menu/{food_id}")
def update_availability(food_id: int, payload: AvailabilityUpdate) -> dict:
    with db() as conn:
        result = conn.execute("UPDATE menu SET available=? WHERE id=?", (int(payload.available), food_id))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Menu item not found")
        return menu_dict(conn.execute("SELECT * FROM menu WHERE id=?", (food_id,)).fetchone())

@app.patch("/api/staff/orders/{order_id}")
def update_order_status(order_id: int, payload: OrderStatusUpdate) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        allowed = {"confirmed": {"preparing"}, "preparing": {"ready"}, "ready": {"collected"}, "collected": set()}
        if payload.status != row["status"] and payload.status not in allowed[row["status"]]:
            raise HTTPException(status_code=409, detail=f"Cannot move order from {row['status']} to {payload.status}")
        conn.execute("UPDATE orders SET status=? WHERE id=?", (payload.status, order_id))
        return order_dict(conn, conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone())

@app.post("/api/staff/verify/{pickup_code}")
def verify_pickup(pickup_code: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE pickup_code=?", (pickup_code.upper(),)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Pickup code not found")
        if row["status"] == "collected":
            raise HTTPException(status_code=409, detail="This order has already been collected")
        if row["status"] != "ready":
            raise HTTPException(status_code=409, detail="Order must be marked ready before collection")
        conn.execute("UPDATE orders SET status='collected' WHERE id=?", (row["id"],))
        return order_dict(conn, conn.execute("SELECT * FROM orders WHERE id=?", (row["id"],)).fetchone())
