"""Settings. Every value can also be set with an environment variable,
so the same code runs on your laptop and in the cloud."""
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
_port = os.environ.get("DB_PORT", "3306")
DB_PORT = int(_port) if _port.isdigit() else _port      # a wrong value is reported by startup_checks
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")         # XAMPP's root user has an empty password
DB_NAME = os.environ.get("DB_NAME", "library_db")       # schema.sql uses the same name
DB_SSL = os.environ.get("DB_SSL", "0") == "1"           # cloud databases need an encrypted connection

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key")
DEFAULT_SECRET_KEY = "change-this-secret-key"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")   # password of the admin that init_db.py creates
IS_CLOUD = bool(os.environ.get("RENDER"))                       # Render sets this variable on its servers
