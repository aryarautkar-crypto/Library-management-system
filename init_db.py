"""Ek baar chalao:  python init_db.py
Ye MySQL me library_db database, tables, dummy books aur default admin banata hai."""
import os
import mysql.connector
from werkzeug.security import generate_password_hash
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_sql_file(cursor, filename):
    """SQL file ko padh kar ek-ek statement chalata hai."""
    with open(os.path.join(BASE_DIR, filename), encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if not l.strip().startswith("--")]
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            cursor.execute(statement)


def main():
    try:
        conn = mysql.connector.connect(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASSWORD,
        )
    except mysql.connector.Error as err:
        print("MySQL se connect nahi ho paya:", err)
        print("Check karo: 1) MySQL server start hai?  2) config.py me user/password sahi hai?")
        return

    cur = conn.cursor()
    run_sql_file(cur, "schema.sql")
    run_sql_file(cur, "seed.sql")

    # Default admin (librarian)
    cur.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
        ("Librarian", "admin@library.com", generate_password_hash("admin123")),
    )
    conn.commit()
    cur.close()
    conn.close()
    print("Database ready!  Admin login -> admin@library.com / admin123")


if __name__ == "__main__":
    main()
