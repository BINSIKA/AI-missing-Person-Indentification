import sqlite3
import json

DB_FILE = "missing_persons.db"

# --- DATABASE CONNECTION ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- INITIALIZE DATABASE ---
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            phone TEXT,
            image_filename TEXT NOT NULL,
            encoding_json TEXT,
            latitude REAL,
            longitude REAL
        )
    ''')
    # --- ADD SIGHTINGS TABLE ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS sightings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            image_filename TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        )
    ''')
    conn.commit()
    conn.close()

# --- ADD PERSON ---
def add_person(name, age, gender, height, weight, image_filename, face_encoding, phone, latitude=None, longitude=None):
    conn = get_db_connection()
    c = conn.cursor()
    encoding_json = json.dumps(face_encoding)
    c.execute("""
        INSERT INTO persons (name, age, gender, height, weight, phone, image_filename, encoding_json, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, age, gender, height, weight, phone, image_filename, encoding_json, latitude, longitude))
    conn.commit()
    conn.close()

# --- GET ALL PERSONS ---
def get_all_persons():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM persons")
    rows = c.fetchall()
    conn.close()

    persons = []
    for row in rows:
        person_dict = dict(row)
        encoding = person_dict.get('encoding_json')
        person_dict['face_encoding'] = json.loads(encoding) if encoding else None
        del person_dict['encoding_json']
        persons.append(person_dict)

    return persons

# --- GET PERSON BY ID ---
def get_person_by_id(pid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM persons WHERE id=?", (pid,))
    row = c.fetchone()
    conn.close()

    if row:
        person_dict = dict(row)
        encoding = person_dict.get('encoding_json')
        person_dict['face_encoding'] = json.loads(encoding) if encoding else None
        del person_dict['encoding_json']
        return person_dict

    return None

# --- LOG SIGHTING (NEW FUNCTION) ---
def log_sighting(person_id, image_filename, latitude=None, longitude=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO sightings (person_id, image_filename, latitude, longitude)
        VALUES (?, ?, ?, ?)
    """, (person_id, image_filename, latitude, longitude))
    sighting_id = c.lastrowid
    conn.commit()
    conn.close()
    return sighting_id

# --- GET SIGHTING BY ID (NEW FUNCTION) ---
def get_sighting_by_id(sid):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM sightings WHERE id=?", (sid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None