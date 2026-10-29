"""Module 4: Issue / Return + Fine.
Admin: book issue/return karta hai. Member: sirf apni issue history dekhta hai."""
from datetime import date, datetime, timedelta
import mysql.connector
from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)
from db import fetch_all, fetch_one, get_db
from routes.auth import admin_required, login_required

issues_bp = Blueprint("issues", __name__, url_prefix="/issues")

# Library ke rules (yaha se badal sakte ho)
FINE_PER_DAY = 5      # due date ke baad har din ka fine (Rs.)
LOAN_DAYS = 14        # default kitne din ke liye book milti hai
MAX_BOOKS = 3         # ek member ek saath kitni books le sakta hai


def to_date(value):
    """DB se aayi value ko date me badalta hai."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def overdue_info(due_date, return_date=None):
    """(late_days, fine) return karta hai. Return nahi hui to aaj tak ka hisaab."""
    due = to_date(due_date)
    end = to_date(return_date) if return_date else date.today()
    days = max((end - due).days, 0)
    return days, days * FINE_PER_DAY


# ---------- List / History ----------
@issues_bp.route("/")
@login_required
def list_issues():
    status = request.args.get("status", "all")
    sql = """SELECT issues.*, books.title, users.name AS member_name
             FROM issues
             JOIN books ON books.book_id = issues.book_id
             JOIN users ON users.user_id = issues.user_id"""
    params = ()
    if g.user["role"] != "admin":          # member sirf apne records dekhe
        sql += " WHERE issues.user_id = %s"
        params = (g.user["user_id"],)
    sql += " ORDER BY issues.issue_id DESC"

    rows = []
    for row in fetch_all(sql, params):
        row["late_days"], row["fine_now"] = overdue_info(row["due_date"], row["return_date"])
        row["is_overdue"] = row["return_date"] is None and row["late_days"] > 0
        if status == "issued" and row["return_date"] is not None:
            continue
        if status == "returned" and row["return_date"] is None:
            continue
        if status == "overdue" and not row["is_overdue"]:
            continue
        rows.append(row)

    return render_template("issues/list.html", issues=rows, status=status, fine_per_day=FINE_PER_DAY)


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
            error = "Member, book aur din sahi se chuno."

        if error is None and not (1 <= days <= 60):
            error = "Din 1 se 60 ke beech me hone chahiye."

        if error is None:
            member = fetch_one("SELECT * FROM users WHERE user_id=%s AND role='member'", (user_id,))
            book = fetch_one("SELECT * FROM books WHERE book_id=%s", (book_id,))
            holding = fetch_one(
                "SELECT COUNT(*) AS total FROM issues WHERE user_id=%s AND return_date IS NULL", (user_id,))
            same_book = fetch_one(
                "SELECT COUNT(*) AS total FROM issues WHERE user_id=%s AND book_id=%s AND return_date IS NULL",
                (user_id, book_id))
            if member is None or book is None:
                error = "Member ya book nahi mili."
            elif holding["total"] >= MAX_BOOKS:
                error = "Is member ke paas pehle se %d books hain (limit %d)." % (holding["total"], MAX_BOOKS)
            elif same_book["total"] > 0:
                error = "Ye book is member ke paas pehle se issue hai."

        if error is None:
            today = date.today()
            db = get_db()
            cur = db.cursor()
            try:
                # Copy tabhi ghatao jab available ho (do logo ke ek saath issue karne se bachne ke liye)
                cur.execute(
                    "UPDATE books SET available_copies = available_copies - 1 "
                    "WHERE book_id = %s AND available_copies > 0", (book_id,))
                if cur.rowcount == 0:
                    db.rollback()
                    error = "Is book ki koi copy available nahi hai."
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
            flash("Book issue ho gayi. Due date: %s" % (date.today() + timedelta(days=days)).isoformat(), "success")
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
        flash("Ye book pehle hi return ho chuki hai.", "warning")
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
        flash("Book return ho gayi. %d din late, fine Rs. %d." % (late_days, fine), "warning")
    else:
        flash("Book return ho gayi. Koi fine nahi.", "success")
    return redirect(url_for("issues.list_issues"))
