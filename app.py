from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
from datetime import datetime
import os

app = Flask(__name__, static_folder='.')
app.secret_key = secrets.token_hex(32)
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'http://127.0.0.1:5000'])

DATABASE = 'aibs.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
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
            password TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('Farmer', 'Vendor', 'Admin')),
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'blocked')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Listings table (farmer crops)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            farmer_name TEXT NOT NULL,
            crop TEXT NOT NULL,
            quantity_kg REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'Accepted', 'Rejected')),
            accepted_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accepted_at TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES users(id),
            FOREIGN KEY (accepted_by) REFERENCES users(id)
        )
    ''')
    
    # Supplies table (vendor products)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('Fertilizer', 'Pesticide', 'Seeds')),
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vendor_id) REFERENCES users(id)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER NOT NULL,
            farmer_id INTEGER NOT NULL,
            vendor_id INTEGER NOT NULL,
            crop TEXT NOT NULL,
            quantity_kg REAL NOT NULL,
            price_per_kg REAL NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'Success' CHECK(status IN ('Success', 'Pending', 'Failed')),
            method TEXT DEFAULT 'Online',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES listings(id),
            FOREIGN KEY (farmer_id) REFERENCES users(id),
            FOREIGN KEY (vendor_id) REFERENCES users(id)
        )
    ''')
    
    # Create default admin
    admin_password = hash_password('admin123')
    cursor.execute('''
        INSERT OR IGNORE INTO users (name, email, password, type)
        VALUES ('Admin', 'admin@aibs.com', ?, 'Admin')
    ''', (admin_password,))
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Serve HTML files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return "File not found", 404

# Auth endpoints
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('type')
    
    if not all([name, email, password, user_type]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        hashed_pw = hash_password(password)
        cursor.execute('''
            INSERT INTO users (name, email, password, type, last_login)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, hashed_pw, user_type, datetime.now()))
        conn.commit()
        
        user_id = cursor.lastrowid
        session['user_id'] = user_id
        session['user_type'] = user_type
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'name': name,
                'email': email,
                'type': user_type
            }
        })
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists'}), 400
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('type')
    
    conn = get_db()
    cursor = conn.cursor()
    
    hashed_pw = hash_password(password)
    cursor.execute('''
        SELECT * FROM users WHERE email = ? AND password = ?
    ''', (email, hashed_pw))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if user['status'] == 'blocked':
        conn.close()
        return jsonify({'error': 'Account is blocked'}), 403
    
    if user['type'] != user_type:
        conn.close()
        return jsonify({'error': f'Account is registered as {user["type"]}'}), 403
    
    # Update last login
    cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                   (datetime.now(), user['id']))
    conn.commit()
    conn.close()
    
    session['user_id'] = user['id']
    session['user_type'] = user['type']
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'type': user['type']
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, type FROM users WHERE id = ?',
                   (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'type': user['type']
    })

# Listings endpoints
@app.route('/api/listings', methods=['GET'])
def get_listings():
    conn = get_db()
    cursor = conn.cursor()
    
    status = request.args.get('status')
    farmer_id = request.args.get('farmer_id')
    
    query = 'SELECT * FROM listings WHERE 1=1'
    params = []
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    
    if farmer_id:
        query += ' AND farmer_id = ?'
        params.append(farmer_id)
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    listings = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(l) for l in listings])

@app.route('/api/listings', methods=['POST'])
def create_listing():
    if 'user_id' not in session or session['user_type'] != 'Farmer':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    # Get farmer name
    cursor.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],))
    farmer = cursor.fetchone()
    
    cursor.execute('''
        INSERT INTO listings (farmer_id, farmer_name, crop, quantity_kg, price_per_kg)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], farmer['name'], data['crop'],
          data['quantityKg'], data['pricePerKg']))
    
    listing_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': listing_id})

