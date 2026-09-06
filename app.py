import os
import secrets
import smtplib
import sqlite3
import click
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
SUPPORTED_LANGUAGES = {"en": "English", "hi": "हिन्दी", "mr": "मराठी"}


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(BASE_DIR / "instance"), instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.getenv("DATABASE_PATH", str(BASE_DIR / "instance" / "procureflow.db")),
        APP_BASE_URL=os.getenv("APP_BASE_URL", "http://127.0.0.1:5000"),
        SMTP_ENABLED=os.getenv("SMTP_ENABLED", "false").lower() == "true",
        SMTP_HOST=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        SMTP_PORT=int(os.getenv("SMTP_PORT", "587")),
        SMTP_USERNAME=os.getenv("SMTP_USERNAME", ""),
        SMTP_APP_PASSWORD=os.getenv("SMTP_APP_PASSWORD", ""),
        SMTP_FROM_NAME=os.getenv("SMTP_FROM_NAME", "ProcureFlow"),
        SMTP_FROM_EMAIL=os.getenv("SMTP_FROM_EMAIL", ""),
        PUBLIC_SITE_ORIGIN=os.getenv("PUBLIC_SITE_ORIGIN", ""),
        DEMO_ALERT_RECIPIENT=os.getenv("DEMO_ALERT_RECIPIENT", ""),
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)

    @app.before_request
    def load_user_and_csrf():
        g.user = None
        if "user_id" in session:
            g.user = query_one("SELECT * FROM users WHERE id = ?", (session["user_id"],))
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(24)

    @app.context_processor
    def inject_globals():
        return {
            "current_user": g.user,
            "csrf_token": session.get("csrf_token"),
            "today": date.today().isoformat(),
            "language": session.get("language", "en"),
            "languages": SUPPORTED_LANGUAGES,
        }

    @app.template_filter("pretty_date")
    def pretty_date(value):
        if not value:
            return "—"
        try:
            parsed = datetime.fromisoformat(str(value))
            lang = session.get("language", "en")
            months = {
                "hi": ("जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अग", "सित", "अक्टू", "नव", "दिस"),
                "mr": ("जाने", "फेब्रु", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑग", "सप्टें", "ऑक्टो", "नोव्हें", "डिसें"),
            }
            if lang in months:
                return f"{parsed.day:02d} {months[lang][parsed.month - 1]} {parsed.year}"
            return parsed.strftime("%d %b %Y")
        except ValueError:
            return value

    @app.template_filter("pretty_time")
    def pretty_time(value):
        if not value:
            return "—"
        try:
            return datetime.fromisoformat(str(value)).strftime("%d %b, %I:%M %p")
        except ValueError:
            return value

    @app.template_filter("number")
    def number(value):
        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return value

    @app.get("/")
    def index():
        if not g.user:
            return redirect(url_for("login"))
        if g.user["role"] == "farmer":
            return redirect(url_for("farmer_dashboard"))
        if g.user["role"] == "staff":
            return redirect(url_for("staff_dashboard"))
        return redirect(url_for("admin_dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            require_csrf()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = query_one("SELECT * FROM users WHERE email = ? AND active = 1", (email,))
            if user and check_password_hash(user["password_hash"], password):
                selected_language = session.get("language", "en")
                session.clear()
                session["user_id"] = user["id"]
                session["csrf_token"] = secrets.token_hex(24)
                session["language"] = selected_language
                audit("login", "user", user["id"], f"{user['role']} signed in")
                return redirect(url_for("index"))
            flash("Email or password is incorrect.", "error")
        return render_template("login.html")

    @app.post("/language/<code>")
    def change_language(code):
        require_csrf()
        if code not in SUPPORTED_LANGUAGES:
            abort(404)
        session["language"] = code
        destination = request.form.get("next", "")
        if not destination.startswith("/") or destination.startswith("//"):
            destination = url_for("index") if g.user else url_for("login")
        return redirect(destination)

    @app.post("/logout")
    def logout():
        require_csrf()
        selected_language = session.get("language", "en")
        session.clear()
        session["language"] = selected_language
        return redirect(url_for("login"))

    @app.get("/farmer")
    @role_required("farmer")
    def farmer_dashboard():
        next_booking = query_one(
            """SELECT b.*, s.procurement_date, s.start_time, s.end_time,
                      c.name centre_name, c.address centre_address, m.name commodity_name
               FROM bookings b JOIN schedules s ON s.id=b.schedule_id
               JOIN centres c ON c.id=s.centre_id JOIN commodities m ON m.id=s.commodity_id
               WHERE b.farmer_id=? AND b.status NOT IN ('completed','cancelled','no_show')
               ORDER BY s.procurement_date, s.start_time LIMIT 1""",
            (g.user["id"],),
        )
        schedules = query_all(
            """SELECT s.*, c.name centre_name, c.district, m.name commodity_name,
                      (SELECT COUNT(*) FROM bookings b WHERE b.schedule_id=s.id
                       AND b.status NOT IN ('cancelled','no_show')) booked
               FROM schedules s JOIN centres c ON c.id=s.centre_id
               JOIN commodities m ON m.id=s.commodity_id
               WHERE s.status='open' AND s.procurement_date>=?
               ORDER BY s.procurement_date, s.start_time LIMIT 6""",
            (date.today().isoformat(),),
        )
        notices = query_all(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 5",
            (g.user["id"],),
        )
        return render_template("farmer_dashboard.html", next_booking=next_booking, schedules=schedules, notices=notices)

    @app.get("/schedules")
    @role_required("farmer")
    def schedules():
        district = request.args.get("district", "").strip()
        commodity = request.args.get("commodity", "").strip()
        sql = """SELECT s.*, c.name centre_name, c.district, c.address, m.name commodity_name,
                        m.min_quantity, m.max_quantity,
                        (SELECT COUNT(*) FROM bookings b WHERE b.schedule_id=s.id
                         AND b.status NOT IN ('cancelled','no_show')) booked
                 FROM schedules s JOIN centres c ON c.id=s.centre_id
                 JOIN commodities m ON m.id=s.commodity_id
                 WHERE s.status='open' AND s.procurement_date>=?"""
        params = [date.today().isoformat()]
        if district:
            sql += " AND c.district=?"
            params.append(district)
        if commodity:
            sql += " AND m.name=?"
            params.append(commodity)
        sql += " ORDER BY s.procurement_date, s.start_time"
        rows = query_all(sql, tuple(params))
        districts = query_all("SELECT DISTINCT district FROM centres ORDER BY district")
        commodities = query_all("SELECT name FROM commodities ORDER BY name")
        return render_template("schedules.html", schedules=rows, districts=districts, commodities=commodities)

    @app.route("/book/<int:schedule_id>", methods=["GET", "POST"])
    @role_required("farmer")
    def book(schedule_id):
        schedule_row = query_one(
            """SELECT s.*, c.name centre_name, c.address, c.district,
                      m.name commodity_name, m.min_quantity, m.max_quantity, m.required_docs
               FROM schedules s JOIN centres c ON c.id=s.centre_id
               JOIN commodities m ON m.id=s.commodity_id WHERE s.id=?""",
            (schedule_id,),
        )
        if not schedule_row or schedule_row["status"] != "open":
            abort(404)
        if request.method == "POST":
            require_csrf()
            try:
                quantity = float(request.form.get("quantity", "0"))
            except ValueError:
                quantity = 0
            confirmations = all(request.form.get(k) == "yes" for k in ("identity", "bank", "land", "produce"))
            errors = []
            if not confirmations:
                errors.append("Confirm all required eligibility declarations.")
            if not schedule_row["min_quantity"] <= quantity <= schedule_row["max_quantity"]:
                errors.append(f"Quantity must be between {schedule_row['min_quantity']:g} and {schedule_row['max_quantity']:g} quintals.")
            existing = query_one(
                "SELECT id FROM bookings WHERE farmer_id=? AND schedule_id=? AND status NOT IN ('cancelled','no_show')",
                (g.user["id"], schedule_id),
            )
            if existing:
                errors.append("You already have an active token for this schedule.")
            booked = query_one(
                "SELECT COUNT(*) count FROM bookings WHERE schedule_id=? AND status NOT IN ('cancelled','no_show')",
                (schedule_id,),
            )["count"]
            if booked >= schedule_row["capacity"]:
                errors.append("This schedule has reached capacity.")
            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                queue_position = booked + 1
                token_number = make_token(schedule_row["procurement_date"], schedule_id, queue_position)
                now = datetime.now().isoformat(timespec="seconds")
                db = get_db()
                cursor = db.execute(
                    """INSERT INTO bookings
                       (token_number, farmer_id, schedule_id, quantity, eligibility_status,
                        status, queue_position, booked_at, updated_at)
                       VALUES (?,?,?,?,?,'booked',?,?,?)""",
                    (token_number, g.user["id"], schedule_id, quantity, "eligible", queue_position, now, now),
                )
                db.commit()
                booking_id = cursor.lastrowid
                audit("booking_created", "booking", booking_id, token_number)
                create_notification(
                    g.user["id"], "Token confirmed",
                    f"Your {schedule_row['commodity_name']} token {token_number} is confirmed for {schedule_row['procurement_date']}.",
                    "email",
                )
                return redirect(url_for("token_detail", booking_id=booking_id))
        return render_template("book.html", schedule=schedule_row)

    @app.get("/token/<int:booking_id>")
    @login_required
    def token_detail(booking_id):
        booking = get_booking(booking_id)
        if not booking:
            abort(404)
        if g.user["role"] == "farmer" and booking["farmer_id"] != g.user["id"]:
            abort(403)
        queue = queue_metrics(booking["schedule_id"], booking_id)
        return render_template("token.html", booking=booking, queue=queue)

    @app.post("/token/<int:booking_id>/cancel")
    @role_required("farmer")
    def cancel_booking(booking_id):
        require_csrf()
        booking = get_booking(booking_id)
        if not booking or booking["farmer_id"] != g.user["id"]:
            abort(404)
        if booking["status"] not in ("booked", "checked_in"):
            flash("This token can no longer be cancelled.", "error")
        else:
            update_booking_status(booking_id, "cancelled")
            flash("Token cancelled. The slot has been released.", "success")
        return redirect(url_for("farmer_dashboard"))

    @app.get("/staff")
    @role_required("staff")
    def staff_dashboard():
        schedules_rows = query_all(
            """SELECT s.*, c.name centre_name, m.name commodity_name,
                      COUNT(b.id) total_bookings,
                      SUM(CASE WHEN b.status='checked_in' THEN 1 ELSE 0 END) waiting,
                      SUM(CASE WHEN b.status='completed' THEN 1 ELSE 0 END) completed
               FROM schedules s JOIN centres c ON c.id=s.centre_id
               JOIN commodities m ON m.id=s.commodity_id
               LEFT JOIN bookings b ON b.schedule_id=s.id
               WHERE c.staff_user_id=? AND s.procurement_date>=?
               GROUP BY s.id ORDER BY s.procurement_date, s.start_time""",
            (g.user["id"], (date.today() - timedelta(days=1)).isoformat()),
        )
        return render_template("staff_dashboard.html", schedules=schedules_rows)

    @app.get("/staff/queue/<int:schedule_id>")
    @role_required("staff")
    def staff_queue(schedule_id):
        schedule_row = owned_schedule(schedule_id)
        if not schedule_row:
            abort(404)
        bookings = query_all(
            """SELECT b.*, u.name farmer_name, u.phone, u.village
               FROM bookings b JOIN users u ON u.id=b.farmer_id
               WHERE b.schedule_id=? ORDER BY b.queue_position""",
            (schedule_id,),
        )
        return render_template("staff_queue.html", schedule=schedule_row, bookings=bookings)

    @app.post("/staff/booking/<int:booking_id>/<action>")
    @role_required("staff")
    def staff_action(booking_id, action):
        require_csrf()
        booking = get_booking(booking_id)
        if not booking or not owned_schedule(booking["schedule_id"]):
            abort(404)
        transitions = {
            "checkin": ("booked", "checked_in"),
            "start": ("checked_in", "serving"),
            "complete": ("serving", "completed"),
            "no-show": ("booked", "no_show"),
        }
        if action not in transitions:
            abort(400)
        expected, target = transitions[action]
        if booking["status"] != expected:
            flash(f"Cannot apply that action while token is {booking['status'].replace('_', ' ')}.", "error")
        else:
            update_booking_status(booking_id, target)
            flash(f"{booking['token_number']} updated to {target.replace('_', ' ')}.", "success")
        return redirect(url_for("staff_queue", schedule_id=booking["schedule_id"]))

    @app.get("/admin")
    @role_required("admin")
    def admin_dashboard():
        metrics = {
            "farmers": query_one("SELECT COUNT(*) c FROM users WHERE role='farmer'")["c"],
            "open_schedules": query_one("SELECT COUNT(*) c FROM schedules WHERE status='open'")["c"],
            "active_tokens": query_one("SELECT COUNT(*) c FROM bookings WHERE status IN ('booked','checked_in','serving')")["c"],
            "completed": query_one("SELECT COUNT(*) c FROM bookings WHERE status='completed'")["c"],
        }
        schedules_rows = query_all(
            """SELECT s.*, c.name centre_name, m.name commodity_name,
                      COUNT(b.id) booked FROM schedules s
               JOIN centres c ON c.id=s.centre_id JOIN commodities m ON m.id=s.commodity_id
               LEFT JOIN bookings b ON b.schedule_id=s.id AND b.status NOT IN ('cancelled','no_show')
               GROUP BY s.id ORDER BY s.procurement_date DESC"""
        )
        return render_template("admin_dashboard.html", metrics=metrics, schedules=schedules_rows)

    @app.route("/admin/schedule/new", methods=["GET", "POST"])
    @role_required("admin")
    def new_schedule():
        centres = query_all("SELECT * FROM centres ORDER BY name")
        commodities = query_all("SELECT * FROM commodities ORDER BY name")
        if request.method == "POST":
            require_csrf()
            try:
                centre_id = int(request.form["centre_id"])
                commodity_id = int(request.form["commodity_id"])
                capacity = int(request.form["capacity"])
                procurement_date = request.form["procurement_date"]
                start_time = request.form["start_time"]
                end_time = request.form["end_time"]
                slot_minutes = int(request.form.get("slot_minutes", "10"))
                datetime.fromisoformat(f"{procurement_date}T{start_time}")
                datetime.fromisoformat(f"{procurement_date}T{end_time}")
                if capacity < 1 or slot_minutes < 1 or end_time <= start_time:
                    raise ValueError
            except (KeyError, ValueError):
                flash("Enter valid schedule values.", "error")
            else:
                db = get_db()
                cursor = db.execute(
                    """INSERT INTO schedules
                       (centre_id,commodity_id,procurement_date,start_time,end_time,slot_minutes,capacity,status)
                       VALUES (?,?,?,?,?,?,?,'open')""",
                    (centre_id, commodity_id, procurement_date, start_time, end_time, slot_minutes, capacity),
                )
                db.commit()
                audit("schedule_created", "schedule", cursor.lastrowid, procurement_date)
                flash("Procurement schedule created.", "success")
                return redirect(url_for("admin_dashboard"))
        return render_template("new_schedule.html", centres=centres, commodities=commodities)

    @app.post("/admin/schedule/<int:schedule_id>/toggle")
    @role_required("admin")
    def toggle_schedule(schedule_id):
        require_csrf()
        row = query_one("SELECT status FROM schedules WHERE id=?", (schedule_id,))
        if not row:
            abort(404)
        status = "closed" if row["status"] == "open" else "open"
        db = get_db()
        db.execute("UPDATE schedules SET status=? WHERE id=?", (status, schedule_id))
        db.commit()
        audit("schedule_status", "schedule", schedule_id, status)
        flash(f"Schedule marked {status}.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.get("/notifications")
    @login_required
    def notifications():
        if g.user["role"] == "admin":
            rows = query_all(
                """SELECT n.*, u.name recipient_name, u.email recipient_email
                   FROM notifications n JOIN users u ON u.id=n.user_id
                   ORDER BY n.created_at DESC"""
            )
        else:
            rows = query_all(
                """SELECT n.*, u.name recipient_name, u.email recipient_email
                   FROM notifications n JOIN users u ON u.id=n.user_id
                   WHERE n.user_id=? ORDER BY n.created_at DESC""",
                (g.user["id"],),
            )
        return render_template("notifications.html", notifications=rows)

    @app.post("/notifications/<int:notification_id>/retry")
    @role_required("admin")
    def retry_notification(notification_id):
        require_csrf()
        row = query_one(
            """SELECT n.*, u.email FROM notifications n JOIN users u ON u.id=n.user_id WHERE n.id=?""",
            (notification_id,),
        )
        if not row:
            abort(404)
        sent, error = send_email(row["email"], row["subject"], row["message"])
        db = get_db()
        db.execute(
            "UPDATE notifications SET delivery_status=?, error_message=?, sent_at=? WHERE id=?",
            ("sent" if sent else "failed", error, datetime.now().isoformat(timespec="seconds") if sent else None, notification_id),
        )
        db.commit()
        flash("Email sent." if sent else f"Email failed: {error}", "success" if sent else "error")
        return redirect(url_for("notifications"))

    @app.get("/health")
    def health():
        query_one("SELECT 1")
        return {"status": "ok", "service": "ProcureFlow"}

    @app.after_request
    def allow_public_demo_alert(response):
        allowed_origin = app.config["PUBLIC_SITE_ORIGIN"]
        if request.path == "/api/demo-alert" and request.headers.get("Origin") == allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Vary"] = "Origin"
        return response

    @app.post("/api/demo-alert")
    def public_demo_alert():
        if not app.config["PUBLIC_SITE_ORIGIN"] or request.headers.get("Origin") != app.config["PUBLIC_SITE_ORIGIN"]:
            abort(403)
        recipient = app.config["DEMO_ALERT_RECIPIENT"]
        if not recipient:
            return {"ok": False, "message": "Demo recipient is not configured."}, 503
        now = datetime.now()
        last_sent = app.extensions.get("public_alert_last_sent")
        if last_sent and (now - last_sent).total_seconds() < 60:
            return {"ok": False, "message": "Please wait one minute before sending another alert."}, 429
        sent, error = send_email(
            recipient,
            "ProcureFlow live queue alert",
            "Your turn is approaching. 6 farmers are ahead of you and the estimated wait is 42 minutes. Please reach Baramati Procurement Centre with your documents.",
        )
        if not sent:
            return {"ok": False, "message": error or "Email delivery failed."}, 502
        app.extensions["public_alert_last_sent"] = now
        return {"ok": True, "message": "Live queue alert email sent successfully."}

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        seed_db()
        print("Database initialized with demo data.")

    @app.cli.command("send-reminders")
    def send_reminders_command():
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        bookings = query_all(
            """SELECT b.id, b.token_number, u.id user_id, s.procurement_date, s.start_time,
                      c.name centre_name, m.name commodity_name
               FROM bookings b JOIN users u ON u.id=b.farmer_id
               JOIN schedules s ON s.id=b.schedule_id JOIN centres c ON c.id=s.centre_id
               JOIN commodities m ON m.id=s.commodity_id
               WHERE b.status='booked' AND s.procurement_date=?""",
            (tomorrow,),
        )
        for booking in bookings:
            create_notification(
                booking["user_id"], "Procurement reminder",
                f"Reminder: token {booking['token_number']} for {booking['commodity_name']} is tomorrow at {booking['start_time']} at {booking['centre_name']}.",
                "email",
            )
        print(f"Created {len(bookings)} reminders.")

    @app.cli.command("test-smtp")
    @click.option("--to", "recipient", required=True, help="Recipient email address")
    def test_smtp_command(recipient):
        """Send one real SMTP configuration test message."""
        sent, error = send_email(
            recipient,
            "ProcureFlow SMTP test",
            "Your Gmail SMTP configuration is working. This is a ProcureFlow test message.",
        )
        if not sent:
            raise click.ClickException(error or "SMTP test failed")
        click.echo(f"SMTP test message sent to {recipient}.")

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()
        seed_db()
    return app


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(g.current_app.config["DATABASE"] if hasattr(g, "current_app") else current_app().config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def current_app():
    from flask import current_app as flask_current_app
    return flask_current_app


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def init_db():
    schema = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")
    get_db().executescript(schema)
    get_db().commit()


def seed_db():
    if query_one("SELECT id FROM users LIMIT 1"):
        return
    db = get_db()
    users = [
        ("Ramesh Patil", "farmer@demo.in", "9990011223", "farmer", "Farmer@123", "F-MH-1042", "Shirur", 4.5),
        ("Meera Joshi", "farmer2@demo.in", "9990011224", "farmer", "Farmer@123", "F-MH-1043", "Haveli", 2.8),
        ("Asha Kulkarni", "staff@demo.in", "9990011225", "staff", "Staff@123", None, "Pune", None),
        ("System Admin", "admin@demo.in", "9990011226", "admin", "Admin@123", None, "Pune", None),
    ]
    for name, email, phone, role, password, farmer_id, village, land in users:
        db.execute(
            """INSERT INTO users(name,email,phone,role,password_hash,farmer_registration_id,village,land_acres)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, email, phone, role, generate_password_hash(password), farmer_id, village, land),
        )
    staff_id = db.execute("SELECT id FROM users WHERE role='staff'").fetchone()[0]
    db.execute(
        "INSERT INTO centres(name,district,address,staff_user_id) VALUES (?,?,?,?)",
        ("Shirur Procurement Centre", "Pune", "Market Yard Road, Shirur, Pune", staff_id),
    )
    db.execute(
        "INSERT INTO centres(name,district,address,staff_user_id) VALUES (?,?,?,?)",
        ("Baramati Procurement Centre", "Pune", "APMC Campus, Baramati, Pune", staff_id),
    )
    commodities = [
        ("Wheat", 1, 80, "Government ID, bank proof, land/tenancy record"),
        ("Paddy", 1, 100, "Government ID, bank proof, land/tenancy record"),
        ("Onion", 1, 120, "Government ID, bank proof, farmer registration"),
    ]
    db.executemany(
        "INSERT INTO commodities(name,min_quantity,max_quantity,required_docs) VALUES (?,?,?,?)",
        commodities,
    )
    centre_ids = [row[0] for row in db.execute("SELECT id FROM centres ORDER BY id").fetchall()]
    commodity_ids = [row[0] for row in db.execute("SELECT id FROM commodities ORDER BY id").fetchall()]
    schedule_data = [
        (centre_ids[0], commodity_ids[0], (date.today() + timedelta(days=2)).isoformat(), "09:00", "14:00", 10, 24, "open"),
        (centre_ids[0], commodity_ids[2], (date.today() + timedelta(days=4)).isoformat(), "08:30", "13:30", 10, 30, "open"),
        (centre_ids[1], commodity_ids[1], (date.today() + timedelta(days=5)).isoformat(), "09:00", "15:00", 12, 25, "open"),
    ]
    db.executemany(
        """INSERT INTO schedules(centre_id,commodity_id,procurement_date,start_time,end_time,slot_minutes,capacity,status)
           VALUES (?,?,?,?,?,?,?,?)""",
        schedule_data,
    )
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if not g.user:
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(**kwargs):
            if not g.user:
                return redirect(url_for("login"))
            if g.user["role"] not in roles:
                abort(403)
            return view(**kwargs)
        return wrapped
    return decorator


def require_csrf():
    if not secrets.compare_digest(request.form.get("csrf_token", ""), session.get("csrf_token", "")):
        abort(400, "Invalid form token")


def make_token(procurement_date, schedule_id, position):
    day = datetime.fromisoformat(procurement_date).strftime("%d%m")
    return f"PF-{day}-{schedule_id:02d}-{position:03d}"


def get_booking(booking_id):
    return query_one(
        """SELECT b.*, u.name farmer_name, u.email farmer_email, u.phone farmer_phone, u.village,
                  s.procurement_date, s.start_time, s.end_time, s.slot_minutes,
                  c.name centre_name, c.address centre_address, c.district,
                  m.name commodity_name
           FROM bookings b JOIN users u ON u.id=b.farmer_id
           JOIN schedules s ON s.id=b.schedule_id JOIN centres c ON c.id=s.centre_id
           JOIN commodities m ON m.id=s.commodity_id WHERE b.id=?""",
        (booking_id,),
    )


def owned_schedule(schedule_id):
    return query_one(
        """SELECT s.*, c.name centre_name, c.address, m.name commodity_name
           FROM schedules s JOIN centres c ON c.id=s.centre_id
           JOIN commodities m ON m.id=s.commodity_id
           WHERE s.id=? AND c.staff_user_id=?""",
        (schedule_id, g.user["id"]),
    )


def queue_metrics(schedule_id, booking_id):
    booking = query_one("SELECT queue_position,status FROM bookings WHERE id=?", (booking_id,))
    ahead = query_one(
        """SELECT COUNT(*) count FROM bookings
           WHERE schedule_id=? AND queue_position<? AND status IN ('booked','checked_in','serving')""",
        (schedule_id, booking["queue_position"]),
    )["count"]
    slot = query_one("SELECT slot_minutes FROM schedules WHERE id=?", (schedule_id,))["slot_minutes"]
    return {"ahead": ahead, "estimated_wait": ahead * slot, "position": booking["queue_position"]}


def update_booking_status(booking_id, status):
    now = datetime.now().isoformat(timespec="seconds")
    timestamps = {"checked_in": "checkin_at", "serving": "service_started_at", "completed": "completed_at"}
    db = get_db()
    if status in timestamps:
        column = timestamps[status]
        db.execute(f"UPDATE bookings SET status=?, {column}=?, updated_at=? WHERE id=?", (status, now, now, booking_id))
    else:
        db.execute("UPDATE bookings SET status=?, updated_at=? WHERE id=?", (status, now, booking_id))
    db.commit()
    booking = get_booking(booking_id)
    audit("booking_status", "booking", booking_id, status)
    create_notification(
        booking["farmer_id"], f"Token {booking['token_number']} updated",
        f"Your procurement token is now {status.replace('_', ' ')}. Centre: {booking['centre_name']}.", "email",
    )


def audit(action, entity_type, entity_id, details=""):
    user_id = g.user["id"] if getattr(g, "user", None) else None
    db = get_db()
    db.execute(
        "INSERT INTO audit_logs(user_id,action,entity_type,entity_id,details,created_at) VALUES (?,?,?,?,?,?)",
        (user_id, action, entity_type, entity_id, details, datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()


def create_notification(user_id, subject, message, channel="email"):
    user = query_one("SELECT email FROM users WHERE id=?", (user_id,))
    sent, error = send_email(user["email"], subject, message) if channel == "email" else (False, "channel disabled")
    db = get_db()
    db.execute(
        """INSERT INTO notifications(user_id,channel,subject,message,delivery_status,error_message,created_at,sent_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (user_id, channel, subject, message, "sent" if sent else "logged", error,
         datetime.now().isoformat(timespec="seconds"), datetime.now().isoformat(timespec="seconds") if sent else None),
    )
    db.commit()


def send_email(recipient, subject, body):
    app = current_app()
    if not app.config["SMTP_ENABLED"]:
        return False, "SMTP disabled; message saved in notification centre"
    required = (app.config["SMTP_USERNAME"], app.config["SMTP_APP_PASSWORD"], app.config["SMTP_FROM_EMAIL"])
    if not all(required):
        return False, "SMTP credentials are incomplete"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{app.config['SMTP_FROM_NAME']} <{app.config['SMTP_FROM_EMAIL']}>"
    message["To"] = recipient
    message.set_content(body + f"\n\nOpen ProcureFlow: {app.config['APP_BASE_URL']}")
    try:
        with smtplib.SMTP(app.config["SMTP_HOST"], app.config["SMTP_PORT"], timeout=12) as smtp:
            smtp.starttls()
            smtp.login(app.config["SMTP_USERNAME"], app.config["SMTP_APP_PASSWORD"])
            smtp.send_message(message)
        return True, None
    except Exception as exc:
        return False, str(exc)[:240]


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", use_reloader=False)
