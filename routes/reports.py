"""Module 5: Reports (admin only)."""
from datetime import date
from flask import Blueprint, render_template
from db import fetch_all, fetch_one
from routes.auth import admin_required
from routes.issues import overdue_info

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

OVERDUE_LIMIT = 50    # the overdue table shows the longest overdue loans first


@reports_bp.route("/")
@admin_required
def reports():
    today = date.today().isoformat()

    counts = fetch_one(
        """SELECT
             (SELECT COUNT(*) FROM issues WHERE return_date IS NULL) AS issued_now,
             (SELECT COUNT(*) FROM issues WHERE return_date IS NULL AND due_date < %s) AS overdue_count,
             (SELECT COALESCE(SUM(fine), 0) FROM issues WHERE return_date IS NOT NULL) AS fine_collected""",
        (today,),
    )

    overdue = fetch_all(
        """SELECT issues.issue_id, issues.due_date, books.title, users.name AS member_name, users.email
           FROM issues
           JOIN books ON books.book_id = issues.book_id
           JOIN users ON users.user_id = issues.user_id
           WHERE issues.return_date IS NULL AND issues.due_date < %s
           ORDER BY issues.due_date LIMIT %s""",
        (today, OVERDUE_LIMIT),
    )
    for row in overdue:
        row["late_days"], row["fine_now"] = overdue_info(row["due_date"])

    top_books = fetch_all(
        """SELECT books.title, books.author, COUNT(*) AS times
           FROM issues JOIN books ON books.book_id = issues.book_id
           GROUP BY books.book_id, books.title, books.author
           ORDER BY times DESC, books.title
           LIMIT 5""")
    out_of_stock = fetch_all(
        "SELECT title, author FROM books WHERE available_copies = 0 ORDER BY title LIMIT 50")

    return render_template(
        "reports.html", issued_now=counts["issued_now"], overdue_count=counts["overdue_count"],
        fine_collected=int(counts["fine_collected"]), overdue=overdue,
        top_books=top_books, out_of_stock=out_of_stock)
