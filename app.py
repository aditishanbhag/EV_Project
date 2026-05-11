from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import mysql.connector
import razorpay
import datetime
from flask_mail import Mail, Message

# Razorpay client
client = razorpay.Client(auth=("rzp_test_SZpDB6IcaJWFfB", "GblQjwaETBCRmAbDfSOiXVqy"))

app = Flask(__name__)
app.secret_key = "secret123"

#email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'shanbhagaditi82@gmail.com'      # your Gmail
app.config['MAIL_PASSWORD'] = 'jlum zyvz pbic tugn'       # your 16-char app password
app.config['MAIL_DEFAULT_SENDER'] = 'aditi.shanbhag@mitwpu.edu.in'

mail = Mail(app)

#database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="@Aamds0401",
    database="evehicle"
)

cursor = conn.cursor(dictionary=True)

#query function
def query(sql, params=None, fetchone=False, commit=False):
    cursor.execute(sql, params or ())
    
    if commit:
        conn.commit()
        return
    
    return cursor.fetchone() if fetchone else cursor.fetchall()

#helper
def stringify_datetimes(rows):
    result = []
    for row in rows:
        new_row = dict(row)
        for k, v in new_row.items():
            if isinstance(v, (datetime.datetime, datetime.date)):
                new_row[k] = str(v)
        result.append(new_row)
    return result

#send support email
def send_support_email(user_email, user_name, subject, message):
    try:
        # Email to user confirming their ticket
        user_msg = Message(
            subject=f"[EV ChargePro] Support Ticket Received: {subject}",
            recipients=[user_email]
        )
        user_msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#020408;color:#e8f4fd;padding:30px;border-radius:12px;border:1px solid rgba(0,212,255,0.2)">
          <div style="text-align:center;margin-bottom:25px">
            <h1 style="font-size:24px;color:#00d4ff;letter-spacing:2px;margin:0">⚡ CHARGEPRO</h1>
            <p style="color:#7ab3cc;font-size:13px;margin-top:5px">EV Charging Station Management</p>
          </div>
          <div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.15);border-radius:8px;padding:20px;margin-bottom:20px">
            <h2 style="color:#39ff6e;font-size:16px;margin:0 0 10px 0">✅ Ticket Received</h2>
            <p style="color:#e8f4fd;margin:0">Hi <strong>{user_name}</strong>, we've received your support request and will get back to you shortly.</p>
          </div>
          <div style="margin-bottom:20px">
            <p style="color:#7ab3cc;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">Your Ticket Details</p>
            <table style="width:100%;border-collapse:collapse">
              <tr><td style="padding:8px 0;color:#7ab3cc;font-size:13px;width:100px">Subject:</td><td style="padding:8px 0;color:#e8f4fd;font-size:13px"><strong>{subject}</strong></td></tr>
              <tr><td style="padding:8px 0;color:#7ab3cc;font-size:13px;vertical-align:top">Message:</td><td style="padding:8px 0;color:#e8f4fd;font-size:13px">{message}</td></tr>
            </table>
          </div>
          <div style="border-top:1px solid rgba(0,212,255,0.1);padding-top:15px;text-align:center">
            <p style="color:#3a6b82;font-size:12px;margin:0">This is an automated email from EV ChargePro. Please do not reply to this email.</p>
          </div>
        </div>
        """

        # Email to admin notifying of new ticket
        admin_msg = Message(
            subject=f"[ChargePro Admin] New Support Ticket from {user_name}: {subject}",
            recipients=['your_email@gmail.com']    # your admin email
        )
        admin_msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">
          <h2 style="color:#ff6b1a">🎫 New Support Ticket</h2>
          <table style="width:100%;border-collapse:collapse;font-size:14px">
            <tr><td style="padding:8px 0;color:#666;width:100px">From:</td><td><strong>{user_name}</strong> ({user_email})</td></tr>
            <tr><td style="padding:8px 0;color:#666">Subject:</td><td><strong>{subject}</strong></td></tr>
            <tr><td style="padding:8px 0;color:#666;vertical-align:top">Message:</td><td>{message}</td></tr>
          </table>
        </div>
        """

        mail.send(user_msg)
        mail.send(admin_msg)

    except Exception as e:
        print(f"Email error: {e}")  # Don't crash the app if email fails

#login
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]

        user = query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)

        if user:
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect("/dashboard")

    return render_template("login.html")

#register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        query("INSERT INTO users(name,email,phone) VALUES(%s,%s,%s)",
              (name, email, phone), commit=True)

        return redirect("/login")

    return render_template("register.html")

#dashboard
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    stations = query("SELECT * FROM charging_stations")
    vehicles = query("SELECT * FROM vehicles WHERE user_id=%s", (session["user_id"],))
    sessions = query("SELECT * FROM charging_sessions")

    def safe_int(x):
        try:
            return int(x)
        except:
            return 0

    total_sessions = len(sessions)
    total_cost = sum(safe_int(s.get("cost")) for s in sessions)
    total_energy = sum(safe_int(s.get("energy_used")) for s in sessions)

    return render_template(
        "dashboard.html",
        stations=stations,
        vehicles=vehicles,
        total_sessions=total_sessions,
        total_cost=total_cost,
        total_energy=total_energy
    )

#status
@app.route("/status")
def status():
    return render_template("status.html")

