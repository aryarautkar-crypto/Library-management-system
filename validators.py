"""Small input checks shared by the forms."""
import re

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ISBN_PATTERN = re.compile(r"^[0-9Xx-]{10,20}$")


def valid_email(value):
    """A simple format check: something@something.something, at most 120 characters."""
    return len(value) <= 120 and EMAIL_PATTERN.match(value) is not None


def valid_isbn(value):
    """An empty ISBN is allowed (the field is optional)."""
    return value == "" or ISBN_PATTERN.match(value) is not None