@app.route('/api/listings/<int:listing_id>', methods=['PUT'])
def update_listing(listing_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    update_fields = []
    params = []
    
    if 'status' in data:
        update_fields.append('status = ?')
        params.append(data['status'])
    
    if data.get('status') == 'Accepted':
        update_fields.append('accepted_by = ?')
        update_fields.append('accepted_at = ?')
        params.extend([session['user_id'], datetime.now()])
    
    params.append(listing_id)
    
    cursor.execute(f'''
        UPDATE listings SET {', '.join(update_fields)}
        WHERE id = ?
    ''', params)
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# Supplies endpoints
@app.route('/api/supplies', methods=['GET'])
def get_supplies():
    conn = get_db()
    cursor = conn.cursor()
    
    vendor_id = request.args.get('vendor_id')
    
    if vendor_id:
        cursor.execute('SELECT * FROM supplies WHERE vendor_id = ? ORDER BY created_at DESC',
                       (vendor_id,))
    else:
        cursor.execute('SELECT * FROM supplies ORDER BY created_at DESC')
    
    supplies = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(s) for s in supplies])

@app.route('/api/supplies', methods=['POST'])
def create_supply():
    if 'user_id' not in session or session['user_type'] != 'Vendor':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    # Get vendor name
    cursor.execute('SELECT name FROM users WHERE id = ?', (session['user_id'],))
    vendor = cursor.fetchone()
    
    cursor.execute('''
        INSERT INTO supplies (vendor_id, vendor_name, name, category, price)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], vendor['name'], data['name'],
          data['category'], data['price']))
    
    supply_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': supply_id})

# Transactions endpoints
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    conn = get_db()
    cursor = conn.cursor()
    
    vendor_id = request.args.get('vendor_id')
    
    if vendor_id:
        cursor.execute('SELECT * FROM transactions WHERE vendor_id = ? ORDER BY timestamp DESC',
                       (vendor_id,))
    else:
        cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC')
    
    transactions = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(t) for t in transactions])

@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    if 'user_id' not in session or session['user_type'] != 'Vendor':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO transactions (listing_id, farmer_id, vendor_id, crop,
                                 quantity_kg, price_per_kg, amount, status, method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['listingId'], data['farmerId'], session['user_id'],
          data['crop'], data['quantityKg'], data['pricePerKg'],
          data['amount'], 'Success', 'Online'))
    
    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': transaction_id})

# Admin endpoints
@app.route('/api/admin/users', methods=['GET'])
def get_users():
    if 'user_id' not in session or session['user_type'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, type, status, created_at, last_login FROM users')
    users = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(u) for u in users])

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    if 'user_id' not in session or session['user_type'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET status = ? WHERE id = ?',
                   (data['status'], user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/stats', methods=['GET'])
def get_stats():
    if 'user_id' not in session or session['user_type'] != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    # User stats
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE status = 'active' AND type != 'Admin'")
    active_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE status = 'blocked'")
    blocked_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE type = 'Farmer'")
    farmers = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE type = 'Vendor'")
    vendors = cursor.fetchone()['count']
    
    # Transaction stats
    cursor.execute("SELECT COUNT(*) as count, SUM(amount) as total FROM transactions WHERE status = 'Success'")
    tx_data = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'Pending'")
    pending_tx = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE status = 'Failed'")
    failed_tx = cursor.fetchone()['count']
    
    conn.close()
    
    return jsonify({
        'activeUsers': active_users,
        'blockedUsers': blocked_users,
        'farmers': farmers,
        'vendors': vendors,
        'totalTransactions': tx_data['count'] or 0,
        'successfulTransactions': tx_data['count'] or 0,
        'totalRevenue': tx_data['total'] or 0,
        'pendingTransactions': pending_tx,
        'failedTransactions': failed_tx
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  AIBS - Agri Integrated Business System")
    print("="*50)
    print("\nInitializing database...")
    init_db()
    print("\n✓ Server starting on http://localhost:5000")
    print("\nDefault Admin Credentials:")
    print("  Email: admin@aibs.com")
    print("  Password: admin123")
    print("\n" + "="*50 + "\n")
    app.run(debug=True, port=5000, host='0.0.0.0')