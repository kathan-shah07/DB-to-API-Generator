import sqlite3

# Step 1: Connect to (or create) a new database file
conn = sqlite3.connect("sample.db")
cursor = conn.cursor()

# Step 2: Create two tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product TEXT NOT NULL,
    amount REAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# Step 3: Insert sample rows
cursor.executemany("""
INSERT INTO users (name, email)
VALUES (?, ?)
""", [
    ("Alice", "alice@example.com"),
    ("Bob", "bob@example.com")
])

cursor.executemany("""
INSERT INTO orders (user_id, product, amount)
VALUES (?, ?, ?)
""", [
    (1, "Laptop", 1200.50),
    (2, "Headphones", 99.99)
])

# Step 4: Save (commit) changes
conn.commit()

# Step 5: Verify by reading the data
for row in cursor.execute("SELECT * FROM users"):
    print("Users:", row)

for row in cursor.execute("SELECT * FROM orders"):
    print("Orders:", row)

# Step 6: Close connection
conn.close()

print("\n✅ Database 'sample.db' created successfully!")
