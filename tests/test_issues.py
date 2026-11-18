"""Integration tests: issuing and returning books, fines and the loan list."""
from datetime import date, timedelta

from base import (ADMIN_EMAIL, MEMBER_EMAIL, LibraryTestCase, query, run, text)
from routes.issues import FINE_PER_DAY, MAX_BOOKS


def copies(title):
    return query("SELECT available_copies FROM books WHERE title = %s", (title,))[0]["available_copies"]


class IssueTests(LibraryTestCase):
    def test_issuing_a_book_records_the_loan_and_reduces_the_copies(self):
        r = self.issue(MEMBER_EMAIL, "Let Us C")
        due = (date.today() + timedelta(days=14)).isoformat()
        self.assertIn("Book issued. Due on " + due, text(r))
        self.assertEqual(copies("Let Us C"), 1)
        loan = query("SELECT due_date, return_date FROM issues")[0]
        self.assertEqual(str(loan["due_date"]), due)
        self.assertIsNone(loan["return_date"])

    def test_the_same_book_cannot_be_issued_twice_to_one_member(self):
        self.issue(MEMBER_EMAIL, "Let Us C")
        self.assertIn("already has this book", text(self.issue(MEMBER_EMAIL, "Let Us C")))
        self.assertEqual(self.count("issues"), 1)

    def test_a_member_can_hold_only_a_limited_number_of_books(self):
        run("INSERT INTO books (title, author, isbn, category, total_copies, available_copies) "
            "VALUES ('Fourth Book', 'X', NULL, NULL, 1, 1)")
        titles = ["Let Us C", "Python Crash Course", "Wings of Fire", "Fourth Book"]
        for title in titles[:MAX_BOOKS]:
            self.assertIn("Book issued.", text(self.issue(MEMBER_EMAIL, title)))
        self.assertIn("limit %d" % MAX_BOOKS, text(self.issue(MEMBER_EMAIL, titles[MAX_BOOKS])))
        self.assertEqual(self.count("issues"), MAX_BOOKS)

    def test_the_last_copy_can_only_be_issued_once(self):
        self.add_member_row("Second Member", "second@test.com")
        self.assertIn("Book issued.", text(self.issue(MEMBER_EMAIL, "Python Crash Course")))
        self.assertIn("No copy of this book is available", text(self.issue("second@test.com", "Python Crash Course")))
        self.assertEqual(copies("Python Crash Course"), 0)
        self.assertEqual(self.count("issues"), 1)

    def test_invalid_loan_periods_are_rejected(self):
        cases = {"0": "between 1 and 60", "61": "between 1 and 60", "abc": "Choose a member"}
        for days, message in cases.items():
            with self.subTest(days=days):
                self.assertIn(message, text(self.issue(MEMBER_EMAIL, "Let Us C", days=days)))
        self.assertEqual(self.count("issues"), 0)

    def test_only_members_can_borrow(self):
        r = self.admin.post("/issues/issue", data={"user_id": str(self.user_id(ADMIN_EMAIL)),
                                                    "book_id": str(self.book_id("Let Us C")), "days": "14"})
        self.assertIn("Member or book not found", text(r))
        r = self.admin.post("/issues/issue", data={"user_id": "99999", "book_id": "99999", "days": "14"})
        self.assertIn("Member or book not found", text(r))


