"""Integration tests: member management (admin only)."""
from base import ADMIN_EMAIL, MEMBER_EMAIL, LibraryTestCase, query, text


def member_form(**overrides):
    data = {"name": "New Member", "email": "new.member@test.com", "password": "secret1"}
    data.update(overrides)
    return data


class MemberTests(LibraryTestCase):
    def test_list_shows_members_but_not_the_librarian(self):
        page = text(self.admin.get("/members/"))
        self.assertIn("Test Member", page)
        self.assertNotIn(ADMIN_EMAIL, page)

    def test_search_by_name_or_email(self):
        self.add_member_row("Priya Sharma", "priya@test.com")
        for term in ("priya", "sharma", "priya@test"):
            with self.subTest(term=term):
                page = text(self.admin.get("/members/?q=" + term))
                self.assertIn("Priya Sharma", page)
                self.assertNotIn("Test Member", page)

    def test_adding_a_member(self):
        r = self.admin.post("/members/add", data=member_form(), follow_redirects=True)
        self.assertIn("Member added.", text(r))
        row = query("SELECT role, password_hash FROM users WHERE email = %s", ("new.member@test.com",))[0]
        self.assertEqual(row["role"], "member")
        self.assertNotEqual(row["password_hash"], "secret1")

    def test_rejected_input_adds_nothing(self):
        cases = [
            (dict(name=""), "Name and email"),
            (dict(email="nope"), "valid email"),
            (dict(password=""), "Password is required"),
            (dict(password="123"), "at least 6"),
            (dict(email=MEMBER_EMAIL), "already registered"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                before = self.count("users")
                self.assertIn(message, text(self.admin.post("/members/add", data=member_form(**overrides))))
                self.assertEqual(self.count("users"), before)

    def test_editing_without_a_password_keeps_the_old_one(self):
        uid = self.user_id(MEMBER_EMAIL)
        old = query("SELECT password_hash FROM users WHERE user_id = %s", (uid,))[0]["password_hash"]
        r = self.admin.post("/members/%d/edit" % uid, data=member_form(name="Renamed", email=MEMBER_EMAIL, password=""),
                            follow_redirects=True)
        self.assertIn("Member updated.", text(r))
        row = query("SELECT name, password_hash FROM users WHERE user_id = %s", (uid,))[0]
        self.assertEqual((row["name"], row["password_hash"]), ("Renamed", old))

    def test_editing_with_a_password_changes_it(self):
        uid = self.user_id(MEMBER_EMAIL)
        old = query("SELECT password_hash FROM users WHERE user_id = %s", (uid,))[0]["password_hash"]
        self.admin.post("/members/%d/edit" % uid, data=member_form(email=MEMBER_EMAIL, password="brandnew1"))
        self.assertNotEqual(query("SELECT password_hash FROM users WHERE user_id = %s", (uid,))[0]["password_hash"], old)

    def test_an_email_used_by_another_member_is_rejected(self):
        self.add_member_row("Other", "other@test.com")
        r = self.admin.post("/members/%d/edit" % self.user_id(MEMBER_EMAIL), data=member_form(email="other@test.com"))
        self.assertIn("Another member already uses this email", text(r))

    def test_member_with_loan_records_cannot_be_deleted(self):
        self.make_loan(MEMBER_EMAIL, "Let Us C", returned=True)
        r = self.admin.post("/members/%d/delete" % self.user_id(MEMBER_EMAIL), follow_redirects=True)
        self.assertIn("cannot be deleted", text(r))

    def test_member_without_loans_can_be_deleted(self):
        self.add_member_row("Temp", "temp@test.com")
        r = self.admin.post("/members/%d/delete" % self.user_id("temp@test.com"), follow_redirects=True)
        self.assertIn("Member deleted.", text(r))

    def test_the_librarian_account_cannot_be_reached_through_member_pages(self):
        admin_id = self.user_id(ADMIN_EMAIL)
        self.assertEqual(self.admin.get("/members/%d/edit" % admin_id).status_code, 404)
        self.assertEqual(self.admin.post("/members/%d/delete" % admin_id).status_code, 404)
        self.assertEqual(self.count("users"), 2)
