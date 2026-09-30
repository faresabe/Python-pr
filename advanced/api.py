import sqlite3
import time
import bcrypt
import secrets
import json
from http.server import HTTPServer, BaseHTTPRequestHandler


# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
db = "notes.db"
host = "localhost"
port = 8000
SESSION_DURATION = 60 * 30   # 30 min (short, for testing)


# ──────────────────────────────────────────────────────
# DATABASE CONNECTION
# ──────────────────────────────────────────────────────
conn = sqlite3.connect(db, check_same_thread=False)
conn.row_factory = sqlite3.Row


def init_db():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            created_at    INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            title      TEXT    NOT NULL,
            body       TEXT    NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT    NOT NULL UNIQUE,
            user_id    INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()


# ──────────────────────────────────────────────────────
# USER FUNCTIONS
# ──────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))


def create_user(username, password):
    cursor = conn.execute(
        """
        INSERT INTO users (username, password_hash, created_at)
        VALUES (?, ?, ?)
        """,
        (username, hash_password(password), int(time.time()))
    )
    conn.commit()
    return cursor.lastrowid


def get_user_by_username(username):
    return conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()


def get_user_by_id(user_id):
    return conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()


# ──────────────────────────────────────────────────────
# NOTE FUNCTIONS
# ──────────────────────────────────────────────────────
def create_note(user_id, title, body):
    cursor = conn.execute(
        """
        INSERT INTO notes (user_id, title, body, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, title, body, int(time.time()))
    )
    conn.commit()
    return cursor.lastrowid


def list_notes(user_id):
    return conn.execute(
        """
        SELECT * FROM notes
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()


def get_note(note_id):
    return conn.execute(
        "SELECT * FROM notes WHERE id = ?",
        (note_id,)
    ).fetchone()


def delete_note(note_id):
    cursor = conn.execute(
        "DELETE FROM notes WHERE id = ?",
        (note_id,)
    )
    conn.commit()
    return cursor.rowcount > 0


# ──────────────────────────────────────────────────────
# SESSION FUNCTIONS
# ──────────────────────────────────────────────────────
def create_session(user_id):
    session_id = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + SESSION_DURATION
    conn.execute(
        """
        INSERT INTO sessions (session_id, user_id, expires_at)
        VALUES (?, ?, ?)
        """,
        (session_id, user_id, expires_at)
    )
    conn.commit()
    return session_id


def get_user_by_session(session_id):
    return conn.execute(
        """
        SELECT users.id, users.username
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.session_id = ?
          AND sessions.expires_at > ?
        """,
        (session_id, int(time.time()))
    ).fetchone()


def delete_session(session_id):
    conn.execute(
        "DELETE FROM sessions WHERE session_id = ?",
        (session_id,)
    )
    conn.commit()


# ──────────────────────────────────────────────────────
# HTTP HANDLER
# ──────────────────────────────────────────────────────
class RequestHandler(BaseHTTPRequestHandler):

    # ── helpers ──────────────────────────────────────
    def send_json(self, status, data, headers=None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for name, value in headers.items():
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = self.headers.get("Content-Length")
        if not length:
            return None
        try:
            length = int(length)
        except ValueError:
            return None
        if length > 10_000:
            return None

        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def get_session_id(self):
        cookie = self.headers.get("Cookie")
        if not cookie:
            return None
        for item in cookie.split(";"):
            if "=" not in item:
                continue
            key, value = item.strip().split("=", 1)
            if key == "session_id":
                return value
        return None

    def get_current_user(self):
        session_id = self.get_session_id()
        if not session_id:
            return None
        return get_user_by_session(session_id)

    # ── GET ──────────────────────────────────────────
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        if path == "/api/me":
            user = self.get_current_user()
            if user is None:
                self.send_json(401, {"error": "Not logged in."})
                return
            self.send_json(200, {"id": user["id"], "username": user["username"]})
            return

        if path == "/api/notes":
            user = self.get_current_user()
            if user is None:
                self.send_json(401, {"error": "Not logged in."})
                return

            rows = list_notes(user["id"])
            notes = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "body": row["body"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
            self.send_json(200, {"notes": notes})
            return

        self.send_json(404, {"error": "Not found."})

    # ── POST ─────────────────────────────────────────
    def do_POST(self):
        path = self.path.split("?", 1)[0]

        # register
        if path == "/api/register":
            data = self.read_json()
            if data is None:
                self.send_json(400, {"error": "Invalid JSON."})
                return

            username = data.get("username")
            password = data.get("password")
            if not username or not password:
                self.send_json(400, {"error": "username and password are required."})
                return

            try:
                user_id = create_user(username, password)
            except sqlite3.IntegrityError:
                self.send_json(409, {"error": "Username already taken."})
                return

            self.send_json(201, {"user_id": user_id})
            return

        # login
        if path == "/api/login":
            data = self.read_json()
            if data is None:
                self.send_json(400, {"error": "Invalid JSON."})
                return

            username = data.get("username")
            password = data.get("password")

            user = get_user_by_username(username)
            if user is None or not verify_password(password, user["password_hash"]):
                self.send_json(401, {"error": "Invalid username or password."})
                return

            session_id = create_session(user["id"])
            self.send_json(
                200,
                {"message": "Logged in.", "username": user["username"]},
                headers={"Set-Cookie": f"session_id={session_id}; HttpOnly; Path=/"}
            )
            return

        # create note
        if path == "/api/notes":
            user = self.get_current_user()
            if user is None:
                self.send_json(401, {"error": "Not logged in."})
                return

            data = self.read_json()
            if data is None:
                self.send_json(400, {"error": "Invalid JSON."})
                return

            title = data.get("title")
            body = data.get("body")
            if not title or not body:
                self.send_json(400, {"error": "title and body are required."})
                return

            note_id = create_note(user["id"], title, body)
            self.send_json(201, {"note_id": note_id})
            return

        # logout
        if path == "/api/logout":
            session_id = self.get_session_id()
            if session_id:
                delete_session(session_id)
            self.send_json(
                200,
                {"message": "Logged out."},
                headers={"Set-Cookie": "session_id=; HttpOnly; Path=/; Max-Age=0"}
            )
            return

        self.send_json(404, {"error": "Not found."})

    # ── DELETE ───────────────────────────────────────
    def do_DELETE(self):
        path = self.path.split("?", 1)[0]

        # /api/notes/<id>
        if path.startswith("/api/notes/"):
            user = self.get_current_user()
            if user is None:
                self.send_json(401, {"error": "Not logged in."})
                return

            raw_id = path[len("/api/notes/"):]
            if not raw_id.isdigit():
                self.send_json(400, {"error": "Invalid note id."})
                return
            note_id = int(raw_id)

            note = get_note(note_id)
            if note is None:
                self.send_json(404, {"error": "Note not found."})
                return

            # ownership check: only the owner may delete
            if note["user_id"] != user["id"]:
                self.send_json(403, {"error": "Not your note."})
                return

            delete_note(note_id)
            self.send_json(200, {"message": "Deleted."})
            return

        self.send_json(404, {"error": "Not found."})


# ──────────────────────────────────────────────────────
# ENTRYPOINT
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    server = HTTPServer((host, port), RequestHandler)
    print(f"Server running at http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
        conn.close()