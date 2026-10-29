"""Library Management System: main file.
Chalane ke liye:  python app.py   (browser me http://127.0.0.1:5000)"""
from datetime import date
from flask import Flask, g, redirect, render_template, url_for
import config
from db import close_db, fetch_all, fetch_one
from routes.auth import auth_bp, login_required
from routes.books import books_bp
from routes.members import members_bp
from routes.issues import issues_bp, overdue_info
from routes.reports import reports_bp
from routes.profile import profile_bp

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

app.teardown_appcontext(close_db)

# Har module ka Blueprint yaha register hota hai
app.register_blueprint(auth_bp)      # Module 1: Authentication
app.register_blueprint(books_bp)     # Module 2: Book Management
app.register_blueprint(members_bp)   # Module 3: Member Management
app.register_blueprint(issues_bp)    # Module 4: Issue / Return + Fine
app.register_blueprint(reports_bp)   # Module 5: Reports
app.register_blueprint(profile_bp)   # Profile (naam, email, password)


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    if g.user["role"] == "admin":
        today = date.today().isoformat()
        stats = {
            "books": fetch_one("SELECT COUNT(*) AS total FROM books")["total"],
            "members": fetch_one("SELECT COUNT(*) AS total FROM users WHERE role = 'member'")["total"],
            "issued": fetch_one("SELECT COUNT(*) AS total FROM issues WHERE return_date IS NULL")["total"],
            "overdue": fetch_one(
                "SELECT COUNT(*) AS total FROM issues WHERE return_date IS NULL AND due_date < %s",
                (today,))["total"],
        }
        return render_template("dashboard.html", stats=stats, my_books=[])

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
    app.run(debug=True)
