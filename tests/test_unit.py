"""Unit tests: small pieces of logic, tested on their own (no database needed)."""
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

import mysql.connector

import config
import db
import pagination
import startup_checks
import validators
from app import app as flask_app
from routes.books import read_book_form
from routes.issues import FINE_PER_DAY, overdue_info, plural, to_date
from routes.members import read_member_form


def days_ago(n):
    return date.today() - timedelta(days=n)


class FineTests(unittest.TestCase):
    def test_due_in_the_future_has_no_fine(self):
        self.assertEqual(overdue_info(date.today() + timedelta(days=3)), (0, 0))

    def test_due_today_has_no_fine(self):
        self.assertEqual(overdue_info(date.today()), (0, 0))

    def test_one_day_late(self):
        self.assertEqual(overdue_info(days_ago(1)), (1, FINE_PER_DAY))

    def test_ten_days_late(self):
        self.assertEqual(overdue_info(days_ago(10)), (10, 10 * FINE_PER_DAY))

    def test_returned_on_time_or_early_has_no_fine(self):
        self.assertEqual(overdue_info(days_ago(5), days_ago(5)), (0, 0))
        self.assertEqual(overdue_info(days_ago(5), days_ago(8)), (0, 0))

    def test_returned_late_counts_until_the_return_date(self):
        self.assertEqual(overdue_info(days_ago(10), days_ago(6)), (4, 4 * FINE_PER_DAY))

    def test_accepts_dates_written_as_text(self):
        self.assertEqual(overdue_info(days_ago(2).isoformat()), (2, 2 * FINE_PER_DAY))

    def test_accepts_datetime_values(self):
        self.assertEqual(overdue_info(datetime.now() - timedelta(days=3)), (3, 3 * FINE_PER_DAY))


class HelperTests(unittest.TestCase):
    def test_plural(self):
        self.assertEqual(plural(0, "day"), "0 days")
        self.assertEqual(plural(1, "day"), "1 day")
        self.assertEqual(plural(2, "day"), "2 days")

    def test_to_date(self):
        today = date.today()
        self.assertEqual(to_date(today), today)
        self.assertEqual(to_date(datetime(2026, 11, 10, 15, 30)), date(2026, 11, 10))
        self.assertEqual(to_date("2026-11-10"), date(2026, 11, 10))


class ValidatorTests(unittest.TestCase):
    def test_valid_emails(self):
        for value in ("a@b.com", "first.last@college.edu.in", "x+tag@mail.org"):
            with self.subTest(value=value):
                self.assertTrue(validators.valid_email(value))

    def test_invalid_emails(self):
        for value in ("", "plain", "a@b", "@b.com", "a b@c.com", "a@b.com " + "x" * 120):
            with self.subTest(value=value):
                self.assertFalse(validators.valid_email(value))

    def test_valid_isbn(self):
        for value in ("", "9788183331630", "978-81-8333-163-0", "080442957X"):
            with self.subTest(value=value):
                self.assertTrue(validators.valid_isbn(value))

    def test_invalid_isbn(self):
        for value in ("123", "abcdefghijk", "9788183331630123456789"):
            with self.subTest(value=value):
                self.assertFalse(validators.valid_isbn(value))


