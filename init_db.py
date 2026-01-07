import sqlite3

# Database file name
DATABASE = "event_registration.db"

def init_db():
    # Connect to the SQLite database (it will be created if it doesn’t exist)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create users table (stores login info + role: admin or participant)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # Create events table (stores event details created by admins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT,              -- ✅ Added date column
            fee REAL,
            max_members INTEGER,    -- ✅ Added max_members column
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')

    # Create registrations table (stores which user registered for which event)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')

    # Save changes and close
    conn.commit()
    conn.close()

    print("✅ Database initialized with tables: users, events, registrations")

# Run the function if this file is executed directly
if __name__ == "__main__":
    init_db()
