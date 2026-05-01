import os
import uuid
import random
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from dotenv import load_dotenv
import db

CITIES = sorted([
    "Manila", "Cebu", "Davao", "Iloilo", "Bacolod",
    "Batangas", "Calapan", "Dumaguete", "Cagayan de Oro", "Zamboanga"
])

if os.environ.get("VERCEL") is None:
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "transport_booking_key")

app.config["MAIL_SERVER"]   = "smtp.gmail.com"
app.config["MAIL_PORT"]     = 587
app.config["MAIL_USE_TLS"]  = True
app.config["MAIL_USERNAME"] = "ellajoylocahinherra5@gmail.com"
app.config["MAIL_PASSWORD"] = "uvzbczopvdymfkam"
app.config["MAIL_DEFAULT_SENDER"] = "ellajoylocahinherra5@gmail.com"
mail = Mail(app)


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
        phone     = request.form.get("phone", "").strip()

        if not full_name or not email or not password or not phone:
            flash("All fields are required.", "danger")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        if db.get_user_by_email(email):
            flash("Email already registered.", "danger")
            return render_template("signup.html")

        code = str(random.randint(100000, 999999))
        db.save_reset_code(email, code)
        try:
            msg = Message("TravelBook — Email Verification Code",
                          sender="ellajoylocahinherra5@gmail.com",
                          recipients=[email])
            msg.body = f"Your verification code is: {code}\n\nEnter this code to complete your registration."
            mail.send(msg)
            session["pending_signup"] = {
                "full_name": full_name,
                "email":     email,
                "password":  password,
                "phone":     phone
            }
            flash("A verification code has been sent to your email.", "info")
            return redirect(url_for("verify_signup", email=email))
        except Exception as e:
            flash(f"Failed to send verification email: {str(e)}", "danger")
    return render_template("signup.html")


