# Library Management System

Milestone 3 (Implementation). Stack (Milestone 2 ke hisaab se):
HTML, CSS, JavaScript (frontend) + Python Flask (backend) + MySQL (database) + Git/GitHub.

## Modules
- [x] Module 1: Authentication (register, login, logout, admin/member roles)
- [x] Module 2: Book Management (add, edit, delete, search)
- [x] Module 3: Member Management + Profile
- [x] Module 4: Issue / Return + Fine
- [x] Module 5: Reports

## Setup
1. MySQL chalu karo (XAMPP Control Panel me MySQL ke saamne **Start**).
2. `config.py` me DB_USER / DB_PASSWORD check karo (XAMPP me user `root`, password khaali).
3. Terminal me:
```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python init_db.py              # database + tables + dummy data
python app.py                  # http://127.0.0.1:5000
```
Admin login: `admin@library.com` / `admin123`

## Database
`schema.sql` (tables: users, books, issues) aur `seed.sql` (dummy books).
Ye files phpMyAdmin me import karke bhi chala sakte ho.

## Folder structure
- `app.py` - main app, `config.py` - settings, `db.py` - MySQL connection
- `routes/` - module-wise backend code
- `templates/` - HTML, `static/css`, `static/js` - CSS aur JavaScript
