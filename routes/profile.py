"""Profile: any signed-in user can change their name and email, and change their password."""
import mysql.connector
from flask import (Blueprint, flash, g, redirect, render_template,
                   request, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from db import execute
from validators import valid_email
from routes.auth import login_required

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "details":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            if not name or not email:
                flash("Name and email are required.", "danger")
            elif len(name) > 100:
                flash("Name must be 100 characters or fewer.", "danger")
            elif not valid_email(email):
                flash("Please enter a valid email address.", "danger")
            else:
                try:
                    execute("UPDATE users SET name=%s, email=%s WHERE user_id=%s",
                            (name, email, g.user["user_id"]))
                except mysql.connector.IntegrityError:
                    flash("Another account already uses this email.", "danger")
                else:
                    flash("Profile updated.", "success")
                    return redirect(url_for("profile.profile"))

        elif action == "password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not check_password_hash(g.user["password_hash"], current):
                flash("Current password is incorrect.", "danger")
            elif len(new) < 6:
                flash("New password must be at least 6 characters.", "danger")
            elif len(new) > 128:
                flash("New password must be 128 characters or fewer.", "danger")
            elif new != confirm:
                flash("New password and confirmation do not match.", "danger")
            else:
                execute("UPDATE users SET password_hash=%s WHERE user_id=%s",
                        (generate_password_hash(new), g.user["user_id"]))
                flash("Password changed.", "success")
                return redirect(url_for("profile.profile"))

    return render_template("profile.html")
