import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_file

# --- Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "event_registration.db")

app = Flask(__name__)
app.secret_key = "replace_this_with_a_random_secret"

# --- DB helpers ---
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

# --- Routes ---
@app.route("/")
def index():
    db = get_db()
    events = db.execute("SELECT * FROM events").fetchall()
    return render_template("index.html", events=events)

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
            flash("Signup successful — please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
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
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# Admin: create event
@app.route("/create_event", methods=["GET","POST"])
def create_event():
    if session.get("role") != "admin":
        flash("Only admins can create events.", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        date = request.form["date"].strip()
        fee = float(request.form["fee"] or 0)
        max_members = int(request.form["max_members"] or 0)
        db = get_db()
        db.execute("INSERT INTO events (title,description,date,fee,max_members) VALUES (?,?,?,?,?)",
                   (title,description,date,fee,max_members))
        db.commit()
        flash("Event created.", "success")
        return redirect(url_for("index"))
    return render_template("create_event.html")

# Participant: register for event
@app.route("/register_event/<int:event_id>", methods=["GET","POST"])
def register_event(event_id):
    if session.get("role") != "participant":
        flash("Only participants can register.", "danger")
        return redirect(url_for("login"))
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("index"))

    # insert registration (user -> event)
    db.execute("INSERT INTO registrations (event_id, user_id) VALUES (?,?)",
               (event_id, session["user_id"]))
    db.commit()
    flash(f"Registered for {event['title']}.", "success")
    return redirect(url_for("index"))

# Admin: view participants for an event
@app.route("/participants/<int:event_id>")
def participants(event_id):
    if session.get("role") != "admin":
        flash("Only admins can view participants.", "danger")
        return redirect(url_for("login"))
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for("index"))
    rows = db.execute("""
        SELECT u.id, u.username
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
    """, (event_id,)).fetchall()
    return render_template("participants.html", event=event, participants=rows)

# Admin: remove participant from event
@app.route("/remove_participant/<int:event_id>/<int:user_id>")
def remove_participant(event_id, user_id):
    if session.get("role") != "admin":
        flash("Only admins can remove participants.", "danger")
        return redirect(url_for("login"))
    db = get_db()
    db.execute("DELETE FROM registrations WHERE event_id=? AND user_id=?", (event_id,user_id))
    db.commit()
    flash("Participant removed.", "info")
    return redirect(url_for("participants", event_id=event_id))

# Admin: export participants to CSV
@app.route("/export_participants/<int:event_id>")
def export_participants(event_id):
    if session.get("role") != "admin":
        flash("Only admins can export.", "danger")
        return redirect(url_for("login"))
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    rows = db.execute("""
        SELECT u.username
        FROM registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id=?
    """, (event_id,)).fetchall()
    # create temporary CSV
    csv_path = os.path.join(BASE_DIR, f"participants_event_{event_id}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        import csv
        w = csv.writer(f)
        w.writerow(["username"])
        for r in rows:
            w.writerow([r["username"]])
    return send_file(csv_path, as_attachment=True)

if __name__ == "__main__":
    # If DB missing, instruct user to run init_db.py or run it automatically:
    if not os.path.exists(DATABASE):
        # try to run the initializer automatically
        try:
            from init_db import init_db
            init_db()
            print("Database created by init_db.py")
        except Exception as e:
            print("Database missing and init_db.py could not run:", e)
    app.run(debug=True)
