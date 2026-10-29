"""MySQL connection aur chhote helper functions.
Har module in functions se database use karta hai."""
import mysql.connector
from flask import g
import config


def get_db():
    """Ek request ke liye ek MySQL connection deta hai."""
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
        )
    return g.db


def close_db(e=None):
    """Request khatam hone par connection band karta hai."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def fetch_one(sql, params=()):
    """Ek row deta hai (dictionary ki tarah), nahi mili to None."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row


def fetch_all(sql, params=()):
    """Saari rows ki list deta hai."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def execute(sql, params=()):
    """INSERT / UPDATE / DELETE chalata hai aur save (commit) karta hai.
    INSERT ke case me naye row ki id return karta hai."""
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
