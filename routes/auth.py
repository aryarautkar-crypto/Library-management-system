"""Module 1: Authentication (register, login, logout)."""
import functools
import mysql.connector
from flask import (Blueprint, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from db import execute, fetch_one

auth_bp = Blueprint("auth", __name__)


# ---------- Decorators: pages ko protect karne ke liye ----------
def login_required(view):
    """Login ke bina page nahi khulega."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Pehle login karo.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Sirf librarian (admin) ke liye."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            flash("Ye page sirf admin ke liye hai.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.before_app_request
def load_logged_in_user():
    """Har request par check karta hai ki kaun login hai."""
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
            error = "Saari fields bharna zaroori hai."
        elif len(password) < 6:
            error = "Password kam se kam 6 characters ka hona chahiye."

        if error is None:
            try:
                execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                    (name, email, generate_password_hash(password)),
                )
            except mysql.connector.IntegrityError:
                error = "Ye email pehle se registered hai."
            else:
                flash("Registration ho gaya! Ab login karo.", "success")
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
            flash("Email ya password galat hai.", "danger")
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logout ho gaye.", "info")
    return redirect(url_for("auth.login"))
