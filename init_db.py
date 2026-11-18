"""Run once:  python init_db.py
Creates the library_db database in MySQL with its tables, sample books and the default admin."""
import os
import mysql.connector
from werkzeug.security import generate_password_hash
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_sql_file(cursor, filename):
    """Read an SQL file and run its statements one by one."""
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
        print("Could not connect to MySQL:", err)
        print("Check that 1) the MySQL server is running and 2) the user and password in config.py are correct.")
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
