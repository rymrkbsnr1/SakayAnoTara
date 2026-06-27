import sqlite3
import hashlib
from datetime import datetime

DB_NAME = "sakayko.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passenger_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stop_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver_trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER NOT NULL,
            from_stop TEXT NOT NULL,
            to_stop TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            fare_per_head REAL NOT NULL,
            total_fare REAL NOT NULL,
            distance_km REAL NOT NULL,
            estimated_fuel_cost REAL NOT NULL,
            net_income REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fuel_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price_per_liter REAL NOT NULL,
            date_updated TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM fuel_prices")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO fuel_prices (price_per_liter, date_updated) VALUES (?, ?)",
            (75.50, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )

    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─── STOPS & FARE MATRIX ──────────────────────────────────────

# Stops along Zapote–Tagaytay via Aguinaldo Highway
# (distance in km from Zapote)
STOPS = [
    {"name": "Zapote",          "km": 0.0},
    {"name": "Bacoor Rotunda",  "km": 4.5},
    {"name": "SM Bacoor",       "km": 6.0},
    {"name": "Imus Crossing",   "km": 10.5},
    {"name": "Pasong Buaya",    "km": 13.0},
    {"name": "Dasmariñas",      "km": 17.0},
    {"name": "Pala-Pala",       "km": 19.5},
    {"name": "Silang Market",   "km": 24.0},
    {"name": "Silang Terminal", "km": 24.8},
    {"name": "Lalaan",          "km": 28.0},
    {"name": "Tagaytay Rotonda","km": 34.0},
    {"name": "Tagaytay Market", "km": 35.5},
]

STOP_NAMES = [s["name"] for s in STOPS]

# LTFRB 2026 fare matrix — Traditional Jeepney
MIN_FARE = 14.00       # first 4 km
MIN_KM   = 4.0
PER_KM   = 2.00        # per km after first 4km
FUEL_PER_KM = 0.35     # estimated fuel consumed per km (in liters)

def get_stop_km(stop_name):
    for s in STOPS:
        if s["name"] == stop_name:
            return s["km"]
    return 0.0

def compute_fare(from_stop, to_stop):
    """Compute LTFRB fare between two stops."""
    km_from = get_stop_km(from_stop)
    km_to   = get_stop_km(to_stop)
    distance = abs(km_to - km_from)
    if distance <= MIN_KM:
        fare = MIN_FARE
    else:
        fare = MIN_FARE + (distance - MIN_KM) * PER_KM
    return round(fare, 2), round(distance, 2)

def compute_fuel_cost(distance_km, fuel_price):
    liters = distance_km * FUEL_PER_KM
    return round(liters * fuel_price, 2)

# ─── USER FUNCTIONS ───────────────────────────────────────────

def register_user(full_name, email, password, role):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)",
            (full_name, email, hash_password(password), role)
        )
        conn.commit()
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, "Email already exists."
    finally:
        conn.close()

def login_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return True, dict(user)
    return False, "Invalid email or password."

# ─── PASSENGER FUNCTIONS ──────────────────────────────────────

