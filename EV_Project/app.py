from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE CONNECTION ----------------
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="@Aamds0401",   # change if needed
    database="evehicle"
)

# ---------------- QUERY FUNCTION (FIXED) ----------------
def query(sql, params=None, fetchone=False, commit=False):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="@Aamds0401",
        database="evehicle"
    )

    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())

    if commit:
        conn.commit()
        cur.close()
        conn.close()
        return

    if fetchone:
        result = cur.fetchone()
    else:
        result = cur.fetchall()

    cur.close()
    conn.close()

    return result

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]

        user = query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)

        if user:
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect("/dashboard")

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        query("INSERT INTO users(name,email,phone) VALUES(%s,%s,%s)",
              (name,email,phone), commit=True)

        return redirect("/login")

    return render_template("register.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    stations = query("SELECT * FROM charging_stations")
    vehicles = query("SELECT * FROM vehicles WHERE user_id=%s", (session["user_id"],))
    sessions = query("SELECT * FROM charging_sessions")

    return render_template("dashboard.html",
                           stations=stations,
                           vehicles=vehicles,
                           total_sessions=len(sessions),
                           total_cost=sum((s["cost"] or 0) for s in sessions),
                           total_energy=sum((s["energy_used"] or 0) for s in sessions))

# ---------------- STATUS ----------------
@app.route("/status")
def status():
    return render_template("status.html")

# ---------------- ADD VEHICLE ----------------
@app.route("/add_vehicle", methods=["GET","POST"])
def add_vehicle():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        model_name = request.form["model_name"]
        battery_capacity = request.form["battery_capacity"]

        query("""
        INSERT INTO vehicles (user_id, model_name, battery_capacity)
        VALUES (%s, %s, %s)
        """, (session["user_id"], model_name, battery_capacity), commit=True)

        return redirect("/my_vehicles")

    return render_template("add_vehicle.html")

# ---------------- MY VEHICLES ----------------
@app.route("/my_vehicles")
def my_vehicles():
    if "user_id" not in session:
        return redirect("/login")

    vehicles = query("SELECT * FROM vehicles WHERE user_id=%s", (session["user_id"],))

    # ✅ handle NULL values
    for v in vehicles:
        if v["battery_capacity"] is None:
            v["battery_capacity"] = 0

    return render_template("my_vehicles.html", vehicles=vehicles)

# ---------------- BOOK SLOT ----------------
@app.route("/book/<int:station_id>", methods=["GET","POST"])
def book_slot(station_id):
    if "user_id" not in session:
        return redirect("/login")

    station = query("SELECT * FROM charging_stations WHERE station_id=%s",
                    (station_id,), fetchone=True)

    vehicles = query("SELECT * FROM vehicles WHERE user_id=%s",
                     (session["user_id"],))

    if request.method == "POST":
        vehicle_id = request.form["vehicle_id"]

        query("""
        INSERT INTO charging_sessions
        (vehicle_id, station_id, start_time, end_time, energy_used, cost)
        VALUES (%s, %s, NOW(), NOW(), 10, 200)
        """, (vehicle_id, station_id), commit=True)

        return redirect("/my_sessions")

    return render_template("book_slot.html", station=station, vehicles=vehicles)

# ---------------- MY SESSIONS ----------------
@app.route("/my_sessions")
def my_sessions():
    if "user_id" not in session:
        return redirect("/login")

    sessions = query("""
    SELECT cs.*, v.model_name, s.station_name, s.location
    FROM charging_sessions cs
    JOIN vehicles v ON cs.vehicle_id = v.vehicle_id
    JOIN charging_stations s ON cs.station_id = s.station_id
    """)

    return render_template("my_sessions.html", sessions=sessions)

# ---------------- PAYMENTS ----------------
@app.route("/payments")
def payments():
    unpaid = query("""
    SELECT cs.*, v.model_name, s.station_name
    FROM charging_sessions cs
    JOIN vehicles v ON cs.vehicle_id=v.vehicle_id
    JOIN charging_stations s ON cs.station_id=s.station_id
    """)

    return render_template("payments.html", unpaid=unpaid)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)