"""Module 2: Book Management (list + search, add, edit, delete).
Books dekhna/search karna: sab logged-in users. Add/Edit/Delete: sirf admin."""
import mysql.connector
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from db import execute, fetch_all, fetch_one
from routes.auth import admin_required, login_required

books_bp = Blueprint("books", __name__, url_prefix="/books")


def read_book_form():
    """Form se data leta hai aur check karta hai. (data, error) return karta hai."""
    data = {
        "title": request.form.get("title", "").strip(),
        "author": request.form.get("author", "").strip(),
        "isbn": request.form.get("isbn", "").strip(),
        "category": request.form.get("category", "").strip(),
        "total_copies": request.form.get("total_copies", "").strip(),
    }
    error = None
    if not data["title"] or not data["author"]:
        error = "Title aur Author bharna zaroori hai."
    else:
        try:
            data["total_copies"] = int(data["total_copies"])
            if data["total_copies"] < 1:
                error = "Copies kam se kam 1 honi chahiye."
        except ValueError:
            error = "Copies ki jagah number likho."
    return data, error


# ---------- List + Search ----------
@books_bp.route("/")
@login_required
def list_books():
    q = request.args.get("q", "").strip()
    if q:
        like = "%" + q + "%"
        books = fetch_all(
            """SELECT * FROM books
               WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s OR category LIKE %s
               ORDER BY title""",
            (like, like, like, like),
        )
    else:
        books = fetch_all("SELECT * FROM books ORDER BY title")
    return render_template("books/list.html", books=books, q=q)


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
                error = "Is ISBN ki book pehle se maujood hai."
            else:
                flash("Book add ho gayi.", "success")
                return redirect(url_for("books.list_books"))
        flash(error, "danger")
    return render_template("books/form.html", book=book, heading="Add New Book")


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
            # Kitni copies abhi issue hain: total - available
            issued = book["total_copies"] - book["available_copies"]
            if data["total_copies"] < issued:
                error = "Abhi %d copies issue hain, total copies isse kam nahi ho sakti." % issued
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
                    error = "Is ISBN ki dusri book pehle se maujood hai."
                else:
                    flash("Book update ho gayi.", "success")
                    return redirect(url_for("books.list_books"))
        flash(error, "danger")
        book = data  # galti hone par user ka likha hua data form me wapas dikhao

    return render_template("books/form.html", book=book, heading="Edit Book")


# ---------- Delete ----------
@books_bp.route("/<int:book_id>/delete", methods=["POST"])
@admin_required
def delete_book(book_id):
    book = fetch_one("SELECT * FROM books WHERE book_id = %s", (book_id,))
    if book is None:
        abort(404)

    used = fetch_one("SELECT COUNT(*) AS total FROM issues WHERE book_id = %s", (book_id,))["total"]
    if used > 0:
        flash("Ye book delete nahi ho sakti, kyunki iska issue record maujood hai.", "danger")
    else:
        execute("DELETE FROM books WHERE book_id = %s", (book_id,))
        flash("Book delete ho gayi.", "info")
    return redirect(url_for("books.list_books"))
