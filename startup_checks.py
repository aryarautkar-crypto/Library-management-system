"""Startup checks: a wrong setting is reported in plain English instead of a long error trace."""
import re
import mysql.connector
import config
from db import connection_settings


class ConfigError(Exception):
    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = problems


def check_config():
    """Raise ConfigError listing every invalid value in config.py."""
    problems = []
    if not str(config.DB_HOST or "").strip():
        problems.append("DB_HOST is empty.")
    if not isinstance(config.DB_PORT, int) or not 1 <= config.DB_PORT <= 65535:
        problems.append("DB_PORT must be a number between 1 and 65535.")
    if not str(config.DB_USER or "").strip():
        problems.append("DB_USER is empty.")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", str(config.DB_NAME or "")):
        problems.append("DB_NAME may contain only letters, digits and underscores (at most 64 characters).")
    if len(str(config.SECRET_KEY or "")) < 8:
        problems.append("SECRET_KEY is missing or too short (use at least 8 characters).")
    if config.IS_CLOUD and config.SECRET_KEY == config.DEFAULT_SECRET_KEY:
        problems.append("SECRET_KEY must be changed from the default value when the app runs in the cloud.")
    if problems:
        raise ConfigError(problems)


def check_database():
    """Try to connect to MySQL. Returns (ok, message)."""
    try:
        conn = mysql.connector.connect(**connection_settings(), connection_timeout=5)
        conn.close()
        return True, "Database connection OK."
    except mysql.connector.Error as err:
        code = getattr(err, "errno", None)
        if code in (2002, 2003):
            return False, "Cannot reach MySQL at %s:%s. Start MySQL (XAMPP Control Panel) and try again." % (config.DB_HOST, config.DB_PORT)
        if code == 1045:
            return False, "MySQL refused the user name or password. Check DB_USER and DB_PASSWORD in config.py."
        if code == 1049:
            return False, "The database '%s' does not exist yet. Run:  python init_db.py" % config.DB_NAME
        return False, "Database error: %s" % err
