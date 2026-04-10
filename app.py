from flask import Flask, render_template, request, redirect, url_for, session, flash
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "transport_booking_key"

# ── Data Store ────────────────────────────────────────────────────────────────
flights = [
    {"id": "F1", "type": "plane", "from": "Manila",  "to": "Cebu",      "departure": "2025-08-10 06:00", "arrival": "2025-08-10 07:10", "airline": "AirFast",   "price": 2500.00, "seats": 120},
    {"id": "F2", "type": "plane", "from": "Manila",  "to": "Davao",     "departure": "2025-08-10 08:00", "arrival": "2025-08-10 09:30", "airline": "SkyLine",   "price": 3200.00, "seats": 100},
    {"id": "F3", "type": "plane", "from": "Cebu",    "to": "Manila",    "departure": "2025-08-11 14:00", "arrival": "2025-08-11 15:10", "airline": "AirFast",   "price": 2600.00, "seats": 90},
    {"id": "F4", "type": "plane", "from": "Davao",   "to": "Manila",    "departure": "2025-08-12 10:00", "arrival": "2025-08-12 11:30", "airline": "BlueBird",  "price": 3100.00, "seats": 80},
    {"id": "V1", "type": "ferry", "from": "Batangas","to": "Calapan",   "departure": "2025-08-10 07:00", "arrival": "2025-08-10 09:00", "airline": "OceanJet",  "price": 350.00,  "seats": 200},
    {"id": "V2", "type": "ferry", "from": "Cebu",    "to": "Bohol",     "departure": "2025-08-10 08:30", "arrival": "2025-08-10 09:30", "airline": "SuperCat",  "price": 280.00,  "seats": 150},
    {"id": "V3", "type": "ferry", "from": "Manila",  "to": "Batangas",  "departure": "2025-08-11 06:00", "arrival": "2025-08-11 09:00", "airline": "2GO Ferry", "price": 500.00,  "seats": 180},
    {"id": "V4", "type": "ferry", "from": "Bohol",   "to": "Cebu",      "departure": "2025-08-12 15:00", "arrival": "2025-08-12 16:00", "airline": "OceanJet",  "price": 290.00,  "seats": 160},
]

bookings = []


def get_trip(trip_id):
    return next((t for t in flights if t["id"] == trip_id), None)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    origins      = sorted(set(t["from"] for t in flights))
    destinations = sorted(set(t["to"]   for t in flights))
    return render_template("index.html", origins=origins, destinations=destinations)


@app.route("/search")
def search():
    trip_type = request.args.get("type", "plane")
    origin    = request.args.get("from", "").strip()
    dest      = request.args.get("to",   "").strip()
    date      = request.args.get("date", "").strip()
    passengers = request.args.get("passengers", "1").strip()

    results = [
        t for t in flights
        if t["type"] == trip_type
        and (not origin or t["from"].lower() == origin.lower())
        and (not dest   or t["to"].lower()   == dest.lower())
        and (not date   or t["departure"].startswith(date))
        and t["seats"] > 0
    ]
    return render_template("results.html", results=results, trip_type=trip_type,
                           origin=origin, dest=dest, date=date, passengers=passengers)


@app.route("/book/<trip_id>", methods=["GET", "POST"])
def book(trip_id):
    trip = get_trip(trip_id)
    if not trip:
        flash("Trip not found.", "danger")
        return redirect(url_for("index"))

    passengers = int(request.args.get("passengers", 1))

    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        email      = request.form.get("email", "").strip()
        phone      = request.form.get("phone", "").strip()
        passengers = int(request.form.get("passengers", 1))

        if not name or not email or not phone:
            flash("Please fill in all required fields.", "danger")
            return render_template("book.html", trip=trip, passengers=passengers)

        if passengers > trip["seats"]:
            flash(f"Only {trip['seats']} seats available.", "warning")
            return render_template("book.html", trip=trip, passengers=passengers)

        booking = {
            "id":         str(uuid.uuid4())[:8].upper(),
            "trip_id":    trip_id,
            "type":       trip["type"],
            "from":       trip["from"],
            "to":         trip["to"],
            "departure":  trip["departure"],
            "arrival":    trip["arrival"],
            "operator":   trip["airline"],
            "name":       name,
            "email":      email,
            "phone":      phone,
            "passengers": passengers,
            "total":      passengers * trip["price"],
            "booked_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status":     "Confirmed",
        }
        bookings.append(booking)
        trip["seats"] -= passengers
        session["last_booking_id"] = booking["id"]
        return redirect(url_for("confirm"))

    return render_template("book.html", trip=trip, passengers=passengers)


@app.route("/confirm")
def confirm():
    booking_id = session.get("last_booking_id")
    booking = next((b for b in bookings if b["id"] == booking_id), None)
    if not booking:
        return redirect(url_for("index"))
    return render_template("confirm.html", booking=booking)


@app.route("/my-bookings")
def my_bookings():
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/cancel/<booking_id>", methods=["POST"])
def cancel(booking_id):
    global bookings
    booking = next((b for b in bookings if b["id"] == booking_id), None)
    if booking:
        trip = get_trip(booking["trip_id"])
        if trip:
            trip["seats"] += booking["passengers"]
        bookings = [b for b in bookings if b["id"] != booking_id]
        flash(f"Booking #{booking_id} has been cancelled.", "success")
    else:
        flash("Booking not found.", "danger")
    return redirect(url_for("my_bookings"))


if __name__ == "__main__":
    app.run(debug=False)
