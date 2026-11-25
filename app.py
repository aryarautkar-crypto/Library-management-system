"""Library Management System: main file.
To run it:  python app.py   (then open http://127.0.0.1:5000 in a browser)
Set the environment variable FLASK_DEBUG=1 if you want auto-reload while you edit the code."""
import os
import sys
from datetime import date, timedelta

import mysql.connector
from flask import Flask, g, jsonify, redirect, render_template, url_for

import config
from db import close_db, fetch_all, fetch_one
from routes.auth import auth_bp, login_required
from routes.books import books_bp
from routes.members import members_bp
from routes.issues import issues_bp, overdue_info, plural
from routes.reports import reports_bp
from routes.profile import profile_bp
from startup_checks import ConfigError, check_config, check_database

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=7)   # browsers keep CSS and JS for a week
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,          # JavaScript cannot read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",         # the cookie is not sent with requests from other sites
    SESSION_COOKIE_SECURE=config.IS_CLOUD, # in the cloud the cookie travels only over HTTPS
)
if config.IS_CLOUD:
    check_config()                         # in the cloud, wrong settings stop the app with a clear message

app.teardown_appcontext(close_db)
app.jinja_env.filters["plural"] = plural      # in templates: {{ 3|plural('day') }} -> 3 days

# Each module is a Blueprint and is registered here
app.register_blueprint(auth_bp)      # Module 1: Authentication
app.register_blueprint(books_bp)     # Module 2: Book Management
app.register_blueprint(members_bp)   # Module 3: Member Management
app.register_blueprint(issues_bp)    # Module 4: Issue / Return + Fine
app.register_blueprint(reports_bp)   # Module 5: Reports
app.register_blueprint(profile_bp)   # Profile (name, email, password)


# ---------- Static files: a version number in the link lets the browser cache them safely ----------
def _asset_version():
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    stamps = [os.path.getmtime(os.path.join(root, name))
              for root, _, files in os.walk(folder) for name in files]
    return int(max(stamps)) if stamps else 0


ASSET_VERSION = _asset_version()


@app.context_processor
def inject_asset_version():
    return {"asset_version": ASSET_VERSION}


# ---------- Error handling: friendly pages instead of raw error messages ----------
def error_page(code, title, message):
    return render_template("error.html", code=code, title=title, message=message), code


@app.errorhandler(400)
def bad_request(err):
    return error_page(400, "Request not understood", "Some information was missing or invalid. Please go back and try again.")


@app.errorhandler(403)
def forbidden(err):
    return error_page(403, "Not allowed", "You do not have permission to open this page.")


@app.errorhandler(404)
def not_found(err):
    return error_page(404, "Page not found", "The page you asked for does not exist. It may have been moved or deleted.")


@app.errorhandler(405)
def method_not_allowed(err):
    return error_page(405, "Action not allowed", "That action is not allowed on this page.")


@app.errorhandler(mysql.connector.Error)
def database_unavailable(err):
    app.logger.error("Database error: %s", err)
    return error_page(503, "The database is not available",
                      "The library database cannot be reached right now. Make sure MySQL is running, then try again.")


@app.errorhandler(500)
def server_error(err):
    return error_page(500, "Something went wrong",
                      "An unexpected error happened and has been logged. Please try again in a moment.")


@app.route("/health")
def health():
    """Tells a monitoring tool (or a person) whether the site and the database are working."""
    try:
        fetch_one("SELECT 1 AS ok")
        return jsonify(status="ok", database="connected")
    except mysql.connector.Error:
        return jsonify(status="degraded", database="unavailable"), 503


# ---------- Pages ----------
@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    if g.user["role"] == "admin":
        today = date.today().isoformat()
        # One query for all four numbers
        stats = fetch_one(
            """SELECT
                 (SELECT COUNT(*) FROM books) AS books,
                 (SELECT COUNT(*) FROM users WHERE role = 'member') AS members,
                 (SELECT COUNT(*) FROM issues WHERE return_date IS NULL) AS issued,
                 (SELECT COUNT(*) FROM issues WHERE return_date IS NULL AND due_date < %s) AS overdue""",
            (today,),
        )
        overdue_rows = fetch_all(
            """SELECT issues.issue_id, issues.due_date, books.title, users.name AS member_name
               FROM issues
               JOIN books ON books.book_id = issues.book_id
               JOIN users ON users.user_id = issues.user_id
               WHERE issues.return_date IS NULL AND issues.due_date < %s
               ORDER BY issues.due_date LIMIT 5""",
            (today,),
        )
        for r in overdue_rows:
            r["late_days"], r["fine_now"] = overdue_info(r["due_date"])
        recent = fetch_all(
            """SELECT issues.issue_id, issues.issue_date, issues.return_date, books.title, users.name AS member_name
               FROM issues
               JOIN books ON books.book_id = issues.book_id
               JOIN users ON users.user_id = issues.user_id
               ORDER BY issues.issue_id DESC LIMIT 5"""
        )
        return render_template("dashboard.html", stats=stats, my_books=[],
                               overdue_rows=overdue_rows, recent=recent)

    my_books = fetch_all(
        """SELECT books.title, issues.issue_date, issues.due_date
           FROM issues JOIN books ON books.book_id = issues.book_id
           WHERE issues.user_id = %s AND issues.return_date IS NULL
           ORDER BY issues.due_date""",
        (g.user["user_id"],),
    )
    for b in my_books:
        b["late_days"], b["fine_now"] = overdue_info(b["due_date"])
    return render_template("dashboard.html", stats=None, my_books=my_books)


if __name__ == "__main__":
    try:
        check_config()
    except ConfigError as err:
        print("The settings in config.py are not valid:")
        for problem in err.problems:
            print("  - " + problem)
        print("Fix them and run the app again.")
        sys.exit(1)

    ok, message = check_database()
    print(message)
    if not ok:
        print("The site will still start, but pages that need the database show an error page until this is fixed.")
    app.run()
