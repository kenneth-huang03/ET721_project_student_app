import hashlib
import os
import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for, send_from_directory
from functools import wraps
from werkzeug.utils import secure_filename


App = Flask(__name__)
App.secret_key = "<MAKE ONE UP>"

UPLOAD_FOLDER = os.path.join(App.static_folder, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


if os.environ.get("_A"):
    from werkzeug.middleware.proxy_fix import ProxyFix
    App.wsgi_app = ProxyFix(App.wsgi_app, x_prefix=1)


def use_database(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        connection = sqlite3.connect("lms.sqlite3")
        connection.row_factory = sqlite3.Row

        try:
            return method(connection, *args, **kwargs)
        finally:
            connection.close()
    return wrapper


def login_required(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        if "id" not in session:
            return redirect(url_for("login"))
        return method(*args, **kwargs)
    return wrapper


@App.route('/')
def root():
    return redirect(url_for("login"))


@App.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return login_POST()

    return render_template("login.html")


@use_database
def login_POST(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM users WHERE username = ? AND password = ?
    """, (request.form["username"], request.form["password"]))

    user = cursor.fetchone()

    if not user:
        flash("Invalid Username or Password")
        return redirect(url_for("login"))

    session.update({
        "id":       user["id"],
        "username": user["username"],
        "f_name":   user["f_name"],
        "l_name":   user["l_name"],
    })
    return redirect(url_for("dashboard"))


@App.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@App.route("/dashboard")
@login_required
@use_database
def dashboard(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM todo WHERE user_id = ? AND done = 0 LIMIT 5", (session["id"],))
    todos = cursor.fetchall()
    return render_template("dashboard.html", user={
        "f_name":  session["f_name"],
        "l_name":  session["l_name"],
    }, todos=todos)


@App.route("/todo", methods=["GET", "POST"])
@login_required
def todo():
    if request.method == "POST":
        return todo_POST()
    return todo_GET()


@use_database
def todo_GET(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM todo WHERE user_id = ? ORDER BY id DESC", (session["id"],))
    todos = cursor.fetchall()
    return render_template("todo.html", todos=todos)


@use_database
def todo_POST(connection):
    task = request.form.get("todo", "").strip()

    if not task:
        flash("Task cannot be empty.")
        return redirect(url_for("todo"))

    connection.execute(
        "INSERT INTO todo (user_id, task, done) VALUES (?, ?, 0)",
        (session["id"], task)
    )
    connection.commit()
    return redirect(url_for("todo"))


@App.route("/todo/<int:todo_id>/done", methods=["POST"])
@login_required
@use_database
def todo_done(connection, todo_id):
    connection.execute(
        "UPDATE todo SET done = 1 WHERE id = ? AND user_id = ?",
        (todo_id, session["id"])
    )
    connection.commit()
    return redirect(url_for("todo"))


@App.route("/todo/<int:todo_id>/delete", methods=["POST"])
@login_required
@use_database
def todo_delete(connection, todo_id):
    connection.execute(
        "DELETE FROM todo WHERE id = ? AND user_id = ?",
        (todo_id, session["id"])
    )
    connection.commit()
    return redirect(url_for("todo"))


@App.route("/blogs", methods=["GET", "POST"])
@login_required
def blogs():
    if request.method == "POST":
        return blogs_POST()
    return blogs_GET()


@use_database
def blogs_GET(connection):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT blogs.*, users.f_name, users.l_name, users.username
        FROM blogs
        JOIN users ON blogs.user_id = users.id
        ORDER BY blogs.id DESC
    """)
    posts = cursor.fetchall()
    return render_template("blogs.html", posts=posts)


@use_database
def blogs_POST(connection):
    title   = request.form.get("title",   "").strip()
    content = request.form.get("content", "").strip()

    if not title or not content:
        flash("Title and content are required.")
        return redirect(url_for("blogs"))

    connection.execute(
        "INSERT INTO blogs (user_id, title, content) VALUES (?, ?, ?)",
        (session["id"], title, content)
    )
    connection.commit()
    return redirect(url_for("blogs"))


@App.route("/blogs/<int:post_id>/delete", methods=["POST"])
@login_required
@use_database
def blog_delete(connection, post_id):
    connection.execute(
        "DELETE FROM blogs WHERE id = ? AND user_id = ?",
        (post_id, session["id"])
    )
    connection.commit()
    return redirect(url_for("blogs"))


EXT_IMAGE   = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff", "heic"}
EXT_PDF     = {"pdf"}
EXT_TEXT    = {"txt", "csv", "tsv", "md", "tex", "bib", "ipynb", "json", "xml", "log"}
EXT_AUDIO   = {"mp3", "m4a", "wav", "ogg"}
EXT_VIDEO   = {"mp4", "mov", "webm", "ogv"}
EXT_OFFICE  = {"doc", "docx", "odt", "rtf", "xls", "xlsx", "ods", "ppt", "pptx", "odp"}
EXT_ARCHIVE = {"zip", "tar", "gz", "7z"}

ALLOWED_EXTENSIONS = EXT_IMAGE | EXT_PDF | EXT_TEXT | EXT_OFFICE | EXT_ARCHIVE

PREVIEW_TEXT_MAX_BYTES = 256 * 1024


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def preview_kind(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in EXT_IMAGE: return "image"
    if ext in EXT_PDF:   return "pdf"
    if ext in EXT_TEXT:  return "text"
    if ext in EXT_AUDIO: return "audio"
    if ext in EXT_VIDEO: return "video"
    return "binary"


def hashed_storage_name(file_storage, original_filename):
    hasher = hashlib.sha256()
    while True:
        chunk = file_storage.stream.read(8192)
        if not chunk: break

        hasher.update(chunk)
    file_storage.stream.seek(0)

    return hasher.hexdigest()


@App.route("/file-share", methods=["GET", "POST"])
@login_required
def file_share():
    if request.method == "POST":
        return file_share_POST()
    return file_share_GET()


@use_database
def file_share_GET(connection):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT files.*, users.f_name, users.l_name, users.username
        FROM files
        JOIN users ON files.user_id = users.id
        ORDER BY files.id DESC
    """)
    files = cursor.fetchall()
    return render_template(
        "file-share.html",
        files=files,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
    )


@use_database
def file_share_POST(connection):
    description = request.form.get("description", "").strip()
    file        = request.files.get("file")

    if not file or file.filename == "":
        flash("No file selected.")
        return redirect(url_for("file_share"))

    if not allowed_file(file.filename):
        flash("File type not allowed.")
        return redirect(url_for("file_share"))

    original_name = secure_filename(file.filename) or "upload"
    stored_name   = hashed_storage_name(file, original_name)
    save_path     = os.path.join(UPLOAD_FOLDER, stored_name)

    if not os.path.exists(save_path):
        file.save(save_path)

    connection.execute(
        "INSERT INTO files (user_id, stored_name, filename, description) VALUES (?, ?, ?, ?)",
        (session["id"], stored_name, original_name, description)
    )
    connection.commit()
    return redirect(url_for("file_share"))


@App.route("/file-share/<int:file_id>/delete", methods=["POST"])
@login_required
@use_database
def file_delete(connection, file_id):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT stored_name FROM files WHERE id = ? AND user_id = ?",
        (file_id, session["id"])
    )
    row = cursor.fetchone()
    if row is None:
        return redirect(url_for("file_share"))

    stored_name = row["stored_name"]
    connection.execute("DELETE FROM files WHERE id = ?", (file_id,))
    connection.commit()

    cursor.execute(
        "SELECT 1 FROM files WHERE stored_name = ? LIMIT 1",
        (stored_name,)
    )
    if cursor.fetchone() is None:
        path = os.path.join(UPLOAD_FOLDER, stored_name)
        if os.path.exists(path):
            os.remove(path)

    return redirect(url_for("file_share"))


@App.route("/file-share/<int:file_id>")
@login_required
@use_database
def file_view(connection, file_id):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT files.*, users.f_name, users.l_name, users.username
        FROM files
        JOIN users ON files.user_id = users.id
        WHERE files.id = ?
    """, (file_id,))
    file_row = cursor.fetchone()
    if file_row is None:
        abort(404)

    kind         = preview_kind(file_row["filename"])
    text_preview = None
    if kind == "text":
        path = os.path.join(UPLOAD_FOLDER, file_row["stored_name"])
        try:
            with open(path, "rb") as fh:
                raw = fh.read(PREVIEW_TEXT_MAX_BYTES + 1)
            text_preview = {
                "content":   raw[:PREVIEW_TEXT_MAX_BYTES].decode("utf-8", errors="replace"),
                "truncated": len(raw) > PREVIEW_TEXT_MAX_BYTES,
            }
        except OSError:
            text_preview = None

    return render_template(
        "file-view.html",
        file=file_row,
        kind=kind,
        text_preview=text_preview,
    )


@App.route("/uploads/<stored_name>")
@login_required
@use_database
def uploaded_file(connection, stored_name):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT filename FROM files WHERE stored_name = ? LIMIT 1",
        (stored_name,)
    )
    row = cursor.fetchone()
    if not row:
        abort(404)

    response = send_from_directory(
        UPLOAD_FOLDER,
        stored_name,
        download_name=row["filename"],
        as_attachment=False,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@App.route("/uploads/<stored_name>/download")
@login_required
@use_database
def download_file(connection, stored_name):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT filename FROM files WHERE stored_name = ? LIMIT 1",
        (stored_name,)
    )
    row = cursor.fetchone()
    if not row:
        abort(404)

    response = send_from_directory(
        UPLOAD_FOLDER,
        stored_name,
        download_name=row["filename"],
        as_attachment=True,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


if __name__ == "__main__":
    if not os.path.exists("lms.sqlite3"):
        connection = sqlite3.connect("lms.sqlite3")
        cursor     = connection.cursor()

        cursor.execute('''
            CREATE TABLE users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                password VARCHAR(128) NOT NULL,
                username TEXT NOT NULL UNIQUE,
                f_name   TEXT NOT NULL,
                l_name   TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE todo (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task    TEXT NOT NULL,
                done    INTEGER NOT NULL DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE blogs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                title      TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')

        cursor.execute('''
            CREATE TABLE files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                stored_name TEXT NOT NULL,
                filename    TEXT NOT NULL,
                description TEXT,
                uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')

        cursor.executemany('''
            INSERT INTO users (username, password, f_name, l_name)
            VALUES (?, ?, ?, ?)
        ''', [
            ('admin',     'admin',     'Admin', 'User'),
            ('professor', 'professor', 'Prof',  'Smith'),
            ('student',   'student',   'John',  'Doe'),
        ])

        connection.commit()
        connection.close()


    App.run()