@app.route("/verify-signup", methods=["GET", "POST"])
def verify_signup():
    email = request.args.get("email") or request.form.get("email", "")
    if not email or "pending_signup" not in session:
        return redirect(url_for("signup"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        record = db.get_reset_code(email)
        if record and record["code"] == code:
            data = session.pop("pending_signup")
            db.delete_reset_code(email)
            try:
                user = db.register_user(data["full_name"], data["email"], data["password"], data.get("phone", ""))
                if not user or not isinstance(user, dict) or "id" not in user:
                    flash(f"Registration failed: {user}", "danger")
                    return redirect(url_for("signup"))
                session["user_id"]    = user["id"]
                session["user_name"]  = user["full_name"]
                session["user_email"] = data["email"]
                session["user_phone"] = data.get("phone", "")
                flash(f"Welcome, {user['full_name']}! Your account has been verified successfully.", "success")
                return redirect(url_for("index"))
            except Exception as e:
                flash(f"Error: {str(e)}", "danger")
                return redirect(url_for("signup"))
        flash("Invalid code. Please try again.", "danger")
    return render_template("verify_signup.html", email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role     = request.form.get("role", "user")
        user = db.login_user(email, password)
        if user:
            if role == "admin" and not user.get("is_admin"):
                flash("This account is not an admin.", "danger")
                return render_template("login.html")
            if role == "user" and user.get("is_admin"):
                flash("Please use the Admin tab to log in as admin.", "warning")
                return render_template("login.html")
            session["user_id"]    = user["id"]
            session["user_name"]  = user["full_name"]
            session["user_email"] = email
            session["user_phone"] = user.get("phone", "")
            session["is_admin"]   = user.get("is_admin", False)
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
        dests   = sorted(set(t["to_city"] for t in trips))
        all_cities = sorted(set(origins + dests))
        flights = [t for t in trips if t["type"] == "plane"]
        ferries = [t for t in trips if t["type"] == "ferry"]
        # attach available dates to each trip
        for t in flights + ferries:
            t["available_dates"] = db.get_trip_dates(t["id"])
    except Exception as e:
        app.logger.error(f"DB error on index: {e}")
        origins, dests, all_cities, flights, ferries = [], [], [], [], []
        flash(str(e), "danger")
    return render_template("index.html", origins=CITIES, destinations=CITIES,
                           flights=flights, ferries=ferries)


@app.route("/search")
def search():
    trip_type  = request.args.get("type", "").strip()
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
    available_dates = db.get_trip_dates(trip_id)

    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        email        = request.form.get("email", "").strip()
        phone        = request.form.get("phone", "").strip()
        passengers   = int(request.form.get("passengers", 1))
        travel_date  = request.form.get("travel_date", trip["departure"][:10])

        if not name or not email or not phone:
            flash("Please fill in all required fields.", "danger")
            return render_template("book.html", trip=trip, passengers=passengers, available_dates=available_dates)

        if passengers > trip["seats"]:
            flash(f"Only {trip['seats']} seats available.", "warning")
            return render_template("book.html", trip=trip, passengers=passengers, available_dates=available_dates)

        dep_time = trip["departure"][11:] if len(trip["departure"]) > 10 else "00:00:00"
        arr_time = trip["arrival"][11:]   if len(trip["arrival"]) > 10   else "00:00:00"

        booking_data = {
            "id":             str(uuid.uuid4())[:8].upper(),
            "trip_id":        trip_id,
            "user_id":        session["user_id"],
            "type":           trip["type"],
            "from_city":      trip["from_city"],
            "to_city":        trip["to_city"],
            "departure":      f"{travel_date}T{dep_time}",
            "arrival":        f"{travel_date}T{arr_time}",
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
        session["last_booking_total"] = booking_data["total"]
        return redirect(url_for("gcash_payment"))

    return render_template("book.html", trip=trip, passengers=passengers, available_dates=available_dates)


@app.route("/gcash", methods=["GET", "POST"])
@login_required
def gcash_payment():
    booking_id = session.get("last_booking_id")
    total      = session.get("last_booking_total", 0)
    if not booking_id:
        return redirect(url_for("index"))
    if request.method == "POST":
        return redirect(url_for("confirm"))
    return render_template("gcash.html", total=total, booking_id=booking_id)


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
    if booking and booking["user_id"] == session["user_id"] and booking["status"] == "Confirmed":
        reason = request.form.get("reason", "").strip()
        if not reason:
            flash("Please provide a reason for cancellation.", "danger")
            return redirect(url_for("my_bookings"))
        db.request_cancellation(booking_id, reason)
        flash(f"Cancellation request for booking #{booking_id} has been submitted. Please wait for admin approval.", "info")
    else:
        flash("Booking not found.", "danger")
    return redirect(url_for("my_bookings"))


# ── Forgot Password ──────────────────────────────────────────────────────────
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = db.get_user_by_email(email)
        if not user:
            flash("No account found with that email.", "danger")
            return render_template("forgot_password.html")
        code = str(random.randint(100000, 999999))
        db.save_reset_code(email, code)
        try:
            msg = Message("TravelBook — Password Reset Code",
                          sender="ellajoylocahinherra5@gmail.com",
                          recipients=[email])
            msg.body = f"Your password reset code is: {code}\n\nEnter this code to reset your password."
            mail.send(msg)
            flash("A reset code has been sent to your email.", "success")
            return redirect(url_for("verify_code", email=email))
        except Exception as e:
            flash(f"Failed to send email: {str(e)}", "danger")
    return render_template("forgot_password.html")


@app.route("/verify-code", methods=["GET", "POST"])
def verify_code():
    email = request.args.get("email") or request.form.get("email", "")
    if not email:
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        record = db.get_reset_code(email)
        if record and record["code"] == code:
            session["reset_verified"] = True
            session["reset_email"]    = email
            return redirect(url_for("reset_password"))
        flash("Invalid code. Please try again.", "danger")
    return render_template("verify_code.html", email=email)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if not session.get("reset_verified"):
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()
        if not password:
            flash("Password cannot be empty.", "danger")
            return render_template("reset_password.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")
        email = session.pop("reset_email", None)
        session.pop("reset_verified", None)
        db.update_password(email, password)
        db.delete_reset_code(email)
        flash("Password updated! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html")


# ── Profile ──────────────────────────────────────────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = db.get_user(session["user_id"])
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone     = request.form.get("phone", "").strip()
        db.update_user_profile(session["user_id"], {"full_name": full_name, "phone": phone})
        session["user_name"]  = full_name
        session["user_phone"] = phone
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.route("/profile/change-email", methods=["POST"])
@login_required
def change_email_request():
    new_email = request.form.get("new_email", "").strip()
    if not new_email:
        flash("Please enter a new email.", "danger")
        return redirect(url_for("profile"))
    if db.get_user_by_email(new_email):
        flash("Email already in use.", "danger")
        return redirect(url_for("profile"))
    code = str(random.randint(100000, 999999))
    db.save_reset_code(new_email, code)
    try:
        msg = Message("TravelBook — Email Change Verification",
                      sender="ellajoylocahinherra5@gmail.com",
                      recipients=[new_email])
        msg.body = f"Your email change verification code is: {code}\n\nEnter this code to confirm your new email."
        mail.send(msg)
        session["pending_email"] = new_email
        flash("A verification code has been sent to your new email.", "info")
        return redirect(url_for("verify_email_change"))
    except Exception as e:
        flash(f"Failed to send email: {str(e)}", "danger")
        return redirect(url_for("profile"))


@app.route("/profile/verify-email", methods=["GET", "POST"])
@login_required
def verify_email_change():
    new_email = session.get("pending_email")
    if not new_email:
        return redirect(url_for("profile"))
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        record = db.get_reset_code(new_email)
        if record and record["code"] == code:
            db.update_user_profile(session["user_id"], {"email": new_email})
            db.delete_reset_code(new_email)
            session["user_email"] = new_email
            session.pop("pending_email", None)
            flash("Email updated successfully!", "success")
            return redirect(url_for("profile"))
        flash("Invalid code. Please try again.", "danger")
    return render_template("verify_email_change.html", new_email=new_email)


# ── Error Handlers ────────────────────────────────────────────────────────────
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
        flash(f"Booking #{booking_id} cancelled and deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/reject-cancel/<booking_id>", methods=["POST"])
@admin_required
def admin_reject_cancel(booking_id):
    db.reject_cancellation(booking_id)
    flash(f"Cancellation request for #{booking_id} rejected.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/trip/add", methods=["GET", "POST"])
@admin_required
def admin_add_trip():
    if request.method == "POST":
        fields = ["type", "from_city", "to_city", "departure", "arrival", "operator", "price", "seats"]
        data = {f: request.form.get(f, "").strip() for f in fields}
        try:
            data["price"] = float(data["price"])
            data["seats"] = int(data["seats"])
        except Exception:
            flash("Invalid price or seats.", "danger")
            return render_template("add_trip.html", cities=CITIES)
        db.create_trip(data)
        flash("Trip added!", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("add_trip.html", cities=CITIES)

@app.route("/admin/trip/edit/<trip_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_trip(trip_id):
    trip = db.get_trip(trip_id)
    if not trip:
        flash("Trip not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        fields = ["from_city", "to_city", "departure", "arrival", "operator", "price", "seats"]
        data = {f: request.form.get(f, trip.get(f)) for f in fields}
        try:
            data["price"] = float(data["price"])
            data["seats"] = int(data["seats"])
        except Exception:
            pass
        db.update_trip(trip_id, data)
        flash("Trip updated!", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("edit_trip.html", trip=trip, cities=CITIES)

@app.route("/admin/trip/delete/<trip_id>", methods=["POST"])
@admin_required
def admin_delete_trip(trip_id):
    db.delete_trip(trip_id)
    flash("Trip deleted!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/user/delete/<user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    db.delete_user(user_id)
    flash("User deleted!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(debug=True)
