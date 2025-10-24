import sqlite3
from datetime import datetime

DB_FILE = "chat_sessions.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT,
                    last_active TIMESTAMP
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    type TEXT,
                    content TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )''')
    conn.commit()
    conn.close()
    
def save_session(session_id, name=None):
    now = datetime.utcnow()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Insert if not exists
    c.execute("INSERT OR IGNORE INTO sessions (session_id, name, last_active) VALUES (?, ?, ?)",
              (session_id, name, now))
    
    # Only update name if provided
    if name is not None:
        c.execute("UPDATE sessions SET last_active = ?, name = ? WHERE session_id = ?",
                  (now, name, session_id))
    else:
        c.execute("UPDATE sessions SET last_active = ? WHERE session_id = ?",
                  (now, session_id))
    
    conn.commit()
    conn.close()





def save_message(session_id, type_, content):
    now = datetime.utcnow()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, type, content, timestamp) VALUES (?, ?, ?, ?)",
              (session_id, type_, content, now))
    conn.commit()
    conn.close()

def get_messages(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT type, content FROM messages WHERE session_id = ? ORDER BY timestamp", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"type": row[0], "content": row[1]} for row in rows]

def get_sessions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT session_id, name FROM sessions ORDER BY last_active DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1] or "New Chat"} for row in rows]

def delete_session(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
