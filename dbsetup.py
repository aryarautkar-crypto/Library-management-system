"""Create a fresh copy of the database under another name.
Used by the tests (library_test) and by the benchmark (library_bench), so your real data is never touched."""
import os
import re
import mysql.connector
import config
from db import connection_settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def connect(db_name=None):
    settings = connection_settings(include_database=False)
    if db_name:
        settings["database"] = db_name
    return mysql.connector.connect(**settings)


def create_database(db_name):
    """Drop db_name if it exists, then create it again with every table and index from schema.sql."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", db_name):
        raise ValueError("Invalid database name: %r" % db_name)
    if db_name == "library_db":
        raise ValueError("Refusing to rebuild library_db: it holds your real data.")

    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        sql = f.read().replace("library_db", db_name)
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]

    conn = connect()
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS " + db_name)
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            cur.execute(statement)
    conn.commit()
    cur.close()
    conn.close()
