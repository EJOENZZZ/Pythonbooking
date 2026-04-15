import os
import uuid
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "transport_booking_key")


# ── Auth guard ────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access only.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email", "").strip()
        password  = request.form.get("password", "").strip()
        confirm   = request.form.get("confirm", "").strip()

        if not full_name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        if db.get_user_by_email(email):
            flash("Email already registered.", "danger")
            return render_template("signup.html")

        try:
            user = db.register_user(full_name, email, password)
            if not user or not isinstance(user, dict) or "id" not in user:
                flash(f"Registration failed: {user}", "danger")
                return render_template("signup.html")
            session["user_id"]   = user["id"]
            session["user_name"] = user["full_name"]
            flash(f"Welcome, {user['full_name']}!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return render_template("signup.html")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        user = db.login_user(email, password)
        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["full_name"]
            session["is_admin"]  = user.get("is_admin", False)
            flash(f"Welcome back, {user['full_name']}!", "success")
            if user.get("is_admin"):
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ── Main Routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    try:
        trips = db.get_all_trips()
        if not isinstance(trips, list):
            raise Exception(f"Supabase error: {trips}")
        origins = sorted(set(t["from_city"] for t in trips))
        dests   = sorted(set(t["to_city"]   for t in trips))
        flights = [t for t in trips if t["type"] == "plane"]
        ferries = [t for t in trips if t["type"] == "ferry"]
    except Exception as e:
        app.logger.error(f"DB error on index: {e}")
        origins, dests, flights, ferries = [], [], [], []
        flash(str(e), "danger")
    return render_template("index.html", origins=origins, destinations=dests,
                           flights=flights, ferries=ferries)


@app.route("/search")
def search():
    trip_type  = request.args.get("type", "plane")
    origin     = request.args.get("from", "").strip()
    dest       = request.args.get("to",   "").strip()
    date       = request.args.get("date", "").strip()
    passengers = request.args.get("passengers", "1").strip()

    results = db.search_trips(trip_type, origin, dest, date)
    app.logger.info(f"Search: type={trip_type} from={origin} to={dest} date={date} results={len(results)}")
    return render_template("results.html", results=results, trip_type=trip_type,
                           origin=origin, dest=dest, date=date, passengers=passengers)


@app.route("/book/<trip_id>", methods=["GET", "POST"])
@login_required
def book(trip_id):
    trip = db.get_trip(trip_id)
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

        booking_data = {
            "id":             str(uuid.uuid4())[:8].upper(),
            "trip_id":        trip_id,
            "user_id":        session["user_id"],
            "type":           trip["type"],
            "from_city":      trip["from_city"],
            "to_city":        trip["to_city"],
            "departure":      trip["departure"],
            "arrival":        trip["arrival"],
            "operator":       trip["operator"],
            "passenger_name": name,
            "email":          email,
            "phone":          phone,
            "passengers":     passengers,
            "total":          passengers * trip["price"],
            "booked_at":      datetime.now().isoformat(),
            "status":         "Confirmed",
        }
        booking = db.create_booking(booking_data)
        db.decrement_seats(trip_id, passengers)
        session["last_booking_id"] = booking["id"]
        return redirect(url_for("confirm"))

    return render_template("book.html", trip=trip, passengers=passengers)


@app.route("/confirm")
@login_required
def confirm():
    booking_id = session.get("last_booking_id")
    booking = db.get_booking(booking_id) if booking_id else None
    if not booking:
        return redirect(url_for("index"))
    return render_template("confirm.html", booking=booking)


@app.route("/my-bookings")
@login_required
def my_bookings():
    bookings = db.get_user_bookings(session["user_id"])
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/cancel/<booking_id>", methods=["POST"])
@login_required
def cancel(booking_id):
    booking = db.get_booking(booking_id)
    if booking and booking["user_id"] == session["user_id"]:
        db.increment_seats(booking["trip_id"], booking["passengers"])
        db.cancel_booking(booking_id)
        flash(f"Booking #{booking_id} has been cancelled.", "success")
    else:
        flash("Booking not found.", "danger")
    return redirect(url_for("my_bookings"))


# ── Error Handlers ───────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, msg="Page not found."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, msg=str(e)), 500

@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {e}")
    return render_template("error.html", code=500, msg=str(e)), 500


# ── Admin Routes ──────────────────────────────────────────────────────────────
@app.route("/admin")
@admin_required
def admin_dashboard():
    bookings = db.get_all_bookings()
    users    = db.get_all_users()
    trips    = db.get_all_trips()
    return render_template("admin.html", bookings=bookings, users=users, trips=trips)

@app.route("/admin/cancel/<booking_id>", methods=["POST"])
@admin_required
def admin_cancel(booking_id):
    booking = db.get_booking(booking_id)
    if booking:
        db.increment_seats(booking["trip_id"], booking["passengers"])
        db.cancel_booking(booking_id)
        flash(f"Booking #{booking_id} cancelled.", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
