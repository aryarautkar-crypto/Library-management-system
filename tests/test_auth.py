"""Integration tests: registration, sign in, sign out and who may open which page."""
from base import (ADMIN_EMAIL, MEMBER_EMAIL, MEMBER_PASSWORD, LibraryTestCase, query, run, text)


class RegisterTests(LibraryTestCase):
    def test_registration_creates_a_member_with_a_hashed_password(self):
        r = self.client.post("/register", data={"name": "New Person", "email": "new@test.com", "password": "secret1"},
                             follow_redirects=True)
        self.assertIn("Account created", text(r))
        row = query("SELECT role, password_hash FROM users WHERE email = %s", ("new@test.com",))[0]
        self.assertEqual(row["role"], "member")
        self.assertNotEqual(row["password_hash"], "secret1")        # never stored as plain text

    def test_invalid_registrations_are_rejected(self):
        cases = [
            ({"name": "", "email": "a@b.com", "password": "secret1"}, "fill in all fields"),
            ({"name": "A", "email": "not-an-email", "password": "secret1"}, "valid email"),
            ({"name": "A", "email": "a@b.com", "password": "123"}, "at least 6 characters"),
            ({"name": "A" * 101, "email": "a@b.com", "password": "secret1"}, "100 characters"),
            ({"name": "A", "email": "a@b.com", "password": "x" * 129}, "128 characters"),
        ]
        for data, message in cases:
            with self.subTest(data=data):
                before = self.count("users")
                self.assertIn(message, text(self.client.post("/register", data=data)))
                self.assertEqual(self.count("users"), before)

    def test_duplicate_email_is_rejected_even_with_different_capitals(self):
        r = self.client.post("/register", data={"name": "X", "email": MEMBER_EMAIL.upper(), "password": "secret1"})
        self.assertIn("already registered", text(r))

    def test_missing_form_field_gives_a_friendly_400_page(self):
        r = self.client.post("/register", data={})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Request not understood", text(r))


class SignInTests(LibraryTestCase):
    def test_admin_can_sign_in(self):
        r = self.client.post("/login", data={"email": ADMIN_EMAIL, "password": "admin-pass-1"}, follow_redirects=True)
        self.assertIn("Welcome back, Test Librarian", text(r))

    def test_member_can_sign_in(self):
        r = self.client.post("/login", data={"email": MEMBER_EMAIL, "password": MEMBER_PASSWORD}, follow_redirects=True)
        self.assertIn("Books you have on loan", text(r))

    def test_wrong_password_and_unknown_email_get_the_same_message(self):
        for email, password in ((MEMBER_EMAIL, "wrong"), ("nobody@test.com", "whatever")):
            with self.subTest(email=email):
                r = self.client.post("/login", data={"email": email, "password": password})
                self.assertIn("Email or password is incorrect.", text(r))

    def test_sign_out_ends_the_session(self):
        r = self.member.get("/logout", follow_redirects=True)
        self.assertIn("You have been signed out.", text(r))
        self.assertIn("/login", self.member.get("/dashboard").headers["Location"])

    def test_a_deleted_user_is_signed_out_on_the_next_request(self):
        self.member.get("/dashboard")
        run("DELETE FROM users WHERE email = %s", (MEMBER_EMAIL,))
        self.assertIn("/login", self.member.get("/dashboard").headers["Location"])


class AccessControlTests(LibraryTestCase):
    def test_anonymous_visitors_are_sent_to_the_login_page(self):
        for url in ("/dashboard", "/books/", "/issues/", "/profile", "/members/", "/reports/"):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertIn("/login", r.headers["Location"])

    def test_member_cannot_open_librarian_pages(self):
        for url in ("/members/", "/members/add", "/reports/", "/issues/issue", "/books/add"):
            with self.subTest(url=url):
                r = self.member.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertIn("/dashboard", r.headers["Location"])

    def test_member_cannot_send_librarian_actions(self):
        books_before = self.count("books")
        self.member.post("/books/add", data={"title": "Sneaky", "author": "X", "isbn": "", "category": "", "total_copies": "1"})
        self.member.post("/books/%d/delete" % self.book_id("Let Us C"))
        self.assertEqual(self.count("books"), books_before)

    def test_librarian_pages_explain_why_a_member_was_turned_away(self):
        r = self.member.get("/reports/", follow_redirects=True)
        self.assertIn("That page is for the librarian only.", text(r))