class ReturnTests(LibraryTestCase):
    def test_returning_on_time_restores_the_copy_without_a_fine(self):
        loan = self.make_loan(MEMBER_EMAIL, "Let Us C", due_in_days=3)
        r = self.admin.post("/issues/%d/return" % loan, follow_redirects=True)
        self.assertIn("Book returned. No fine.", text(r))
        row = query("SELECT return_date, fine FROM issues WHERE issue_id = %s", (loan,))[0]
        self.assertIsNotNone(row["return_date"])
        self.assertEqual(row["fine"], 0)
        self.assertEqual(copies("Let Us C"), 2)

    def test_returning_late_charges_a_fine_per_day(self):
        loan = self.make_loan(MEMBER_EMAIL, "Let Us C", due_in_days=-4)
        r = self.admin.post("/issues/%d/return" % loan, follow_redirects=True)
        self.assertIn("4 days late, fine Rs. %d" % (4 * FINE_PER_DAY), text(r))
        self.assertEqual(query("SELECT fine FROM issues WHERE issue_id = %s", (loan,))[0]["fine"], 4 * FINE_PER_DAY)

    def test_a_loan_cannot_be_returned_twice(self):
        loan = self.make_loan(MEMBER_EMAIL, "Let Us C")
        self.admin.post("/issues/%d/return" % loan)
        r = self.admin.post("/issues/%d/return" % loan, follow_redirects=True)
        self.assertIn("already been returned", text(r))
        self.assertEqual(copies("Let Us C"), 2)             # not increased a second time

    def test_returning_an_unknown_loan_gives_a_404(self):
        self.assertEqual(self.admin.post("/issues/99999/return").status_code, 404)

    def test_a_member_cannot_return_a_book(self):
        loan = self.make_loan(MEMBER_EMAIL, "Let Us C")
        self.member.post("/issues/%d/return" % loan)
        self.assertIsNone(query("SELECT return_date FROM issues WHERE issue_id = %s", (loan,))[0]["return_date"])


class LoanListTests(LibraryTestCase):
    def setUp(self):
        super().setUp()
        self.make_loan(MEMBER_EMAIL, "Let Us C", due_in_days=5)                 # on loan, on time
        self.make_loan(MEMBER_EMAIL, "Python Crash Course", due_in_days=-3)     # overdue
        self.make_loan(MEMBER_EMAIL, "Wings of Fire", returned=True)            # returned

    def test_filters_show_the_right_loans(self):
        expected = {
            "all": {"Let Us C", "Python Crash Course", "Wings of Fire"},
            "issued": {"Let Us C", "Python Crash Course"},
            "overdue": {"Python Crash Course"},
            "returned": {"Wings of Fire"},
        }
        every_title = expected["all"]
        for status, titles in expected.items():
            with self.subTest(status=status):
                page = text(self.admin.get("/issues/?status=" + status))
                for title in every_title:
                    self.assertEqual(title in page, title in titles, "%s under %s" % (title, status))

    def test_filter_tabs_show_counts(self):
        page = text(self.admin.get("/issues/"))
        for label, number in (("All", 3), ("On loan", 2), ("Overdue", 1), ("Returned", 1)):
            self.assertIn('%s<span class="seg-count">%d</span>' % (label, number), page)

    def test_an_unknown_filter_falls_back_to_all(self):
        page = text(self.admin.get("/issues/?status=hacked"))
        for title in ("Let Us C", "Python Crash Course", "Wings of Fire"):
            self.assertIn(title, page)

    def test_overdue_loans_show_the_days_late_and_the_fine(self):
        page = text(self.admin.get("/issues/?status=overdue"))
        self.assertIn("3 days late", page)
        self.assertIn("Rs. %d" % (3 * FINE_PER_DAY), page)

    def test_a_member_sees_only_their_own_loans(self):
        self.add_member_row("Other Member", "other@test.com")
        run("INSERT INTO books (title, author, isbn, category, total_copies, available_copies) "
            "VALUES ('Private Book', 'X', NULL, NULL, 1, 1)")
        self.make_loan("other@test.com", "Private Book")
        page = text(self.member.get("/issues/"))
        self.assertIn("Let Us C", page)
        self.assertNotIn("Private Book", page)
        self.assertNotIn(">Return<", page)                  # members cannot return books

    def test_the_member_dashboard_marks_late_books(self):
        page = text(self.member.get("/dashboard"))
        self.assertIn("3 days late, fine Rs. %d" % (3 * FINE_PER_DAY), page)
        self.assertIn("On time", page)
