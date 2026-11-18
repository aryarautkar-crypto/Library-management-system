"""Shared test setup.

The tests run against their own database (library_test), so your real library_db is never touched.
MySQL must be running before you start the tests.
"""
import unittest
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

import config
import dbsetup

TEST_DB = "library_test"
config.DB_NAME = TEST_DB            # from now on every database call in this process uses the test database

ADMIN_EMAIL, ADMIN_PASSWORD = "admin@test.com", "admin-pass-1"
MEMBER_EMAIL, MEMBER_PASSWORD = "member@test.com", "member-pass-1"

# Password hashing is slow on purpose, so it is done only once
ADMIN_HASH = generate_password_hash(ADMIN_PASSWORD)
MEMBER_HASH = generate_password_hash(MEMBER_PASSWORD)

BOOKS = [
    ("Let Us C", "Yashavant Kanetkar", "9788183331630", "Programming", 2, 2),
    ("Python Crash Course", "Eric Matthes", "9781593279288", "Programming", 1, 1),
    ("Wings of Fire", "A. P. J. Abdul Kalam", "9788173711466", "Biography", 3, 3),
]

_state = {"app": None}


def get_app():
    """Build the test database once, then return the Flask app."""
    if _state["app"] is None:
        dbsetup.create_database(TEST_DB)
        from app import app
        app.config.update(TESTING=True)
        _state["app"] = app
    return _state["app"]


def query(sql, params=()):
    conn = dbsetup.connect(TEST_DB)
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def run(sql, params=()):
    conn = dbsetup.connect(TEST_DB)
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    cur.close()
    conn.close()


def run_many(sql, rows):
    conn = dbsetup.connect(TEST_DB)
    cur = conn.cursor()
    cur.executemany(sql, rows)
    conn.commit()
    cur.close()
    conn.close()


def reset_data():
    """Empty the tables, then add the librarian, one member and three books."""
    conn = dbsetup.connect(TEST_DB)
    cur = conn.cursor()
    for table in ("issues", "books", "users"):
        cur.execute("DELETE FROM " + table)
    cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
                ("Test Librarian", ADMIN_EMAIL, ADMIN_HASH))
    cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'member')",
                ("Test Member", MEMBER_EMAIL, MEMBER_HASH))
    cur.executemany(
        "INSERT INTO books (title, author, isbn, category, total_copies, available_copies) "
        "VALUES (%s, %s, %s, %s, %s, %s)", BOOKS)
    conn.commit()
    cur.close()
    conn.close()


def text(response):
    return response.get_data(as_text=True)


class LibraryTestCase(unittest.TestCase):
    """Base class for every test that needs the database."""

    @classmethod
    def setUpClass(cls):
        cls.app = get_app()

    def setUp(self):
        reset_data()
        self.client = self.app.test_client()          # not signed in
        self._clients = {}

    def sign_in(self, email, password):
        client = self.app.test_client()
        client.post("/login", data={"email": email, "password": password})
        return client

    @property
    def admin(self):
        if "admin" not in self._clients:
            self._clients["admin"] = self.sign_in(ADMIN_EMAIL, ADMIN_PASSWORD)
        return self._clients["admin"]

    @property
    def member(self):
        if "member" not in self._clients:
            self._clients["member"] = self.sign_in(MEMBER_EMAIL, MEMBER_PASSWORD)
        return self._clients["member"]

    # ----- small helpers -----
    def user_id(self, email):
        return query("SELECT user_id FROM users WHERE email = %s", (email,))[0]["user_id"]

    def book_id(self, title):
        return query("SELECT book_id FROM books WHERE title = %s", (title,))[0]["book_id"]

    def count(self, table):
        return query("SELECT COUNT(*) AS n FROM " + table)[0]["n"]

    def add_member_row(self, name, email):
        run("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'member')",
            (name, email, MEMBER_HASH))

    def make_loan(self, email, title, due_in_days=14, returned=False, fine=0):
        """Create a loan directly in the database (a quick way to set up a test situation)."""
        due = date.today() + timedelta(days=due_in_days)
        issued = due - timedelta(days=14)
        run("INSERT INTO issues (user_id, book_id, issue_date, due_date, return_date, fine) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (self.user_id(email), self.book_id(title), issued.isoformat(), due.isoformat(),
             date.today().isoformat() if returned else None, fine))
        if not returned:
            run("UPDATE books SET available_copies = available_copies - 1 WHERE book_id = %s",
                (self.book_id(title),))
        return query("SELECT MAX(issue_id) AS id FROM issues")[0]["id"]

    def issue(self, email, title, days="14"):
        """Issue a book through the real form, as the librarian would."""
        return self.admin.post("/issues/issue", data={
            "user_id": str(self.user_id(email)), "book_id": str(self.book_id(title)), "days": days},
            follow_redirects=True)