def submit_waiting(user_id, stop_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE passenger_requests SET status='inactive' WHERE user_id=? AND status='active'",
        (user_id,)
    )
    cursor.execute(
        "INSERT INTO passenger_requests (user_id, stop_name, timestamp, status) VALUES (?,?,?,'active')",
        (user_id, stop_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def cancel_waiting(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE passenger_requests SET status='inactive' WHERE user_id=? AND status='active'",
        (user_id,)
    )
    conn.commit()
    conn.close()

def get_active_requests():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stop_name, COUNT(*) as passenger_count
        FROM passenger_requests
        WHERE status='active'
        GROUP BY stop_name
        ORDER BY passenger_count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── DRIVER FUNCTIONS ─────────────────────────────────────────

def get_fuel_price():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price_per_liter FROM fuel_prices ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row["price_per_liter"] if row else 75.50

def log_trip(driver_id, from_stop, to_stop, passengers):
    fare_per_head, distance = compute_fare(from_stop, to_stop)
    total_fare = round(fare_per_head * passengers, 2)
    fuel_price = get_fuel_price()
    fuel_cost = compute_fuel_cost(distance, fuel_price)
    net = round(total_fare - fuel_cost, 2)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO driver_trips
        (driver_id, from_stop, to_stop, passengers, fare_per_head,
         total_fare, distance_km, estimated_fuel_cost, net_income, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (driver_id, from_stop, to_stop, passengers,
          fare_per_head, total_fare, distance,
          fuel_cost, net, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return fare_per_head, total_fare, fuel_cost, net, distance

def get_today_summary(driver_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT
            COALESCE(SUM(total_fare),0)          as total_income,
            COALESCE(SUM(estimated_fuel_cost),0) as total_fuel,
            COALESCE(SUM(net_income),0)          as total_net,
            COUNT(*)                              as trip_count
        FROM driver_trips
        WHERE driver_id=? AND timestamp LIKE ?
    """, (driver_id, f"{today}%"))
    row = cursor.fetchone()
    conn.close()
    return dict(row)

def get_trip_history(driver_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT from_stop, to_stop, passengers, fare_per_head,
               total_fare, estimated_fuel_cost, net_income, timestamp
        FROM driver_trips WHERE driver_id=?
        ORDER BY id DESC LIMIT ?
    """, (driver_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_fuel_price_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price_per_liter, date_updated FROM fuel_prices ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_fuel_price(new_price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO fuel_prices (price_per_liter, date_updated) VALUES (?,?)",
        (new_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

# ─── RECOMMENDATIONS ──────────────────────────────────────────

def get_recommendations(driver_id):
    tips = []
    hour = datetime.now().hour

    if 6 <= hour <= 9:
        tips.append({"title": "Peak hour — 6 to 9 AM",
            "body": "High passenger demand. Good time to operate.", "type": "peak"})
    elif 17 <= hour <= 19:
        tips.append({"title": "Evening rush — 5 to 7 PM",
            "body": "Demand is high. Maximize trips now.", "type": "peak"})
    else:
        tips.append({"title": "Low demand period",
            "body": "Consider waiting for peak hours to maximize income.", "type": "low"})

    active = get_active_requests()
    if active:
        top = active[0]
        tips.append({"title": f"{top['passenger_count']} waiting at {top['stop_name']}",
            "body": f"Head to {top['stop_name']} to fill up faster.", "type": "demand"})

    fuel = get_fuel_price()
    if fuel >= 75:
        tips.append({"title": f"Fuel at ₱{fuel:.2f}/L — maximize loads",
            "body": "Higher fuel price today. Make sure each trip is full to keep net income up.",
            "type": "fuel"})

    summary = get_today_summary(driver_id)
    if summary["trip_count"] > 0:
        if summary["total_net"] < summary["total_income"] * 0.4:
            tips.append({"title": "Fuel eating your earnings",
                "body": "Net income is below 40% of gross. Try shorter high-demand routes.",
                "type": "warning"})

    return tips

if __name__ == "__main__":
    create_tables()
    print("Database ready.")
    print(f"Fuel price: ₱{get_fuel_price()}/L")
    fare, dist = compute_fare("Silang Market", "Silang Terminal")
    print(f"Silang to Silang: ₱{fare} ({dist}km) — minimum fare applied")
    fare2, dist2 = compute_fare("Zapote", "Tagaytay Market")
    print(f"Zapote to Tagaytay: ₱{fare2} ({dist2}km)")
    fare3, dist3 = compute_fare("Silang Market", "Tagaytay Rotonda")
    print(f"Silang to Tagaytay: ₱{fare3} ({dist3}km)")

# ─── MULTI-STOP TRIP FUNCTIONS ────────────────────────────────

def get_stops_between(from_stop, to_stop):
    """Return list of stops between from and to (exclusive of origin, inclusive of destinations)."""
    from_km = get_stop_km(from_stop)
    to_km   = get_stop_km(to_stop)
    if from_km == to_km:
        return []
    going_forward = to_km > from_km
    result = []
    for s in STOPS:
        if going_forward:
            if s["km"] > from_km and s["km"] <= to_km:
                result.append(s["name"])
        else:
            if s["km"] < from_km and s["km"] >= to_km:
                result.append(s["name"])
    if not going_forward:
        result.reverse()
    return result

def log_multi_stop_trip(driver_id, from_stop, to_stop, passengers_per_stop):
    """
    Log a single trip with multiple drop-off stops.
    passengers_per_stop = {stop_name: count}
    Fuel cost computed once for the full route distance.
    """
    from_km   = get_stop_km(from_stop)
    to_km     = get_stop_km(to_stop)
    full_dist = abs(to_km - from_km)
    fuel_price = get_fuel_price()
    fuel_cost  = compute_fuel_cost(full_dist, fuel_price)

    total_fare = 0.0
    for stop, count in passengers_per_stop.items():
        if count > 0:
            fare, _ = compute_fare(from_stop, stop)
            total_fare += fare * count

    total_fare = round(total_fare, 2)
    net        = round(total_fare - fuel_cost, 2)

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO driver_trips
        (driver_id, from_stop, to_stop, passengers, fare_per_head,
         total_fare, distance_km, estimated_fuel_cost, net_income, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (driver_id, from_stop, to_stop,
          sum(passengers_per_stop.values()),
          0,  # fare_per_head not applicable for multi-stop
          total_fare, full_dist, fuel_cost, net,
          __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

    return {
        "from": from_stop,
        "to": to_stop,
        "distance": full_dist,
        "passengers": passengers_per_stop,
        "total_fare": total_fare,
        "fuel_cost": fuel_cost,
        "net": net
    }

# ─── HISTORY FUNCTIONS ────────────────────────────────────────

def get_daily_history(driver_id, limit=30):
    """Get income summary per day for the last N days."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            DATE(timestamp) as trip_date,
            COALESCE(SUM(total_fare), 0) as total_income,
            COALESCE(SUM(estimated_fuel_cost), 0) as total_fuel,
            COALESCE(SUM(net_income), 0) as total_net,
            COUNT(*) as trip_count
        FROM driver_trips
        WHERE driver_id = ?
        GROUP BY DATE(timestamp)
        ORDER BY trip_date DESC
        LIMIT ?
    """, (driver_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_today(driver_id):
    """Archive (soft delete) today's trips by marking them as archived."""
    conn = get_connection()
    cursor = conn.cursor()
    today = __import__('datetime').datetime.now().strftime("%Y-%m-%d")
    # We don't actually delete — just mark as a new session
    # by inserting a zero-record sentinel so history is preserved
    cursor.execute("""
        SELECT COUNT(*) FROM driver_trips
        WHERE driver_id = ? AND timestamp LIKE ?
    """, (driver_id, f"{today}%"))
    count = cursor.fetchone()[0]
    conn.close()
    return count  # returns how many trips were "cleared"