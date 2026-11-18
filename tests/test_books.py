"""Integration tests: book catalogue (list, search, add, edit, delete)."""
from base import MEMBER_EMAIL, LibraryTestCase, query, text


def book_form(**overrides):
    data = {"title": "New Book", "author": "New Author", "isbn": "9780000000001", "category": "Testing", "total_copies": "2"}
    data.update(overrides)
    return data


class ListAndSearchTests(LibraryTestCase):
    def test_everyone_signed_in_can_see_the_catalogue(self):
        for client in (self.admin, self.member):
            page = text(client.get("/books/"))
            self.assertIn("Let Us C", page)
            self.assertIn("3 books in the catalogue", page)

    def test_only_the_librarian_sees_the_action_buttons(self):
        self.assertIn("Add a book", text(self.admin.get("/books/")))
        self.assertNotIn("Add a book", text(self.member.get("/books/")))
        self.assertNotIn(">Delete<", text(self.member.get("/books/")))

    def test_search_matches_title_author_isbn_and_category(self):
        cases = {"wings": "Wings of Fire", "matthes": "Python Crash Course",
                 "9788183331630": "Let Us C", "biography": "Wings of Fire"}
        for term, expected in cases.items():
            with self.subTest(term=term):
                page = text(self.admin.get("/books/?q=" + term))
                self.assertIn(expected, page)
                self.assertIn("1 result for", page)

    def test_search_without_matches_explains_it(self):
        page = text(self.admin.get("/books/?q=zzzz"))
        self.assertIn("No books match", page)
        self.assertIn("0 results for", page)

    def test_availability_is_shown(self):
        self.make_loan(MEMBER_EMAIL, "Python Crash Course")
        page = text(self.admin.get("/books/"))
        self.assertIn("All 1 on loan", page)
        self.assertIn("2 of 2 available", page)


class AddTests(LibraryTestCase):
    def test_adding_a_book_makes_all_copies_available(self):
        r = self.admin.post("/books/add", data=book_form(), follow_redirects=True)
        self.assertIn("Book added.", text(r))
        row = query("SELECT total_copies, available_copies FROM books WHERE title = %s", ("New Book",))[0]
        self.assertEqual((row["total_copies"], row["available_copies"]), (2, 2))

    def test_rejected_input_adds_nothing(self):
        cases = [
            (dict(title=""), "Title and author"),
            (dict(title="x" * 201), "200 characters"),
            (dict(total_copies="abc"), "must be a number"),
            (dict(total_copies="0"), "at least 1"),
            (dict(total_copies="1001"), "1000"),
            (dict(isbn="123"), "ISBN must"),
            (dict(isbn="9788183331630"), "already exists"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                before = self.count("books")
                self.assertIn(message, text(self.admin.post("/books/add", data=book_form(**overrides))))
                self.assertEqual(self.count("books"), before)

    def test_the_form_keeps_what_the_user_typed_after_an_error(self):
        page = text(self.admin.post("/books/add", data=book_form(title="Typed Title", total_copies="abc")))
        self.assertIn('value="Typed Title"', page)

    def test_several_books_can_have_no_isbn(self):
        for title in ("No ISBN One", "No ISBN Two"):
            r = self.admin.post("/books/add", data=book_form(title=title, isbn=""), follow_redirects=True)
            self.assertIn("Book added.", text(r))

    def test_markup_in_a_title_is_shown_as_text_not_run(self):
        self.admin.post("/books/add", data=book_form(title="<script>alert(1)</script>"))
        page = text(self.admin.get("/books/"))
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)


class EditTests(LibraryTestCase):
    def test_editing_changes_the_book(self):
        bid = self.book_id("Let Us C")
        r = self.admin.post("/books/%d/edit" % bid, data=book_form(title="Let Us C 2nd Edition", isbn="9788183331630"),
                            follow_redirects=True)
        self.assertIn("Book updated.", text(r))
        self.assertEqual(query("SELECT title FROM books WHERE book_id = %s", (bid,))[0]["title"], "Let Us C 2nd Edition")

    def test_more_copies_are_added_to_the_available_count(self):
        self.make_loan(MEMBER_EMAIL, "Let Us C")                    # 1 of 2 on loan
        bid = self.book_id("Let Us C")
        self.admin.post("/books/%d/edit" % bid, data=book_form(isbn="9788183331630", total_copies="5"))
        row = query("SELECT total_copies, available_copies FROM books WHERE book_id = %s", (bid,))[0]
        self.assertEqual((row["total_copies"], row["available_copies"]), (5, 4))

    def test_total_cannot_drop_below_the_copies_on_loan(self):
        self.make_loan(MEMBER_EMAIL, "Let Us C")
        self.make_loan(MEMBER_EMAIL, "Let Us C")                    # both copies on loan
        bid = self.book_id("Let Us C")
        r = self.admin.post("/books/%d/edit" % bid, data=book_form(isbn="9788183331630", total_copies="1"))
        self.assertIn("2 copies are on loan", text(r))

    def test_an_isbn_used_by_another_book_is_rejected(self):
        bid = self.book_id("Let Us C")
        r = self.admin.post("/books/%d/edit" % bid, data=book_form(isbn="9781593279288"))
        self.assertIn("Another book already uses this ISBN", text(r))

    def test_editing_a_missing_book_gives_a_404_page(self):
        r = self.admin.get("/books/99999/edit")
        self.assertEqual(r.status_code, 404)
        self.assertIn("Page not found", text(r))


class DeleteTests(LibraryTestCase):
    def test_a_book_without_loans_can_be_deleted(self):
        r = self.admin.post("/books/%d/delete" % self.book_id("Wings of Fire"), follow_redirects=True)
        self.assertIn("Book deleted.", text(r))
        self.assertEqual(self.count("books"), 2)

    def test_a_book_with_loan_records_cannot_be_deleted(self):
        self.make_loan(MEMBER_EMAIL, "Wings of Fire", returned=True)   # even a returned loan is a record
        r = self.admin.post("/books/%d/delete" % self.book_id("Wings of Fire"), follow_redirects=True)
        self.assertIn("cannot be deleted", text(r))
        self.assertEqual(self.count("books"), 3)

    def test_deleting_a_missing_book_gives_a_404(self):
        self.assertEqual(self.admin.post("/books/99999/delete").status_code, 404)
