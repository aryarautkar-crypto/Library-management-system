# Library Management System

Milestone 3 (Implementation) and Milestone 4 (Testing and Optimization).
Stack, as chosen in Milestone 2: HTML, CSS, JavaScript (front end), Python Flask (back end),
MySQL (database), Git and GitHub (version control).

## Modules
- [x] Module 1: Authentication (register, sign in, sign out, admin and member roles)
- [x] Module 2: Book Management (add, edit, delete, search)
- [x] Module 3: Member Management and Profile
- [x] Module 4: Issue, Return and Fine
- [x] Module 5: Reports

## Features
- Light and dark theme (the toggle is in the header; the choice is remembered)
- Role based access: the admin manages everything, a member sees books and their own loans
- Long lists are shown 15 rows per page, with search and filters kept between pages
- Friendly error pages (404, 405, 400, 500) and a clear page when the database is not available
- `/health` shows whether the site and the database are working

## Setup
1. Start MySQL (in the XAMPP Control Panel, press **Start** next to MySQL).
2. Check `DB_USER` and `DB_PASSWORD` in `config.py` (XAMPP: user `root`, empty password).
3. In a terminal:
```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python init_db.py              # creates the database, tables, indexes and sample data
python app.py                  # open http://127.0.0.1:5000
```
Admin login: `admin@library.com` / `admin123`

If a database was created before the indexes were added, run `python add_indexes.py` once.
Set the environment variable `FLASK_DEBUG=1` if you want the server to reload while you edit code.

## Testing (Milestone 4)
```bash
python -m unittest discover -s tests -v
```
MySQL must be running. The tests build their own database called `library_test`, so your real data is never touched.

- `tests/test_unit.py`: unit tests for the fine calculation, form validation, pagination, input checks and the startup configuration check
- `tests/test_auth.py`, `test_books.py`, `test_members.py`, `test_issues.py`, `test_reports_profile.py`: integration tests that use the real pages and the database
- `tests/test_errors_pagination.py`: error pages, database outage, caching and pagination

## Performance (Milestone 4)
- Database indexes (in `schema.sql`) for the sorted lists, open and overdue loans, and loans of one member
- Pagination (15 rows per page) and filtering in SQL, so a page loads only the rows it shows
- Dashboard and report numbers are fetched with one query each
- CSS and JavaScript are cached by the browser and linked with a version number
- `python benchmark.py` measures the pages with 10,000 books and 20,000 loans, before and after, and saves `benchmark_results.txt`

## Folder structure
- `app.py` is the main application, `config.py` holds the settings, `db.py` handles the MySQL connection
- `routes/` has one file per module; `validators.py`, `pagination.py` and `startup_checks.py` hold shared helpers
- `templates/` holds the HTML pages; `static/css` and `static/js` hold the CSS and JavaScript
- `schema.sql`, `seed.sql`, `init_db.py`, `add_indexes.py`, `dbsetup.py` handle the database
- `tests/` holds the automated tests and `benchmark.py` the performance measurements
