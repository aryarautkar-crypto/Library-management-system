"""Module 3: Member Management (admin only): list, search, add, edit, delete."""
import mysql.connector
from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, url_for)
from werkzeug.security import generate_password_hash
from db import execute, fetch_all, fetch_one
from pagination import paginate
from routes.auth import admin_required
from validators import valid_email

members_bp = Blueprint("members", __name__, url_prefix="/members")


def read_member_form(password_required):
    """Read the form and validate it. Returns (data, error)."""
    data = {
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
        "password": request.form.get("password", ""),
    }
    error = None
    if not data["name"] or not data["email"]:
        error = "Name and email are required."
    elif len(data["name"]) > 100:
        error = "Name must be 100 characters or fewer."
    elif not valid_email(data["email"]):
        error = "Please enter a valid email address."
    elif password_required and not data["password"]:
        error = "Password is required."
    elif data["password"] and len(data["password"]) < 6:
        error = "Password must be at least 6 characters."
    elif len(data["password"]) > 128:
        error = "Password must be 128 characters or fewer."
    return data, error


@members_bp.route("/")
@admin_required
def list_members():
    q = request.args.get("q", "").strip()[:100]
    like = "%" + q + "%"
    total = fetch_one(
        "SELECT COUNT(*) AS total FROM users u WHERE u.role = 'member' AND (u.name LIKE %s OR u.email LIKE %s)",
        (like, like),
    )["total"]
    pg = paginate(total)
    members = fetch_all(
        """SELECT u.user_id, u.name, u.email, u.created_at,
                  (SELECT COUNT(*) FROM issues i
                   WHERE i.user_id = u.user_id AND i.return_date IS NULL) AS issued_count
           FROM users u
           WHERE u.role = 'member' AND (u.name LIKE %s OR u.email LIKE %s)
           ORDER BY u.name LIMIT %s OFFSET %s""",
        (like, like, pg.per_page, pg.offset),
    )
    return render_template("members/list.html", members=members, q=q, pg=pg)


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
                error = "That email is already registered."
            else:
                flash("Member added.", "success")
                return redirect(url_for("members.list_members"))
        flash(error, "danger")
    return render_template("members/form.html", member=member, heading="Add a member", editing=False)


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
                error = "Another member already uses this email."
            else:
                flash("Member updated.", "success")
                return redirect(url_for("members.list_members"))
        flash(error, "danger")
        member = data

    return render_template("members/form.html", member=member, heading="Edit member", editing=True)


@members_bp.route("/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_member(user_id):
    member = fetch_one("SELECT * FROM users WHERE user_id = %s AND role = 'member'", (user_id,))
    if member is None:
        abort(404)

    used = fetch_one("SELECT COUNT(*) AS total FROM issues WHERE user_id = %s", (user_id,))["total"]
    if used > 0:
        flash("This member cannot be deleted because they have loan records.", "danger")
    else:
        execute("DELETE FROM users WHERE user_id = %s AND role = 'member'", (user_id,))
        flash("Member deleted.", "info")
    return redirect(url_for("members.list_members"))
