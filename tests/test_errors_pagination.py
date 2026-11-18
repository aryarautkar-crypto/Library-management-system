"""Integration tests: friendly error pages, database problems, caching and pagination."""
from unittest import mock

import mysql.connector

import db
from base import MEMBER_EMAIL, LibraryTestCase, query, run, run_many, text
from datetime import date, timedelta


def rows_on(page_html):
    """Count the table rows on a list page (every row has one title cell)."""
    return page_html.count('class="cell-title"')


class ErrorPageTests(LibraryTestCase):
    def test_unknown_address_gives_a_friendly_404(self):
        r = self.client.get("/no-such-page")
        self.assertEqual(r.status_code, 404)
        page = text(r)
        self.assertIn("Page not found", page)
        self.assertIn("Go to the dashboard", page)
        self.assertNotIn("Traceback", page)

    def test_wrong_method_gives_a_friendly_405(self):
        r = self.admin.get("/books/%d/delete" % self.book_id("Let Us C"))
        self.assertEqual(r.status_code, 405)
        self.assertIn("Action not allowed", text(r))

    def test_health_check_reports_a_working_database(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok", "database": "connected"})

    def test_a_database_outage_gives_a_503_page_not_a_crash(self):
        def database_is_down():
            raise mysql.connector.Error("MySQL is down", errno=2003)
        admin = self.admin                      # sign in first, while the database still works
        with mock.patch.object(db, "get_db", database_is_down):
            with self.assertLogs(self.app.logger, level="ERROR"):
                r = admin.get("/books/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("The database is not available", text(r))

    def test_health_check_reports_a_database_outage(self):
        def database_is_down():
            raise mysql.connector.Error("MySQL is down", errno=2003)
        with mock.patch.object(db, "get_db", database_is_down):
            r = self.client.get("/health")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.get_json()["database"], "unavailable")

    def test_an_unexpected_bug_gives_a_500_page(self):
        admin = self.admin
        with mock.patch("routes.reports.fetch_one", side_effect=RuntimeError("boom")):
            with mock.patch.dict(self.app.config, {"PROPAGATE_EXCEPTIONS": False}):
                with self.assertLogs(self.app.logger, level="ERROR"):
                    r = admin.get("/reports/")
        self.assertEqual(r.status_code, 500)
        self.assertIn("Something went wrong", text(r))
        self.assertNotIn("boom", text(r))                       # the technical message is not shown to users


class CachingTests(LibraryTestCase):
    def test_static_files_can_be_cached_by_the_browser(self):
        r = self.client.get("/static/css/style.css")
        self.assertEqual(r.status_code, 200)
        self.assertIn("max-age=604800", r.headers["Cache-Control"])
        r.close()

    def test_pages_link_to_versioned_static_files(self):
        page = text(self.client.get("/login"))
        self.assertIn("style.css?v=", page)
        self.assertIn("main.js?v=", page)


class PaginationTests(LibraryTestCase):
    def add_books(self, count, prefix="Bulk Book"):
        run_many("INSERT INTO books (title, author, isbn, category, total_copies, available_copies) VALUES (%s, %s, %s, %s, 1, 1)",
                 [("%s %03d" % (prefix, i), "Author", None, "Bulk") for i in range(count)])

    def test_the_book_list_is_split_into_pages(self):
        self.add_books(35)                                       # 38 books in total
        first = text(self.admin.get("/books/"))
        self.assertEqual(rows_on(first), 15)
        self.assertIn("Page 1 of 3", first)
        self.assertIn("Showing 1 to 15 of 38", first)
        last = text(self.admin.get("/books/?page=3"))
        self.assertEqual(rows_on(last), 8)
        self.assertIn("Page 3 of 3", last)
        self.assertNotIn(">Next<", last)

    def test_bad_page_numbers_are_handled(self):
        self.add_books(35)
        for value, expected in (("abc", 1), ("0", 1), ("-2", 1), ("999", 3)):
            with self.subTest(page=value):
                page = text(self.admin.get("/books/?page=" + value))
                self.assertIn("Page %d of 3" % expected, page)

    def test_search_results_are_paged_and_keep_the_search_text(self):
        self.add_books(35)
        page = text(self.admin.get("/books/?q=Bulk"))
        self.assertIn("Showing 1 to 15 of 35", page)
        self.assertIn("q=Bulk", page.split("Page 1 of 3")[1])    # the Next link keeps the search

    def test_a_short_list_has_no_pager(self):
        self.assertNotIn("Page 1 of", text(self.admin.get("/books/")))

    def test_the_member_list_is_paged(self):
        run_many("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, 'x', 'member')",
                 [("Member %02d" % i, "m%02d@test.com" % i) for i in range(20)])      # 21 members in total
        self.assertEqual(rows_on(text(self.admin.get("/members/"))), 15)
        self.assertEqual(rows_on(text(self.admin.get("/members/?page=2"))), 6)

    def test_the_loan_list_is_paged(self):
        uid, bid = self.user_id(MEMBER_EMAIL), self.book_id("Let Us C")
        day = date.today().isoformat()
        run_many("INSERT INTO issues (user_id, book_id, issue_date, due_date, return_date, fine) VALUES (%s, %s, %s, %s, %s, 0)",
                 [(uid, bid, day, day, day)] * 35)
        self.assertEqual(rows_on(text(self.admin.get("/issues/"))), 15)
        self.assertEqual(rows_on(text(self.admin.get("/issues/?page=3"))), 5)
        self.assertEqual(rows_on(text(self.member.get("/issues/?page=2"))), 15)
        self.assertIn("Showing 1 to 15 of 35", text(self.admin.get("/issues/")))
