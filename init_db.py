import sqlite3

DATABASE = "event_registration.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # ---------- USERS ----------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')

    # ---------- EVENTS ----------
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT,
        date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        venue TEXT NOT NULL,
        last_date TEXT NOT NULL,
        fee REAL,
        
        is_team_event TEXT,
        team_size INTEGER,
        organizer_name TEXT NOT NULL,
        organizer_contact TEXT NOT NULL,
        status TEXT NOT NULL
    )
''')


    # ---------- REGISTRATIONS WITH FULL DETAILS ----------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            full_name TEXT,
            mobile TEXT,
            email TEXT,
            college TEXT,
            year TEXT,
            branch TEXT,
            payment_image TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')

    conn.commit()
    conn.close()

    print("✅ Database initialized successfully")

if __name__ == "__main__":
    init_db()
