"""Profile: har logged-in user apna naam/email badal sakta hai aur password change kar sakta hai."""
import mysql.connector
from flask import (Blueprint, flash, g, redirect, render_template,
                   request, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from db import execute
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
                flash("Name aur Email bharna zaroori hai.", "danger")
            else:
                try:
                    execute("UPDATE users SET name=%s, email=%s WHERE user_id=%s",
                            (name, email, g.user["user_id"]))
                except mysql.connector.IntegrityError:
                    flash("Ye email kisi aur account ka hai.", "danger")
                else:
                    flash("Profile update ho gayi.", "success")
                    return redirect(url_for("profile.profile"))

        elif action == "password":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not check_password_hash(g.user["password_hash"], current):
                flash("Current password galat hai.", "danger")
            elif len(new) < 6:
                flash("Naya password kam se kam 6 characters ka hona chahiye.", "danger")
            elif new != confirm:
                flash("Naya password aur confirm password same nahi hain.", "danger")
            else:
                execute("UPDATE users SET password_hash=%s WHERE user_id=%s",
                        (generate_password_hash(new), g.user["user_id"]))
                flash("Password change ho gaya.", "success")
                return redirect(url_for("profile.profile"))

    return render_template("profile.html")
