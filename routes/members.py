"""Module 3: Member Management (sirf admin ke liye): list, search, add, edit, delete."""
import mysql.connector
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from werkzeug.security import generate_password_hash
from db import execute, fetch_all, fetch_one
from routes.auth import admin_required

members_bp = Blueprint("members", __name__, url_prefix="/members")


def read_member_form(password_required):
    """Form ka data leta hai aur check karta hai. (data, error) return karta hai."""
    data = {
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "password": request.form.get("password", ""),
    }
    error = None
    if not data["name"] or not data["email"]:
        error = "Name aur Email bharna zaroori hai."
    elif password_required and not data["password"]:
        error = "Password bharna zaroori hai."
    elif data["password"] and len(data["password"]) < 6:
        error = "Password kam se kam 6 characters ka hona chahiye."
    return data, error


@members_bp.route("/")
@admin_required
def list_members():
    q = request.args.get("q", "").strip()
    like = "%" + q + "%"
    members = fetch_all(
        """SELECT u.user_id, u.name, u.email, u.created_at,
                  (SELECT COUNT(*) FROM issues i
                   WHERE i.user_id = u.user_id AND i.return_date IS NULL) AS issued_count
           FROM users u
           WHERE u.role = 'member' AND (u.name LIKE %s OR u.email LIKE %s)
           ORDER BY u.name""",
        (like, like),
    )
    return render_template("members/list.html", members=members, q=q)


@members_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_member():
    member = None
    if request.method == "POST":
        member, error = read_member_form(password_required=True)
        if error is None:
            try:
                execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'member')",
                    (member["name"], member["email"], generate_password_hash(member["password"])),
                )
            except mysql.connector.IntegrityError:
                error = "Ye email pehle se registered hai."
            else:
                flash("Member add ho gaya.", "success")
                return redirect(url_for("members.list_members"))
        flash(error, "danger")
    return render_template("members/form.html", member=member, heading="Add New Member", editing=False)


@members_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_member(user_id):
    member = fetch_one("SELECT * FROM users WHERE user_id = %s AND role = 'member'", (user_id,))
    if member is None:
        abort(404)

    if request.method == "POST":
        data, error = read_member_form(password_required=False)
        if error is None:
            try:
                if data["password"]:
                    execute("UPDATE users SET name=%s, email=%s, password_hash=%s WHERE user_id=%s",
                            (data["name"], data["email"], generate_password_hash(data["password"]), user_id))
                else:
                    execute("UPDATE users SET name=%s, email=%s WHERE user_id=%s",
                            (data["name"], data["email"], user_id))
            except mysql.connector.IntegrityError:
                error = "Ye email kisi aur member ka hai."
            else:
                flash("Member update ho gaya.", "success")
                return redirect(url_for("members.list_members"))
        flash(error, "danger")
        member = data

    return render_template("members/form.html", member=member, heading="Edit Member", editing=True)


@members_bp.route("/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_member(user_id):
    member = fetch_one("SELECT * FROM users WHERE user_id = %s AND role = 'member'", (user_id,))
    if member is None:
        abort(404)

    used = fetch_one("SELECT COUNT(*) AS total FROM issues WHERE user_id = %s", (user_id,))["total"]
    if used > 0:
        flash("Is member ke issue records maujood hain, isliye delete nahi ho sakta.", "danger")
    else:
        execute("DELETE FROM users WHERE user_id = %s AND role = 'member'", (user_id,))
        flash("Member delete ho gaya.", "info")
    return redirect(url_for("members.list_members"))
