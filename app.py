import sqlite3

from flask import Flask, flash, redirect, render_template as render, request, session, url_for
from functools import wraps


App = Flask(__name__)
App.secret_key = "<MAKE ONE UP>"


if __import__("os").environ.get("_A"):
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



@App.route('/')
def root():
    return redirect(url_for("login"))


@App.route("/login", methods = ["GET", "POST"])
def login():
    if request.method == "POST":
        return login_POST()

    return render("login.html")


@use_database
def login_POST(connection):
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM users WHERE username = ? AND password = ?
    """, (request.form["username"], request.form["password"])
    )

    user = cursor.fetchone()

    if not user:
        flash("Invalid Username or Password")
        return redirect(url_for("login"))

    session.update({
        "id": user["id"],
        "username": user["username"],
        "f_name": user["f_name"],
        "l_name": user["l_name"],
    })
    return redirect(url_for("dashboard"))


@App.route("/dashboard")
@use_database
def dashboard(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM todo WHERE user_id = ?", (session["id"],))
    return render("dashboard.html", user = {
        'f_name': session["f_name"],
        'l_name': session["l_name"],
        'courses': 
    })


@App.route("/todo", methods = ["GET", "POST", "DELETE"])
def todo():
    return render("todo.html")


@use_database
def todo_POST(connection):
    todo = request.form["todo"]

    if todo == "": return

    connection.execute("INSERT INTO todo (user_id, task) VALUES (?, ?)", (session["id"], todo,)) 
    connection.commit()

    return redirect(url_for("dashboard"))


@App.route("/blogs", methods = ["GET", "POST", "DELETE"])
def blogs():
    return render("blogs.html")


@App.route("/file-share", methods = ["GET", "POST", "DELETE"])
def file_share():
    return render("file-share.html")



if __name__ == "__main__":
    connection = sqlite3.connect('lms.sqlite3')
    cursor = connection.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password VARCHAR(128) NOT NULL,
            username TEXT NOT NULL UNIQUE,
            f_name TEXT NOT NULL,
            l_name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT * FROM users WHERE username = ?", ('admin',))

    if not cursor.fetchone():
        # Define test credentials (Plain Text for now)
        test_username = 'admin'
        test_password = 'password123' 
        
        # Insert without hashing
        cursor.execute('''
            INSERT INTO users (username, password, f_name, l_name)
            VALUES (?, ?, ?, ?)
        ''', (test_username, test_password, 'Test', 'User'))

    connection.commit()
    connection.close()


    App.run()
