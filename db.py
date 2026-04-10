import os
import hashlib
import httpx
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL", "") + "/rest/v1"
KEY = os.environ.get("SUPABASE_KEY", "")
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _get(table, params=None):
    r = httpx.get(f"{URL}/{table}", headers=HEADERS, params=params)
    return r.json()

def _post(table, data):
    r = httpx.post(f"{URL}/{table}", headers=HEADERS, json=data)
    return r.json()

def _patch(table, match_key, match_val, data):
    httpx.patch(f"{URL}/{table}", headers=HEADERS, json=data,
                params={match_key: f"eq.{match_val}"})

def _delete(table, match_key, match_val):
    httpx.delete(f"{URL}/{table}", headers=HEADERS,
                 params={match_key: f"eq.{match_val}"})


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ── Users ─────────────────────────────────────────────────────────────────────
def get_user_by_email(email):
    res = _get("users", {"email": f"eq.{email}", "limit": 1})
    return res[0] if res else None

def get_all_users():
    return _get("users", {"order": "created_at.desc"})

def register_user(full_name, email, password):
    res = _post("users", {"full_name": full_name, "email": email, "password": hash_password(password), "is_admin": False})
    return res[0] if isinstance(res, list) else res

def login_user(email, password):
    user = get_user_by_email(email)
    if user and user["password"] == hash_password(password):
        return user
    return None


# ── Trips ─────────────────────────────────────────────────────────────────────
def get_all_trips():
    return _get("trips", {"order": "departure.asc"})

def get_trip(trip_id):
    res = _get("trips", {"id": f"eq.{trip_id}", "limit": 1})
    return res[0] if res else None

def search_trips(trip_type, origin, dest, date):
    params = {"type": f"eq.{trip_type}", "seats": "gt.0", "order": "departure.asc"}
    if origin:
        params["from_city"] = f"ilike.{origin}"
    if dest:
        params["to_city"] = f"ilike.{dest}"
    if date:
        params["departure"] = f"gte.{date}"
    return _get("trips", params)

def decrement_seats(trip_id, qty):
    trip = get_trip(trip_id)
    _patch("trips", "id", trip_id, {"seats": trip["seats"] - qty})

def increment_seats(trip_id, qty):
    trip = get_trip(trip_id)
    _patch("trips", "id", trip_id, {"seats": trip["seats"] + qty})


# ── Bookings ──────────────────────────────────────────────────────────────────
def get_all_bookings():
    return _get("bookings", {"order": "booked_at.desc"})

def get_user_bookings(user_id):
    return _get("bookings", {"user_id": f"eq.{user_id}", "order": "booked_at.desc"})

def get_booking(booking_id):
    res = _get("bookings", {"id": f"eq.{booking_id}", "limit": 1})
    return res[0] if res else None

def create_booking(data):
    res = _post("bookings", data)
    return res[0] if isinstance(res, list) else res

def cancel_booking(booking_id):
    _delete("bookings", "id", booking_id)
