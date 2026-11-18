"""Module 2: Book Management (list + search, add, edit, delete).
Viewing and searching books: any signed-in user. Add, edit and delete: admin only."""
import mysql.connector
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from db import execute, fetch_all, fetch_one
from pagination import paginate
from routes.auth import admin_required, login_required
from validators import valid_isbn

books_bp = Blueprint("books", __name__, url_prefix="/books")

MAX_COPIES = 1000


def read_book_form():
    """Read the form and validate it. Returns (data, error)."""
    data = {
        "title": request.form.get("title", "").strip(),
        "author": request.form.get("author", "").strip(),
        "isbn": request.form.get("isbn", "").strip(),
        "category": request.form.get("category", "").strip(),
        "total_copies": request.form.get("total_copies", "").strip(),
    }
    error = None
    if not data["title"] or not data["author"]:
        error = "Title and author are required."
    elif len(data["title"]) > 200:
        error = "Title must be 200 characters or fewer."
    elif len(data["author"]) > 120:
        error = "Author must be 120 characters or fewer."
    elif len(data["category"]) > 60:
        error = "Category must be 60 characters or fewer."
    elif not valid_isbn(data["isbn"]):
        error = "ISBN must have 10 to 20 characters (digits, hyphens or X)."
    else:
        try:
            data["total_copies"] = int(data["total_copies"])
            if data["total_copies"] < 1:
                error = "There must be at least 1 copy."
            elif data["total_copies"] > MAX_COPIES:
                error = "Total copies cannot be more than %d." % MAX_COPIES
        except ValueError:
            error = "Total copies must be a number."
    return data, error


# ---------- List + Search ----------
@books_bp.route("/")
@login_required
def list_books():
    q = request.args.get("q", "").strip()[:100]
    where, params = "", ()
    if q:
        like = "%" + q + "%"
        where = "WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s OR category LIKE %s"
        params = (like, like, like, like)

    total = fetch_one("SELECT COUNT(*) AS total FROM books " + where, params)["total"]
    pg = paginate(total)
    books = fetch_all(
        "SELECT * FROM books " + where + " ORDER BY title LIMIT %s OFFSET %s",
        params + (pg.per_page, pg.offset),
    )
    return render_template("books/list.html", books=books, q=q, pg=pg)


# ---------- Add ----------
@books_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_book():
    book = None
    if request.method == "POST":
        book, error = read_book_form()
        if error is None:
            try:
                execute(
                    """INSERT INTO books (title, author, isbn, category, total_copies, available_copies)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (book["title"], book["author"], book["isbn"] or None,
                     book["category"] or None, book["total_copies"], book["total_copies"]),
                )
            except mysql.connector.IntegrityError:
                error = "A book with this ISBN already exists."
            else:
                flash("Book added.", "success")
                return redirect(url_for("books.list_books"))
        flash(error, "danger")
    return render_template("books/form.html", book=book, heading="Add a book")


# ---------- Edit ----------
@books_bp.route("/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    book = fetch_one("SELECT * FROM books WHERE book_id = %s", (book_id,))
    if book is None:
        abort(404)

    if request.method == "POST":
        data, error = read_book_form()
        if error is None:
            # Copies currently on loan: total - available
            issued = book["total_copies"] - book["available_copies"]
            if data["total_copies"] < issued:
                error = "%d copies are on loan, so total copies cannot be lower than that." % issued
            else:
                try:
                    execute(
                        """UPDATE books SET title=%s, author=%s, isbn=%s, category=%s,
                                  total_copies=%s, available_copies=%s
                           WHERE book_id=%s""",
                        (data["title"], data["author"], data["isbn"] or None,
                         data["category"] or None, data["total_copies"],
                         data["total_copies"] - issued, book_id),
                    )
                except mysql.connector.IntegrityError:
                    error = "Another book already uses this ISBN."
                else:
                    flash("Book updated.", "success")
                    return redirect(url_for("books.list_books"))
        flash(error, "danger")
        book = data  # on an error, show what the user typed back in the form

    return render_template("books/form.html", book=book, heading="Edit book")


# ---------- Delete ----------
@books_bp.route("/<int:book_id>/delete", methods=["POST"])
@admin_required
def delete_book(book_id):
    book = fetch_one("SELECT * FROM books WHERE book_id = %s", (book_id,))
    if book is None:
        abort(404)

    used = fetch_one("SELECT COUNT(*) AS total FROM issues WHERE book_id = %s", (book_id,))["total"]
    if used > 0:
        flash("This book cannot be deleted because it has loan records.", "danger")
    else:
        execute("DELETE FROM books WHERE book_id = %s", (book_id,))
        flash("Book deleted.", "info")
    return redirect(url_for("books.list_books"))