class BookFormTests(unittest.TestCase):
    def check(self, **overrides):
        data = {"title": "T", "author": "A", "isbn": "", "category": "", "total_copies": "2"}
        data.update(overrides)
        with flask_app.test_request_context("/books/add", method="POST", data=data):
            return read_book_form()

    def test_valid_form(self):
        data, error = self.check()
        self.assertIsNone(error)
        self.assertEqual(data["total_copies"], 2)

    def test_isbn_is_optional(self):
        self.assertIsNone(self.check(isbn="")[1])

    def test_rejected_values(self):
        cases = [
            ({"title": ""}, "Title and author"),
            ({"author": "  "}, "Title and author"),
            ({"title": "x" * 201}, "200 characters"),
            ({"author": "x" * 121}, "120 characters"),
            ({"category": "x" * 61}, "60 characters"),
            ({"isbn": "123"}, "ISBN must"),
            ({"total_copies": "abc"}, "must be a number"),
            ({"total_copies": "0"}, "at least 1"),
            ({"total_copies": "-3"}, "at least 1"),
            ({"total_copies": "1001"}, "1000"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                error = self.check(**overrides)[1]
                self.assertIsNotNone(error)
                self.assertIn(message, error)


class MemberFormTests(unittest.TestCase):
    def check(self, password_required=True, **overrides):
        data = {"name": "Asha", "email": "Asha@Test.com ", "password": "secret1"}
        data.update(overrides)
        with flask_app.test_request_context("/members/add", method="POST", data=data):
            return read_member_form(password_required)

    def test_valid_form_cleans_the_email(self):
        data, error = self.check()
        self.assertIsNone(error)
        self.assertEqual(data["email"], "asha@test.com")

    def test_password_is_required_when_adding_but_not_when_editing(self):
        self.assertIn("Password is required", self.check(password="")[1])
        self.assertIsNone(self.check(password_required=False, password="")[1])

    def test_rejected_values(self):
        cases = [
            ({"name": ""}, "Name and email"),
            ({"name": "x" * 101}, "100 characters"),
            ({"email": "not-an-email"}, "valid email"),
            ({"password": "123"}, "at least 6"),
            ({"password": "x" * 129}, "128 characters"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                error = self.check(**overrides)[1]
                self.assertIsNotNone(error)
                self.assertIn(message, error)


class PaginationTests(unittest.TestCase):
    def test_page_arithmetic(self):
        page = pagination.Page(31, 2, 15)
        self.assertEqual((page.pages, page.offset, page.first, page.last), (3, 15, 16, 30))
        self.assertTrue(page.has_prev and page.has_next)

    def test_empty_list_has_one_empty_page(self):
        page = pagination.Page(0, 1, 15)
        self.assertEqual((page.pages, page.first, page.last), (1, 0, 0))
        self.assertFalse(page.has_prev or page.has_next)

    def test_page_number_is_kept_inside_the_range(self):
        self.assertEqual(pagination.Page(31, 99, 15).page, 3)
        self.assertEqual(pagination.Page(31, -4, 15).page, 1)

    def test_page_is_read_from_the_address(self):
        with flask_app.test_request_context("/books/?page=2"):
            self.assertEqual(pagination.paginate(40).page, 2)

    def test_bad_page_value_falls_back_to_page_one(self):
        with flask_app.test_request_context("/books/?page=abc"):
            self.assertEqual(pagination.paginate(40).page, 1)

    def test_page_links_keep_the_search_text(self):
        with flask_app.test_request_context("/books/?q=python&page=1"):
            link = pagination.paginate(40).url(2)
        self.assertIn("q=python", link)
        self.assertIn("page=2", link)


class ConfigCheckTests(unittest.TestCase):
    def problems(self, **settings):
        with mock.patch.multiple(config, **settings):
            with self.assertRaises(startup_checks.ConfigError) as ctx:
                startup_checks.check_config()
        return ctx.exception.problems

    def test_current_settings_are_valid(self):
        startup_checks.check_config()           # must not raise

    def test_each_invalid_setting_is_reported(self):
        cases = [
            ({"DB_HOST": ""}, "DB_HOST"),
            ({"DB_PORT": 0}, "DB_PORT"),
            ({"DB_PORT": 70000}, "DB_PORT"),
            ({"DB_PORT": "abc"}, "DB_PORT"),
            ({"DB_USER": " "}, "DB_USER"),
            ({"DB_NAME": "bad name; DROP TABLE users"}, "DB_NAME"),
            ({"SECRET_KEY": "abc"}, "SECRET_KEY"),
        ]
        for settings, name in cases:
            with self.subTest(settings=settings):
                self.assertIn(name, " ".join(self.problems(**settings)))

    def test_several_problems_are_reported_together(self):
        self.assertEqual(len(self.problems(DB_HOST="", DB_PORT=0)), 2)

    def test_database_errors_get_a_plain_explanation(self):
        cases = [(2003, "Start MySQL"), (1045, "DB_PASSWORD"), (1049, "init_db.py")]
        for errno, expected in cases:
            with self.subTest(errno=errno):
                error = mysql.connector.Error("failure", errno=errno)
                with mock.patch.object(mysql.connector, "connect", side_effect=error):
                    ok, message = startup_checks.check_database()
                self.assertFalse(ok)
                self.assertIn(expected, message)


class DeploymentSettingsTests(unittest.TestCase):
    def test_local_settings_use_a_plain_connection(self):
        with mock.patch.object(config, "DB_SSL", False):
            settings = db.connection_settings()
        self.assertNotIn("ssl_ca", settings)
        self.assertEqual(settings["database"], config.DB_NAME)

    def test_cloud_settings_use_an_encrypted_connection(self):
        fake_certifi = mock.Mock()
        fake_certifi.where.return_value = "/fake/ca.pem"
        with mock.patch.object(config, "DB_SSL", True), mock.patch.dict(sys.modules, {"certifi": fake_certifi}):
            settings = db.connection_settings()
        self.assertEqual(settings["ssl_ca"], "/fake/ca.pem")
        self.assertTrue(settings["ssl_verify_cert"])

    def test_the_database_name_can_be_left_out(self):
        self.assertNotIn("database", db.connection_settings(include_database=False))

    def test_the_cloud_refuses_the_default_secret_key(self):
        with mock.patch.multiple(config, IS_CLOUD=True, SECRET_KEY=config.DEFAULT_SECRET_KEY):
            with self.assertRaises(startup_checks.ConfigError) as ctx:
                startup_checks.check_config()
        self.assertIn("SECRET_KEY", " ".join(ctx.exception.problems))

    def test_a_real_secret_key_is_accepted_in_the_cloud(self):
        with mock.patch.multiple(config, IS_CLOUD=True, SECRET_KEY="a-long-random-value-1234"):
            startup_checks.check_config()           # must not raise

    def test_the_session_cookie_is_protected(self):
        self.assertTrue(flask_app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(flask_app.config["SESSION_COOKIE_SAMESITE"], "Lax")


if __name__ == "__main__":
    unittest.main()
