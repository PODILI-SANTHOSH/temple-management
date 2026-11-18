import sqlite3
import os
import json
import random
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'temple.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            aadhar TEXT,
            city TEXT,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'devotee',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_ref TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            devotee_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            aadhar TEXT,
            age INTEGER,
            temple_name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            service_date TEXT NOT NULL,
            slot_time TEXT,
            quantity INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0.0,
            total_amount REAL DEFAULT 0.0,
            extra_details TEXT,
            payment_status TEXT DEFAULT 'Completed',
            payment_method TEXT DEFAULT 'UPI',
            booking_status TEXT DEFAULT 'Confirmed',
            checkin_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Donations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            temple_name TEXT,
            cause TEXT,
            amount REAL,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    
    # Seed default admin and devotee users if not present
    cursor.execute("SELECT id FROM users WHERE email = ?", ('admin@temple.org',))
    if not cursor.fetchone():
        admin_hash = generate_password_hash('admin123')
        cursor.execute('''
            INSERT INTO users (name, email, phone, aadhar, city, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Sri Temple Administrator', 'admin@temple.org', '9876543210', '999988887777', 'Tirupati', admin_hash, 'admin'))
        
    cursor.execute("SELECT id FROM users WHERE email = ?", ('devotee@temple.org',))
    if not cursor.fetchone():
        devotee_hash = generate_password_hash('devotee123')
        cursor.execute('''
            INSERT INTO users (name, email, phone, aadhar, city, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Smt. Lakshmi Narayana', 'devotee@temple.org', '9848022338', '543210987654', 'Vijayawada', devotee_hash, 'devotee'))
        
    # Check if there are sample bookings, if none add a few realistic ones
    cursor.execute("SELECT COUNT(*) as cnt FROM bookings")
    if cursor.fetchone()['cnt'] == 0:
        sample_bookings = [
            ('TTD-78214', 2, 'Smt. Lakshmi Narayana', 'devotee@temple.org', '9848022338', '543210987654', 42,
             'Tirumala Tirupathi Devasthanam', 'Paid Darshan (Special Entry)', '2026-11-20', '09:00 AM - 11:00 AM', 2, 350.0, 700.0,
             json.dumps({'gothram': 'Kashyapa', 'star': 'Rohini', 'reporting_gate': 'Vaikuntam Queue Complex 1'}),
             'Completed', 'UPI', 'Confirmed'),
            ('KDK-44109', 2, 'Smt. Lakshmi Narayana', 'devotee@temple.org', '9848022338', '543210987654', 42,
             'Sri Durga Malleswara Kanaka Durgamma', 'Prasad Booking', '2026-11-21', 'All Day Delivery', 4, 100.0, 400.0,
             json.dumps({'laddu_type': 'Special Ghee Laddu', 'counter': 'Prasadam Complex Counter 3'}),
             'Completed', 'Card', 'Confirmed'),
            ('SLT-19032', 2, 'Smt. Lakshmi Narayana', 'devotee@temple.org', '9848022338', '543210987654', 42,
             'Sri Lakshmi Tirupathi Amma Temple', 'Room Booking', '2026-11-25', 'Check-in: 12:00 PM', 1, 1200.0, 1200.0,
             json.dumps({'hotel': 'Hotel Govind Heights (Tirupathi)', 'room_type': 'Deluxe AC Suite'}),
             'Completed', 'NetBanking', 'Confirmed')
        ]
        
        cursor.executemany('''
            INSERT INTO bookings (
                booking_ref, user_id, devotee_name, email, phone, aadhar, age,
                temple_name, service_type, service_date, slot_time, quantity,
                unit_price, total_amount, extra_details, payment_status,
                payment_method, booking_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_bookings)
        
    conn.commit()
    conn.close()

# User Management Functions
def create_user(name, email, phone, aadhar, city, password, role='devotee'):
    try:
        conn = get_db()
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (name, email, phone, aadhar, city, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email.strip().lower(), phone, aadhar, city, password_hash, role))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id, None
    except sqlite3.IntegrityError:
        return None, "Email address is already registered."
    except Exception as e:
        return None, str(e)

def authenticate_user(email, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.strip().lower(),))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone, aadhar, city, role, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# Booking Management Functions
def generate_booking_ref(temple_name):
    prefix = "TMP"
    if "Tirupathi" in temple_name or "Tirupati" in temple_name or "TTD" in temple_name:
        prefix = "TTD"
    elif "Kanaka" in temple_name or "Durgamma" in temple_name:
        prefix = "KDK"
    elif "Lakshmi" in temple_name:
        prefix = "SLT"
    rand_num = random.randint(10000, 99999)
    return f"{prefix}-{rand_num}"

def create_booking(data, user_id=None):
    conn = get_db()
    cursor = conn.cursor()
    
    temple = data.get('temple_name', 'Tirumala Tirupathi Devasthanam')
    booking_ref = generate_booking_ref(temple)
    
    # Calculate price if not provided
    service_type = data.get('service_type', 'Paid Darshan')
    qty = int(data.get('quantity', 1) or 1)
    unit_price = float(data.get('unit_price', 0.0) or 0.0)
    
    if unit_price == 0.0:
        if 'Paid Darshan' in service_type or 'Special Entry' in service_type:
            unit_price = 350.0
        elif 'VIP' in service_type:
            unit_price = 500.0
        elif 'Room' in service_type:
            unit_price = 1200.0
        elif 'Prasad' in service_type:
            unit_price = 100.0
        elif 'Taxi' in service_type:
            unit_price = 850.0
        elif 'Vehicle' in service_type:
            unit_price = 150.0
        elif 'Free' in service_type:
            unit_price = 0.0
            
    total_amount = float(data.get('total_amount', unit_price * qty))
    
    extra_details = data.get('extra_details')
    if isinstance(extra_details, dict):
        extra_details_str = json.dumps(extra_details)
    elif isinstance(extra_details, str):
        extra_details_str = extra_details
    else:
        extra_details_str = json.dumps({})
        
    cursor.execute('''
        INSERT INTO bookings (
            booking_ref, user_id, devotee_name, email, phone, aadhar, age,
            temple_name, service_type, service_date, slot_time, quantity,
            unit_price, total_amount, extra_details, payment_status,
            payment_method, booking_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        booking_ref,
        user_id,
        data.get('name') or data.get('devotee_name', 'Devotee'),
        data.get('email', ''),
        data.get('phone', ''),
        data.get('adhar') or data.get('aadhar', ''),
        int(data.get('age', 30) or 30),
        temple,
        service_type,
        data.get('dates') or data.get('service_date', str(date.today())),
        data.get('slot_time', '09:00 AM - 11:00 AM'),
        qty,
        unit_price,
        total_amount,
        extra_details_str,
        data.get('payment_status', 'Completed'),
        data.get('payment_method', 'UPI'),
        data.get('booking_status', 'Confirmed')
    ))
    
    conn.commit()
    booking_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    new_booking = dict(cursor.fetchone())
    conn.close()
    return new_booking

def get_booking_by_ref(booking_ref):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE booking_ref = ?", (booking_ref,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_latest_booking(user_id=None, email=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    elif email:
        cursor.execute("SELECT * FROM bookings WHERE LOWER(email) = ? ORDER BY id DESC LIMIT 1", (email.strip().lower(),))
    else:
        cursor.execute("SELECT * FROM bookings ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_bookings(user_id=None, email=None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY id DESC", (user_id,))
    elif email:
        cursor.execute("SELECT * FROM bookings WHERE LOWER(email) = ? ORDER BY id DESC", (email.strip().lower(),))
    else:
        cursor.execute("SELECT * FROM bookings ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_bookings(filter_temple=None, filter_status=None, search_term=None):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM bookings WHERE 1=1"
    params = []
    
    if filter_temple and filter_temple != 'all':
        query += " AND temple_name LIKE ?"
        params.append(f"%{filter_temple}%")
    if filter_status and filter_status != 'all':
        query += " AND booking_status = ?"
        params.append(filter_status)
    if search_term:
        query += " AND (booking_ref LIKE ? OR devotee_name LIKE ? OR phone LIKE ? OR email LIKE ?)"
        term = f"%{search_term}%"
        params.extend([term, term, term, term])
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_booking_status(booking_ref, status):
    conn = get_db()
    cursor = conn.cursor()
    checkin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'Checked-In' else None
    cursor.execute('''
        UPDATE bookings 
        SET booking_status = ?, checkin_time = COALESCE(?, checkin_time)
        WHERE booking_ref = ?
    ''', (status, checkin_time, booking_ref))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_admin_dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_devotees, SUM(quantity) as total_pilgrims, SUM(total_amount) as total_revenue FROM bookings WHERE booking_status != 'Cancelled'")
    agg = cursor.fetchone()
    
    today_str = str(date.today())
    cursor.execute("SELECT COUNT(*) as today_count FROM bookings WHERE service_date LIKE ?", (f"%{today_str}%",))
    today_agg = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as checked_in FROM bookings WHERE booking_status = 'Checked-In'")
    checked_in = cursor.fetchone()['checked_in']
    
    cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE role = 'devotee'")
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('''
        SELECT temple_name, COUNT(*) as count, SUM(total_amount) as revenue 
        FROM bookings 
        GROUP BY temple_name
    ''')
    temple_breakdown = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute('''
        SELECT service_type, COUNT(*) as count 
        FROM bookings 
        GROUP BY service_type
    ''')
    service_breakdown = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        'total_bookings': agg['total_devotees'] or 0,
        'total_pilgrims': agg['total_pilgrims'] or 0,
        'total_revenue': agg['total_revenue'] or 0.0,
        'today_bookings': today_agg['today_count'] or 0,
        'checked_in': checked_in or 0,
        'total_users': total_users or 0,
        'temple_breakdown': temple_breakdown,
        'service_breakdown': service_breakdown
    }

# Initialize on import
init_db()
