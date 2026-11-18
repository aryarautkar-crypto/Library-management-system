"""Adds the performance indexes to an existing database without losing any data.
Run once:  python add_indexes.py
(A new database gets the same indexes from schema.sql.)"""
import mysql.connector
import dbsetup
import config

# (table, index name, columns)
INDEXES = [
    ("books", "idx_books_title", "title"),                    # sorted book list (ORDER BY title)
    ("books", "idx_books_available", "available_copies"),     # out-of-stock report
    ("users", "idx_users_role_name", "role, name"),           # member list
    ("issues", "idx_issues_open", "return_date, due_date"),   # open and overdue loans
    ("issues", "idx_issues_user_open", "user_id, return_date"),  # loans of one member
]


def create_indexes(cursor):
    """Create every index that is missing. Returns a list of messages."""
    messages = []
    for table, name, columns in INDEXES:
        try:
            cursor.execute("CREATE INDEX %s ON %s (%s)" % (name, table, columns))
            messages.append("created  %s" % name)
        except mysql.connector.Error as err:
            if getattr(err, "errno", None) == 1061:           # duplicate key name: already there
                messages.append("exists   %s" % name)
            else:
                raise
    return messages


def drop_indexes(cursor):
    """Remove the indexes again (the benchmark uses this to measure the difference)."""
    for table, name, _ in INDEXES:
        try:
            cursor.execute("DROP INDEX %s ON %s" % (name, table))
        except mysql.connector.Error:
            pass


if __name__ == "__main__":
    conn = dbsetup.connect(config.DB_NAME)
    cur = conn.cursor()
    for line in create_indexes(cur):
        print(line)
    conn.commit()
    cur.close()
    conn.close()
    print("Done.")
