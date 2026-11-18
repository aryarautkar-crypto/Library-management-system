"""Pagination: long lists are shown a page at a time instead of all at once."""
from flask import request, url_for

PER_PAGE = 15


class Page:
    def __init__(self, total, page, per_page):
        self.total = total
        self.per_page = per_page
        self.pages = max(1, -(-total // per_page))        # ceiling division
        self.page = min(max(page, 1), self.pages)         # keep the page number inside 1..pages
        self.offset = (self.page - 1) * per_page
        self.first = self.offset + 1 if total else 0
        self.last = min(self.offset + per_page, total)
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages

    def url(self, page):
        """Link to another page of the same list, keeping search and filter values."""
        args = request.args.to_dict()
        args["page"] = page
        return url_for(request.endpoint, **args)


def paginate(total, per_page=None):
    """Build a Page from the ?page= value of the current request (bad values fall back to page 1)."""
    per_page = per_page or PER_PAGE
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    return Page(total, page, per_page)
