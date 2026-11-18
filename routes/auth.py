"""Module 1: Authentication (register, login, logout)."""
import functools
import mysql.connector
from flask import (Blueprint, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from db import execute, fetch_one
from validators import valid_email

auth_bp = Blueprint("auth", __name__)


# ---------- Decorators that protect pages ----------
def login_required(view):
    """The page opens only for a signed-in user."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """The page opens only for the librarian (admin)."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            flash("That page is for the librarian only.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.before_app_request
def load_logged_in_user():
    """Before every request, find out who is signed in."""
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = fetch_one("SELECT * FROM users WHERE user_id = %s", (user_id,))


# ---------- Routes ----------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        # Validation
        error = None
        if not name or not email or not password:
            error = "Please fill in all fields."
        elif len(name) > 100:
            error = "Name must be 100 characters or fewer."
        elif not valid_email(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif len(password) > 128:
            error = "Password must be 128 characters or fewer."

        if error is None:
            try:
                execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                    (name, email, generate_password_hash(password)),
                )
            except mysql.connector.IntegrityError:
                error = "That email is already registered."
            else:
                flash("Account created. You can sign in now.", "success")
                return redirect(url_for("auth.login"))

        flash(error, "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = fetch_one("SELECT * FROM users WHERE email = %s", (email,))

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "danger")
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
