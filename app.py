from flask import Flask, render_template, request, redirect, session, url_for
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_this')

# SQL Server connection string
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=REDDRAGON;"
    "DATABASE=RentalCarSystem;"
    "Trusted_Connection=yes;"
)

# Helper function to connect to database
def get_db():
    return pyodbc.connect(conn_str)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO UserAccount (FullName, Email, PasswordHash, Role)
                VALUES (?, ?, ?, ?)
            """, (full_name, email, hashed_password, role))
            conn.commit()
        except Exception as e:
            return render_template('register.html', error=f"Error registering user: {e}")
        finally:
            conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT Id, FullName, Email, PasswordHash, Role FROM UserAccount WHERE Email = ?", (email,))
            user = cursor.fetchone()
        except Exception as e:
            return f"Database error: {e}", 500
        finally:
            conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[4]

            if user[4] == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('vehicles'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Vehicle")
    total_vehicles = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Vehicle WHERE IsAvailable = 1")
    available_vehicles = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Rental WHERE EndDate >= GETDATE() AND IsActive = 1")
    active_rentals = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM UserAccount WHERE Role = 'Customer'")
    total_customers = cursor.fetchone()[0]
    conn.close()

    return render_template('admin_dashboard.html',
                           name=session['user_name'],
                           total_vehicles=total_vehicles,
                           available_vehicles=available_vehicles,
                           active_rentals=active_rentals,
                           total_customers=total_customers)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/vehicles')
def vehicles():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    city = request.args.get('city')
    vehicle_type = request.args.get('type')
    brand = request.args.get('brand')

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Base query with join for location details
        query = """
            SELECT v.Id, v.Name, v.Type, v.Brand, v.IsLuxury, v.PricePerDay, v.IsAvailable,
                   l.Country, l.City
            FROM Vehicle v
            JOIN Location l ON v.LocationId = l.Id
            WHERE 1=1
        """
        params = []

        if city:
            query += " AND l.City = ?"
            params.append(city)
        if vehicle_type:
            query += " AND v.Type = ?"
            params.append(vehicle_type)
        if brand:
            query += " AND v.Brand = ?"
            params.append(brand)

        query += " ORDER BY v.Name"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        user_rentals = {}
        if session.get('role') == 'Customer':
            cursor.execute("""
                SELECT VehicleId, Id FROM Rental
                WHERE CustomerId = ? AND IsActive = 1
            """, (session['user_id'],))
            user_rentals = {row[0]: row[1] for row in cursor.fetchall()}

    except Exception as e:
        return f"Database error: {e}", 500
    finally:
        conn.close()

    vehicles = []
    for row in rows:
        vehicle_id = row[0]
        vehicles.append({
            'id': vehicle_id,
            'name': row[1],
            'type': row[2],
            'brand': row[3],
            'is_luxury': bool(row[4]),
            'price_per_day': float(row[5]),
            'is_available': bool(row[6]),
            'country': row[7],
            'city': row[8],
            'rented_by_user': vehicle_id in user_rentals,
            'rental_id': user_rentals.get(vehicle_id)
        })

    return render_template('vehicles.html', vehicles=vehicles)

@app.route('/vehicles/rent/<int:vehicle_id>', methods=['POST'])
def rent_vehicle(vehicle_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Rental (VehicleId, CustomerId, StartDate, IsActive) VALUES (?, ?, GETDATE(), 1)", (vehicle_id, session['user_id']))
        cursor.execute("UPDATE Vehicle SET IsAvailable = 0 WHERE Id = ?", (vehicle_id,))
        conn.commit()
    except Exception as e:
        return f"Error renting vehicle: {e}", 500
    finally:
        conn.close()

    return redirect(url_for('vehicles'))

@app.route('/my_rentals')
def my_rentals():
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.Id, v.Name, r.StartDate, r.EndDate, r.IsActive
        FROM Rental r
        JOIN Vehicle v ON r.VehicleId = v.Id
        WHERE r.CustomerId = ? AND r.IsActive = 1
    """, (session['user_id'],))
    rentals = cursor.fetchall()
    conn.close()

    return render_template('my_rentals.html', rentals=rentals)

@app.route('/rentals/end/<int:rental_id>', methods=['POST'])
def end_rental(rental_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect(url_for('login'))

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Rental SET EndDate = GETDATE(), IsActive = 0 WHERE Id = ?;
            UPDATE Vehicle SET IsAvailable = 1 
            WHERE Id = (SELECT VehicleId FROM Rental WHERE Id = ?)
        """, (rental_id, rental_id))
        conn.commit()
    except Exception as e:
        return f"Error ending rental: {e}", 500
    finally:
        conn.close()

    return redirect(url_for('my_rentals'))

@app.route('/add-vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        vtype = request.form['type']
        brand = request.form['brand']
        is_luxury = int(request.form.get('is_luxury', 0))  # checkbox, returns '1' or ''
        price_per_day = request.form['price_per_day']
        location_id = request.form['location_id']
        is_available = 1  # default to available when adding

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Vehicle (Name, Type, Brand, IsLuxury, PricePerDay, IsAvailable, LocationId)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, vtype, brand, is_luxury, price_per_day, is_available, location_id))
            conn.commit()
        except Exception as e:
            return f"Error adding vehicle: {e}", 500
        finally:
            conn.close()

        return redirect(url_for('vehicles'))

    return render_template('add_vehicle.html')


if __name__ == '__main__':
    app.run(debug=True)
