"""Integration tests: dashboard numbers, reports and the profile page."""
from datetime import date, timedelta

from base import (MEMBER_EMAIL, MEMBER_PASSWORD, LibraryTestCase, query, run, run_many, text)
from routes.reports import OVERDUE_LIMIT


class DashboardTests(LibraryTestCase):
    def test_librarian_dashboard_counts(self):
        self.make_loan(MEMBER_EMAIL, "Let Us C", due_in_days=-2)
        self.make_loan(MEMBER_EMAIL, "Wings of Fire", due_in_days=7)
        page = text(self.admin.get("/dashboard"))
        for number, label in ((3, "Books in the catalogue"), (1, "Registered members"), (2, "Books on loan"), (1, "Overdue")):
            self.assertIn('<span class="ledger-num">%d</span><span class="ledger-label">%s</span>' % (number, label), page)
        self.assertIn("Overdue loans", page)
        self.assertIn("Recent loans", page)

    def test_empty_library_shows_helpful_messages(self):
        page = text(self.admin.get("/dashboard"))
        self.assertIn("Nothing is overdue", page)
        self.assertIn("No loans yet", page)

    def test_member_without_loans_sees_a_friendly_message(self):
        self.assertIn("No books on loan", text(self.member.get("/dashboard")))


class ReportTests(LibraryTestCase):
    def test_reports_are_for_the_librarian_only(self):
        self.assertEqual(self.member.get("/reports/").status_code, 302)
        self.assertEqual(self.admin.get("/reports/").status_code, 200)

    def test_report_numbers(self):
        self.make_loan(MEMBER_EMAIL, "Let Us C", due_in_days=-5)
        self.make_loan(MEMBER_EMAIL, "Wings of Fire", returned=True, fine=20)
        page = text(self.admin.get("/reports/"))
        self.assertIn('<span class="ledger-num">1</span><span class="ledger-label">Currently on loan</span>', page)
        self.assertIn('<span class="ledger-num">1</span><span class="ledger-label">Overdue books</span>', page)
        self.assertIn("Rs. 20", page)
        self.assertIn("5 days", page)

    def test_books_with_no_copies_are_listed(self):
        run("UPDATE books SET available_copies = 0 WHERE title = %s", ("Python Crash Course",))
        section = text(self.admin.get("/reports/")).split("Books with no copies left")[1]
        self.assertIn("Python Crash Course", section)

    def test_the_overdue_table_is_capped_but_the_count_is_exact(self):
        uid, bid = self.user_id(MEMBER_EMAIL), self.book_id("Let Us C")
        due = (date.today() - timedelta(days=3)).isoformat()
        issued = (date.today() - timedelta(days=17)).isoformat()
        run_many("INSERT INTO issues (user_id, book_id, issue_date, due_date, return_date, fine) VALUES (%s, %s, %s, %s, NULL, 0)",
                 [(uid, bid, issued, due)] * (OVERDUE_LIMIT + 5))
        page = text(self.admin.get("/reports/"))
        self.assertIn('<span class="ledger-num">%d</span><span class="ledger-label">Overdue books</span>' % (OVERDUE_LIMIT + 5), page)
        self.assertIn("Showing the %d longest overdue loans out of %d" % (OVERDUE_LIMIT, OVERDUE_LIMIT + 5), page)


class ProfileTests(LibraryTestCase):
    def test_details_can_be_changed(self):
        r = self.member.post("/profile", data={"action": "details", "name": "Renamed", "email": MEMBER_EMAIL},
                             follow_redirects=True)
        self.assertIn("Profile updated.", text(r))
        self.assertEqual(query("SELECT name FROM users WHERE email = %s", (MEMBER_EMAIL,))[0]["name"], "Renamed")

    def test_invalid_details_are_rejected(self):
        cases = [
            ({"name": "", "email": MEMBER_EMAIL}, "required"),
            ({"name": "x" * 101, "email": MEMBER_EMAIL}, "100 characters"),
            ({"name": "A", "email": "nope"}, "valid email"),
            ({"name": "A", "email": "admin@test.com"}, "already uses this email"),
        ]
        for data, message in cases:
            with self.subTest(data=data):
                data["action"] = "details"
                self.assertIn(message, text(self.member.post("/profile", data=data)))

    def test_password_change_rules(self):
        base = {"action": "password", "current_password": MEMBER_PASSWORD, "new_password": "newpass1", "confirm_password": "newpass1"}
        cases = [
            (dict(current_password="wrong"), "Current password is incorrect"),
            (dict(new_password="123", confirm_password="123"), "at least 6"),
            (dict(confirm_password="different"), "do not match"),
            (dict(new_password="x" * 129, confirm_password="x" * 129), "128 characters"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                self.assertIn(message, text(self.member.post("/profile", data={**base, **overrides})))

    def test_after_a_password_change_only_the_new_password_works(self):
        self.member.post("/profile", data={"action": "password", "current_password": MEMBER_PASSWORD,
                                           "new_password": "newpass1", "confirm_password": "newpass1"})
        self.assertIn("Email or password is incorrect.", text(
            self.client.post("/login", data={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD})))
        self.assertIn("Books you have on loan", text(
            self.client.post("/login", data={"email": MEMBER_EMAIL, "password": "newpass1"}, follow_redirects=True)))
