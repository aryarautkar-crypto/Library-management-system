"""Module 5: Reports (sirf admin ke liye)."""
from datetime import date
from flask import Blueprint, render_template
from db import fetch_all, fetch_one
from routes.auth import admin_required
from routes.issues import overdue_info

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@admin_required
def reports():
    today = date.today().isoformat()

    issued_now = fetch_one("SELECT COUNT(*) AS total FROM issues WHERE return_date IS NULL")["total"]
    fine_collected = fetch_one(
        "SELECT COALESCE(SUM(fine), 0) AS total FROM issues WHERE return_date IS NOT NULL")["total"]

    overdue = fetch_all(
        """SELECT issues.issue_id, issues.due_date, books.title, users.name AS member_name, users.email
           FROM issues
           JOIN books ON books.book_id = issues.book_id
           JOIN users ON users.user_id = issues.user_id
           WHERE issues.return_date IS NULL AND issues.due_date < %s
           ORDER BY issues.due_date""",
        (today,),
    )
    for row in overdue:
        row["late_days"], row["fine_now"] = overdue_info(row["due_date"])

    top_books = fetch_all(
        """SELECT books.title, books.author, COUNT(*) AS times
           FROM issues JOIN books ON books.book_id = issues.book_id
           GROUP BY books.book_id, books.title, books.author
           ORDER BY times DESC, books.title
           LIMIT 5""")
    out_of_stock = fetch_all("SELECT title, author FROM books WHERE available_copies = 0 ORDER BY title")

    return render_template("reports.html", issued_now=issued_now, fine_collected=int(fine_collected),
                           overdue=overdue, top_books=top_books, out_of_stock=out_of_stock)
