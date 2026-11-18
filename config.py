"""Database settings. Change them to match your MySQL installation."""
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")   # XAMPP's root user has an empty password
DB_NAME = "library_db"                            # schema.sql uses the same name

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")
