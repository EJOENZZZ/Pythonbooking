import os
import hashlib
import httpx
from dotenv import load_dotenv

load_dotenv()


def _headers():
    key = os.environ.get("SUPABASE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def _url(table):
    return os.environ.get("SUPABASE_URL", "") + f"/rest/v1/{table}"

def _get(table, params=None):
    r = httpx.get(_url(table), headers=_headers(), params=params)
    data = r.json()
    return data if isinstance(data, list) else []

def _post(table, data):
    r = httpx.post(_url(table), headers=_headers(), json=data)
    res = r.json()
    if isinstance(res, list) and res:
        return res[0]
    return res

def _patch(table, match_key, match_val, data):
    httpx.patch(_url(table), headers=_headers(), json=data,
                params={match_key: f"eq.{match_val}"})

def _delete(table, match_key, match_val):
    httpx.delete(_url(table), headers=_headers(),
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
    return _post("users", {
        "full_name": full_name,
        "email": email,
        "password": hash_password(password),
        "is_admin": False
    })

def login_user(email, password):
    user = get_user_by_email(email)
    if user and isinstance(user, dict) and user.get("password") == hash_password(password):
        return user
    return None


# ── Trips ─────────────────────────────────────────────────────────────────────
def get_all_trips():
    return _get("trips", {"order": "departure.asc"})

def get_trip(trip_id):
    res = _get("trips", {"id": f"eq.{trip_id}", "limit": 1})
    return res[0] if res else None

def search_trips(trip_type, origin, dest, date):
    params = {"order": "departure.asc"}
    if trip_type:
        params["type"] = f"eq.{trip_type}"
    if origin:
        params["from_city"] = f"ilike.{origin}"
    if dest:
        params["to_city"] = f"ilike.{dest}"
    if date:
        params["departure"] = f"gte.{date}T00:00:00"
    results = _get("trips", params)
    return [t for t in results if t.get("seats", 0) > 0]

def decrement_seats(trip_id, qty):
    trip = get_trip(trip_id)
    if trip:
        _patch("trips", "id", trip_id, {"seats": trip["seats"] - qty})

def increment_seats(trip_id, qty):
    trip = get_trip(trip_id)
    if trip:
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
    return _post("bookings", data)

def cancel_booking(booking_id):
    _delete("bookings", "id", booking_id)
