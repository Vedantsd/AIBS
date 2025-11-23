import sqlite3
import os

DATABASE = 'aibs.db'

print("="*50)
print("  AIBS Database Migration")
print("="*50)

if not os.path.exists(DATABASE):
    print("❌ Database 'aibs.db' not found!")
    print("   Please run app.py first to create the database.")
    exit(1)

print(f"\n📊 Migrating database: {DATABASE}")
print("   This will update the supplies table to support Google Sheets integration\n")

response = input("Continue? (yes/no): ")
if response.lower() != 'yes':
    print("Migration cancelled.")
    exit(0)

try:
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("\n1️⃣  Creating backup of supplies table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS supplies_backup AS 
        SELECT * FROM supplies
    ''')
    
    print("2️⃣  Dropping old supplies table...")
    cursor.execute('DROP TABLE IF EXISTS supplies')
    
    print("3️⃣  Creating new supplies table (without constraints)...")
    cursor.execute('''
        CREATE TABLE supplies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vendor_id) REFERENCES users(id)
        )
    ''')
    
    print("4️⃣  Restoring data from backup...")
    cursor.execute('''
        INSERT INTO supplies (id, vendor_id, vendor_name, name, category, price, created_at)
        SELECT id, vendor_id, vendor_name, name, category, price, created_at
        FROM supplies_backup
    ''')
    
    print("5️⃣  Cleaning up backup table...")
    cursor.execute('DROP TABLE supplies_backup')
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ Migration completed successfully!")
    print("="*50)
    print("\nYou can now:")
    print("  1. Restart the server: python app.py")
    print("  2. Login as vendor")
    print("  3. Add products from the Google Sheets list")
    print("\n")

except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    print("\nTo start fresh, delete aibs.db and restart app.py")
    if conn:
        conn.rollback()
        conn.close()