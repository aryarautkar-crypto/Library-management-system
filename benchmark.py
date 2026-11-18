"""Measures how long the main pages take to load when the library holds a lot of data.

Run:      python benchmark.py
Sizes:    python benchmark.py --books 10000 --members 2000 --issues 20000 --runs 5
It builds its own database (library_bench), so your real data is not touched.
The results are printed and also saved in benchmark_results.txt.
"""
import argparse
import random
import statistics
import time
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

import add_indexes
import config
import dbsetup

BENCH_DB = "library_bench"
config.DB_NAME = BENCH_DB           # every database call below uses the benchmark database

import pagination                   # noqa: E402  (imported after the database name is set)
from app import app                 # noqa: E402

ADMIN_EMAIL, PASSWORD = "bench-admin@test.com", "bench-pass"

PAGES = [
    ("Book list", "/books/"),
    ("Book search", "/books/?q=Book 0042"),
    ("Member list", "/members/"),
    ("Loan list", "/issues/"),
    ("Overdue loans", "/issues/?status=overdue"),
    ("Dashboard", "/dashboard"),
    ("Reports", "/reports/"),
]
INDEX_PAGES = [p for p in PAGES if p[0] in ("Book list", "Member list", "Overdue loans", "Dashboard", "Reports")]


def insert_many(cursor, sql, rows, size=1000):
    for i in range(0, len(rows), size):
        cursor.executemany(sql, rows[i:i + size])


def fill(n_books, n_members, n_issues):
    """Fill the benchmark database with random but realistic data."""
    random.seed(42)                                  # same data every time
    conn = dbsetup.connect(BENCH_DB)
    cur = conn.cursor()
    password_hash = generate_password_hash(PASSWORD)
    cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
                ("Bench Admin", ADMIN_EMAIL, password_hash))
    insert_many(cur, "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'member')",
                [("Member %05d" % i, "member%05d@test.com" % i, password_hash) for i in range(n_members)])
    categories = ["Programming", "Database", "History", "Biography", "Science", "Fiction", "Maths", "Networks", "Design", "Law"]
    insert_many(cur, "INSERT INTO books (title, author, isbn, category, total_copies, available_copies) VALUES (%s, %s, %s, %s, 3, 3)",
                [("Book %05d" % i, "Author %03d" % (i % 500), str(9780000000000 + i), categories[i % len(categories)])
                 for i in range(n_books)])
    conn.commit()

    cur.execute("SELECT user_id FROM users WHERE role = 'member'")
    member_ids = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT book_id FROM books")
    book_ids = [row[0] for row in cur.fetchall()]

    today = date.today()
    rows = []
    for _ in range(n_issues):
        if random.random() < 0.7:                    # a returned loan
            issued = today - timedelta(days=random.randint(10, 150))
            due = issued + timedelta(days=14)
            returned = min(today, due + timedelta(days=random.randint(-5, 6)))
            fine = max((returned - due).days, 0) * 5
        else:                                        # a loan that is still open (some are overdue)
            issued = today - timedelta(days=random.randint(0, 30))
            due = issued + timedelta(days=14)
            returned, fine = None, 0
        rows.append((random.choice(member_ids), random.choice(book_ids), issued.isoformat(), due.isoformat(),
                     returned.isoformat() if returned else None, fine))
    insert_many(cur, "INSERT INTO issues (user_id, book_id, issue_date, due_date, return_date, fine) VALUES (%s, %s, %s, %s, %s, %s)", rows)
    conn.commit()
    cur.close()
    conn.close()


def measure(client, pages, runs):
    """Median load time in milliseconds and HTML size in KB for each page."""
    results = {}
    for name, url in pages:
        client.get(url)                              # warm-up request (not counted)
        samples, size = [], 0
        for _ in range(runs):
            start = time.perf_counter()
            response = client.get(url)
            samples.append((time.perf_counter() - start) * 1000)
            assert response.status_code == 200, "%s returned %s" % (url, response.status_code)
            size = len(response.data) / 1024
        results[name] = (statistics.median(samples), size)
    return results


def table(title, left, right, left_name, right_name, show_size):
    lines = ["", title, "-" * len(title)]
    head = "%-16s %12s %12s %10s" % ("Page", left_name, right_name, "Faster by")
    if show_size:
        head += "   %12s %12s" % ("HTML before", "HTML after")
    lines.append(head)
    for name in left:
        a, b = left[name][0], right[name][0]
        row = "%-16s %9.1f ms %9.1f ms %9.1fx" % (name, a, b, a / b if b else 0)
        if show_size:
            row += "   %9.0f KB %9.0f KB" % (left[name][1], right[name][1])
        lines.append(row)
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--books", type=int, default=10000)
    parser.add_argument("--members", type=int, default=2000)
    parser.add_argument("--issues", type=int, default=20000)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    print("Building the benchmark database (%d books, %d members, %d loans)..." % (args.books, args.members, args.issues))
    dbsetup.create_database(BENCH_DB)
    fill(args.books, args.members, args.issues)

    client = app.test_client()
    client.post("/login", data={"email": ADMIN_EMAIL, "password": PASSWORD})

    print("Measuring pages: all rows on one page...")
    original = pagination.PER_PAGE
    pagination.PER_PAGE = 10 ** 9                    # behave like the old version: every row on one page
    before = measure(client, PAGES, args.runs)
    pagination.PER_PAGE = original
    print("Measuring pages: %d rows per page..." % original)
    after = measure(client, PAGES, args.runs)

    print("Measuring pages: without the database indexes...")
    conn = dbsetup.connect(BENCH_DB)
    cur = conn.cursor()
    add_indexes.drop_indexes(cur)
    conn.commit()
    without_idx = measure(client, INDEX_PAGES, args.runs)
    add_indexes.create_indexes(cur)
    conn.commit()
    print("Measuring pages: with the database indexes...")
    with_idx = measure(client, INDEX_PAGES, args.runs)
    cur.close()
    conn.close()

    lines = ["Library Management System: performance benchmark",
             "Data: %d books, %d members, %d loans. Each time is the median of %d requests." % (
                 args.books, args.members, args.issues, args.runs)]
    lines += table("1. Pagination: all rows on one page vs %d rows per page" % original,
                   before, after, "All rows", "%d per page" % original, True)
    lines += table("2. Database indexes: without vs with", without_idx, with_idx, "No indexes", "Indexes", False)
    report = "\n".join(lines)
    print(report)
    with open("benchmark_results.txt", "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("\nSaved in benchmark_results.txt")


if __name__ == "__main__":
    main()