#book slot
@app.route("/book/<int:station_id>", methods=["GET", "POST"])
def book_slot(station_id):
    if "user_id" not in session:
        return redirect("/login")

    raw = query("SELECT * FROM charging_stations WHERE station_id=%s",
                (station_id,), fetchone=True)

    # Provide defaults for columns that don't exist in the table
    station = {
        "station_id":      raw.get("station_id"),
        "station_name":    raw.get("station_name") or "",
        "location":        raw.get("location") or "",
        "total_slots":     int(raw.get("total_slots") or 0),
        "available_slots": int(raw.get("available_slots") or 0),
        "charger_type":    raw.get("charger_type") or "DC Fast",
        "power_kw":        float(raw.get("power_kw") or 50),
        "status":          raw.get("status") or "Active",
    }

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

#my sessions
@app.route("/my_sessions")
def my_sessions():
    if "user_id" not in session:
        return redirect("/login")

    # FIX: stringify datetimes so template can do s.start_time[:16]
    raw = query("""
    SELECT cs.*, v.model_name, s.station_name, s.location
    FROM charging_sessions cs
    JOIN vehicles v ON cs.vehicle_id = v.vehicle_id
    JOIN charging_stations s ON cs.station_id = s.station_id
    """)
    sessions = stringify_datetimes(raw)

    return render_template("my_sessions.html", sessions=sessions)

#my vehicles
@app.route("/my_vehicles")
def my_vehicles():
    if "user_id" not in session:
        return redirect("/login")

    vehicles = query("""
        SELECT v.*,
            COALESCE(COUNT(cs.session_id), 0) AS total_sessions,
            COALESCE(SUM(cs.energy_used), 0) AS total_energy,
            COALESCE(SUM(cs.cost), 0) AS total_cost
        FROM vehicles v
        LEFT JOIN charging_sessions cs ON v.vehicle_id = cs.vehicle_id
        WHERE v.user_id = %s
        GROUP BY v.vehicle_id
    """, (session["user_id"],))

    return render_template("my_vehicles.html", vehicles=vehicles)

#add vehicles
@app.route("/add_vehicle", methods=["POST"])
def add_vehicle():
    if "user_id" not in session:
        return redirect("/login")

    model_name = request.form["model_name"]
    battery_capacity = request.form["battery_capacity"]
    current_charge = request.form.get("current_charge", 50)

    query("""INSERT INTO vehicles(user_id, model_name, battery_capacity, current_charge)
             VALUES(%s, %s, %s, %s)""",
          (session["user_id"], model_name, battery_capacity, current_charge), commit=True)

    return redirect("/my_vehicles")

#payments
@app.route("/payments")
def payments():
    if "user_id" not in session:
        return redirect("/login")

    unpaid = query("""
    SELECT cs.*, v.model_name, s.station_name
    FROM charging_sessions cs
    JOIN vehicles v ON cs.vehicle_id=v.vehicle_id
    JOIN charging_stations s ON cs.station_id=s.station_id
    """)

    return render_template("payments.html", unpaid=unpaid)

#create order
@app.route("/create_order/<int:amount>")
def create_order(amount):
    order = client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": "1"
    })
    return jsonify(order)

#cancel session
@app.route("/cancel_session/<int:session_id>")
def cancel_session(session_id):
    if "user_id" not in session:
        return redirect("/login")
    query("UPDATE charging_sessions SET status='Cancelled' WHERE session_id=%s",
          (session_id,), commit=True)
    return redirect("/my_sessions")

#payment success
@app.route("/payment_success/<int:session_id>/<int:amount>/<payment_id>")
def payment_success(session_id, amount, payment_id):

    query("""
        INSERT INTO payments (session_id, amount, status, payment_id)
        VALUES (%s, %s, %s, %s)
    """, (session_id, amount, "Paid", payment_id), commit=True)

    return redirect("/payments")

#help
@app.route("/help", methods=["GET", "POST"])
def helpdesk():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        subject = request.form["subject"]
        message = request.form["message"]

        query("""
        INSERT INTO support_tickets (user_id, subject, message)
        VALUES (%s, %s, %s)
        """, (session["user_id"], subject, message), commit=True)

        # Get user email and send automated email
        user = query("SELECT * FROM users WHERE user_id=%s",
                     (session["user_id"],), fetchone=True)
        if user and user.get("email"):
            send_support_email(user["email"], user["name"], subject, message)

        return redirect("/help")

    tickets = query("""
    SELECT * FROM support_tickets
    WHERE user_id = %s
    ORDER BY created_at DESC
    """, (session["user_id"],))

    return render_template("help.html", tickets=tickets)

#map
@app.route("/map")
def map_view():
    if "user_id" not in session:
        return redirect("/login")

    raw = query("SELECT * FROM charging_stations")
    stations = []
    for s in raw:
        stations.append({
            "station_id":      s.get("station_id", 0),
            "station_name":    s.get("station_name") or "",
            "location":        s.get("location") or "",
            "charger_type":    "",
            "power_kw":        0,
            "total_slots":     int(s.get("total_slots") or 0),
            "available_slots": int(s.get("available_slots") or 0),
            "status":          "Active",
            "latitude":        float(s.get("latitude") or 0),
            "longitude":       float(s.get("longitude") or 0),
        })

    return render_template("map.html", stations=stations)

#logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

#run app
if __name__ == "__main__":
    app.run(debug=True)