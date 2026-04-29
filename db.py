import os
import hashlib
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv

if os.environ.get("VERCEL") is None:
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

def delete_user(user_id):
    _delete("users", "id", user_id)


# ── Trips ─────────────────────────────────────────────────────────────────────
def _advance_trip(trip):
    """If departure is in the past, advance it to the next future date keeping the same time."""
    if not trip or not trip.get("departure"):
        return trip
    try:
        dep = datetime.fromisoformat(trip["departure"])
        arr = datetime.fromisoformat(trip["arrival"]) if trip.get("arrival") else None
        now = datetime.now()
        if dep < now:
            duration = (arr - dep) if arr else timedelta(hours=1)
            # Advance to today with same time; if still past, use tomorrow
            new_dep = dep.replace(year=now.year, month=now.month, day=now.day)
            if new_dep < now:
                new_dep += timedelta(days=1)
            new_arr = new_dep + duration if arr else None
            trip = dict(trip)
            trip["departure"] = new_dep.strftime("%Y-%m-%dT%H:%M:%S")
            if new_arr:
                trip["arrival"] = new_arr.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        pass
    return trip

def get_all_trips():
    trips = _get("trips", {"order": "departure.asc"})
    return [_advance_trip(t) for t in trips]

def get_trip(trip_id):
    res = _get("trips", {"id": f"eq.{trip_id}", "limit": 1})
    return _advance_trip(res[0]) if res else None

def search_trips(trip_type, origin, dest, date):
    params = {"order": "departure.asc"}
    if trip_type:
        params["type"] = f"eq.{trip_type}"
    if origin:
        params["from_city"] = f"ilike.{origin}"
    if dest:
        params["to_city"] = f"ilike.{dest}"
    results = _get("trips", params)
    trips = [_advance_trip(t) for t in results if t.get("seats", 0) > 0]
    if date:
        trips = [t for t in trips if t["departure"][:10] >= date]
    return trips

def create_trip(data):
    return _post("trips", data)

def update_trip(trip_id, data):
    _patch("trips", "id", trip_id, data)

def delete_trip(trip_id):
    _delete("trips", "id", trip_id)

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
