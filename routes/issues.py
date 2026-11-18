"""Module 4: Issue / Return + Fine.
Admin: issues and returns books. Member: sees only their own loan history."""
from datetime import date, datetime, timedelta
import mysql.connector
from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)
from db import fetch_all, fetch_one, get_db
from pagination import paginate
from routes.auth import admin_required, login_required

issues_bp = Blueprint("issues", __name__, url_prefix="/issues")

# Library rules (change them here)
FINE_PER_DAY = 5      # fine in Rs. for each day after the due date
LOAN_DAYS = 14        # default loan period in days
MAX_BOOKS = 3         # most books one member can hold at a time


def plural(count, word):
    """1 day, 2 days"""
    return "%d %s%s" % (count, word, "" if count == 1 else "s")


def to_date(value):
    """Turn a value read from the database into a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def overdue_info(due_date, return_date=None):
    """Return (late_days, fine). If the book is not returned yet, count up to today."""
    due = to_date(due_date)
    end = to_date(return_date) if return_date else date.today()
    days = max((end - due).days, 0)
    return days, days * FINE_PER_DAY


# ---------- List / History ----------
STATUSES = ("all", "issued", "overdue", "returned")


@issues_bp.route("/")
@login_required
def list_issues():
    status = request.args.get("status", "all")
    if status not in STATUSES:
        status = "all"
    today = date.today().isoformat()
    only_mine = g.user["role"] != "admin"          # a member sees only their own records

    # One query gives the numbers for all four filter tabs
    counts_sql = """SELECT COUNT(*) AS total_all,
                           COALESCE(SUM(return_date IS NULL), 0) AS total_issued,
                           COALESCE(SUM(return_date IS NULL AND due_date < %s), 0) AS total_overdue,
                           COALESCE(SUM(return_date IS NOT NULL), 0) AS total_returned
                    FROM issues"""
    counts_params = [today]
    if only_mine:
        counts_sql += " WHERE user_id = %s"
        counts_params.append(g.user["user_id"])
    row = fetch_one(counts_sql, tuple(counts_params))
    counts = {"all": int(row["total_all"]), "issued": int(row["total_issued"]),
              "overdue": int(row["total_overdue"]), "returned": int(row["total_returned"])}

    # The filter runs in SQL, so only one page of rows is loaded
    conditions, params = [], []
    if only_mine:
        conditions.append("issues.user_id = %s")
        params.append(g.user["user_id"])
    if status == "issued":
        conditions.append("issues.return_date IS NULL")
    elif status == "overdue":
        conditions.append("issues.return_date IS NULL AND issues.due_date < %s")
        params.append(today)
    elif status == "returned":
        conditions.append("issues.return_date IS NOT NULL")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    pg = paginate(counts[status])
    rows = fetch_all(
        """SELECT issues.*, books.title, users.name AS member_name
           FROM issues
           JOIN books ON books.book_id = issues.book_id
           JOIN users ON users.user_id = issues.user_id """ + where +
        " ORDER BY issues.issue_id DESC LIMIT %s OFFSET %s",
        tuple(params) + (pg.per_page, pg.offset),
    )
    for r in rows:
        r["late_days"], r["fine_now"] = overdue_info(r["due_date"], r["return_date"])
        r["is_overdue"] = r["return_date"] is None and r["late_days"] > 0

    return render_template("issues/list.html", issues=rows, status=status, counts=counts,
                           pg=pg, fine_per_day=FINE_PER_DAY)


# ---------- Issue a book ----------
@issues_bp.route("/issue", methods=["GET", "POST"])
@admin_required
def issue_book():
    form = None
    if request.method == "POST":
        form = request.form
        error = None
        try:
            user_id = int(form.get("user_id", ""))
            book_id = int(form.get("book_id", ""))
            days = int(form.get("days", LOAN_DAYS))
        except ValueError:
            user_id = book_id = days = None
            error = "Choose a member, a book, and the number of days."

        if error is None and not (1 <= days <= 60):
            error = "Loan period must be between 1 and 60 days."

        if error is None:
            member = fetch_one("SELECT * FROM users WHERE user_id=%s AND role='member'", (user_id,))
            book = fetch_one("SELECT * FROM books WHERE book_id=%s", (book_id,))
            holding = fetch_one(
                "SELECT COUNT(*) AS total FROM issues WHERE user_id=%s AND return_date IS NULL", (user_id,))
            same_book = fetch_one(
                "SELECT COUNT(*) AS total FROM issues WHERE user_id=%s AND book_id=%s AND return_date IS NULL",
                (user_id, book_id))
            if member is None or book is None:
                error = "Member or book not found."
            elif holding["total"] >= MAX_BOOKS:
                error = "This member already has %d books (limit %d)." % (holding["total"], MAX_BOOKS)
            elif same_book["total"] > 0:
                error = "This member already has this book."

        if error is None:
            today = date.today()
            db = get_db()
            cur = db.cursor()
            try:
                # Reduce the copy count only if a copy is available (protects against two people issuing the last copy)
                cur.execute(
                    "UPDATE books SET available_copies = available_copies - 1 "
                    "WHERE book_id = %s AND available_copies > 0", (book_id,))
                if cur.rowcount == 0:
                    db.rollback()
                    error = "No copy of this book is available."
                else:
                    cur.execute(
                        "INSERT INTO issues (user_id, book_id, issue_date, due_date) VALUES (%s, %s, %s, %s)",
                        (user_id, book_id, today.isoformat(), (today + timedelta(days=days)).isoformat()))
                    db.commit()
            except mysql.connector.Error:
                db.rollback()
                raise
            finally:
                cur.close()

        if error is None:
            flash("Book issued. Due on %s." % (date.today() + timedelta(days=days)).isoformat(), "success")
            return redirect(url_for("issues.list_issues"))
        flash(error, "danger")

    members = fetch_all("SELECT user_id, name, email FROM users WHERE role='member' ORDER BY name")
    books = fetch_all("SELECT book_id, title, author, available_copies FROM books "
                      "WHERE available_copies > 0 ORDER BY title")
    return render_template("issues/issue_form.html", members=members, books=books, form=form,
                           loan_days=LOAN_DAYS, max_books=MAX_BOOKS, fine_per_day=FINE_PER_DAY)


# ---------- Return a book ----------
@issues_bp.route("/<int:issue_id>/return", methods=["POST"])
@admin_required
def return_book(issue_id):
    issue = fetch_one("SELECT * FROM issues WHERE issue_id = %s", (issue_id,))
    if issue is None:
        abort(404)
    if issue["return_date"] is not None:
        flash("This book has already been returned.", "warning")
        return redirect(url_for("issues.list_issues"))

    late_days, fine = overdue_info(issue["due_date"])
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("UPDATE issues SET return_date = %s, fine = %s "
                    "WHERE issue_id = %s AND return_date IS NULL",
                    (date.today().isoformat(), fine, issue_id))
        if cur.rowcount == 1:
            cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id = %s",
                        (issue["book_id"],))
        db.commit()
    except mysql.connector.Error:
        db.rollback()
        raise
    finally:
        cur.close()

    if fine > 0:
        flash("Book returned. %s late, fine Rs. %d." % (plural(late_days, "day"), fine), "warning")
    else:
        flash("Book returned. No fine.", "success")
    return redirect(url_for("issues.list_issues"))
