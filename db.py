"""MySQL connection and small helper functions.
Every module uses these functions to talk to the database."""
import mysql.connector
from flask import g
import config


def get_db():
    """Return the MySQL connection for the current request (created on first use)."""
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
    """Close the connection when the request ends."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def fetch_one(sql, params=()):
    """Return one row as a dictionary, or None if there is no row."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row


def fetch_all(sql, params=()):
    """Return all rows as a list of dictionaries."""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def execute(sql, params=()):
    """Run an INSERT, UPDATE or DELETE and commit it.
    For an INSERT it returns the id of the new row."""
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id
