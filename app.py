import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_file
from werkzeug.utils import secure_filename
import csv
import io
from flask import send_file



# ------------------ APP SETUP ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "event_registration.db")

app = Flask(__name__)
app.secret_key = "replace_with_random_secret"

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# ------------------ DB CONNECTION ------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ------------------ HELPERS ------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------ ROUTES ------------------

@app.route("/")
def index():
    db = get_db()
    events = db.execute("SELECT * FROM events").fetchall()
    return render_template("index.html", events=events)


# ------------ USER AUTH ------------

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form.get("role","participant")

        db = get_db()
        try:
            db.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                       (username, password, role))
            db.commit()
            flash("Signup successful — login now", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists", "danger")
    return render_template("signup.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                          (username,password)).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome {user['username']}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("index"))


# ------------ ADMIN CREATE EVENT ------------

@app.route("/create_event", methods=["GET","POST"])
def create_event():
    if session.get("role") != "admin":
        flash("Admin access only", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":

        # -------- NEW FIELDS FROM YOUR HTML --------
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        date = request.form["date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        venue = request.form["venue"]
        last_date = request.form["last_date"]
        fee = request.form["fee"]
        is_team_event = request.form["is_team_event"]
        team_size = request.form.get("team_size")
        organizer_name = request.form["organizer_name"]
        organizer_contact = request.form["organizer_contact"]
        status = request.form["status"]

        db = get_db()


        db.execute("""
            INSERT INTO events
            (title, description, category, date, start_time, end_time, venue,
            last_date, fee, is_team_event, team_size,
            organizer_name, organizer_contact, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
         """,
         (title, description, category, date, start_time, end_time, venue,
         last_date, fee, is_team_event, team_size,
         organizer_name, organizer_contact, status))


        

        db.commit()

        flash("Event created successfully", "success")
        return redirect(url_for("index"))

    return render_template("create_event.html")

# ------------ PARTICIPANT EVENT REGISTRATION FORM ------------

@app.route("/register_event/<int:event_id>", methods=["GET","POST"])
def register_event(event_id):

    if session.get("role") != "participant":
        flash("Login as participant to register", "danger")
        return redirect(url_for("login"))

    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()

    if not event:
        flash("Event not found", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":

        full_name = request.form["full_name"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        college = request.form["college"]
        year = request.form["year"]
        branch = request.form["branch"]

        file = request.files["payment_screenshot"]

        if not file or not allowed_file(file.filename):
            flash("Upload JPG or PNG only", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        db.execute("""
            INSERT INTO registrations 
            (event_id, user_id, full_name, mobile, email, college, year, branch, payment_image)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (event_id, session["user_id"], full_name, mobile, email, college, year, branch, filename))

        db.commit()

        flash("Registration submitted successfully!", "success")
        return redirect(url_for("index"))

    return render_template("register_event.html", event=event)




# ------------ ADMIN VIEW PARTICIPANTS ------------
@app.route("/participants/<int:event_id>")
def participants(event_id):

    if session.get("role") != "admin":
        flash("Admin access only", "danger")
        return redirect(url_for("login"))

    db = get_db()

    participants = db.execute("""
        SELECT *
        FROM registrations
        WHERE event_id=?
    """, (event_id,)).fetchall()

    event = db.execute(
        "SELECT * FROM events WHERE id=?",
        (event_id,)
    ).fetchone()

    return render_template(
        "participants.html",
        event=event,
        participants=participants
    )


# ------------ ADMIN EXPORT CSV ------------
@app.route("/export/<int:event_id>")
def export(event_id):

    if session.get("role") != "admin":
        flash("Admin access only", "danger")
        return redirect(url_for("login"))

    db = get_db()

    rows = db.execute("""
        SELECT full_name, mobile, email, college, year, branch
        FROM registrations
        WHERE event_id=?
    """, (event_id,)).fetchall()

    si = io.StringIO()
    cw = csv.writer(si)

    # CSV Header
    cw.writerow(["Full Name", "Mobile", "Email", "College", "Year", "Branch"])

    # CSV Rows
    for r in rows:
        cw.writerow([
            r["full_name"],
            r["mobile"],
            r["email"],
            r["college"],
            r["year"],
            r["branch"]
        ])

    output = io.BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="participants.csv"
    )


# ------------ RUN APP ------------

if __name__ == "__main__":
    app.run(debug=True)
