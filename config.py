"""Database settings. Apne MySQL ke hisaab se yaha badlo."""
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")   # XAMPP me root ka password khaali hota hai
DB_NAME = "library_db"                            # schema.sql me bhi yahi naam hai

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")
