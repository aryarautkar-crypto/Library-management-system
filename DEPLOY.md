# Deployment Guide

This guide has two parts: running the project on your own computer (local), and putting it on the internet (cloud).
The cloud setup below uses two free services that do not ask for a credit card: **TiDB Cloud Starter** (a MySQL-compatible database)
and **Render** (the web server). Free plans can change, so check the pricing page of each service before you start.

## Settings used by the application

Every setting can be given as an environment variable. If a variable is not set, the local default is used.

| Variable | Meaning | Local default |
|---|---|---|
| `DB_HOST` | Address of the MySQL server | `localhost` |
| `DB_PORT` | Port of the MySQL server | `3306` (TiDB Cloud uses `4000`) |
| `DB_USER` | Database user | `root` |
| `DB_PASSWORD` | Database password | empty (XAMPP) |
| `DB_NAME` | Database name | `library_db` |
| `DB_SSL` | `1` for an encrypted connection (needed for cloud databases) | `0` |
| `SECRET_KEY` | Secret used to sign login sessions. Must be changed in the cloud | a fixed demo value |
| `ADMIN_PASSWORD` | Password of the librarian account created by `init_db.py` | `admin123` |
| `RENDER` | Set by Render itself. The app then treats itself as running in the cloud | not set |

## Part A: Local setup (your own computer)

1. Install Python 3 and XAMPP. In the XAMPP Control Panel press **Start** next to MySQL.
2. Open a terminal in the project folder (the one that contains `app.py`) and run:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python app.py
```
3. Open `http://127.0.0.1:5000`. The librarian login is `admin@library.com` and the password `admin123`.
4. To run the automated tests: `python -m unittest discover -s tests -v`

## Part B: Cloud setup (TiDB Cloud + Render)

### B1. Put the code on GitHub
```bash
git add .
git commit -m "Prepare for deployment"
git push
```
Open the repository page on GitHub and check that the newest files (for example `DEPLOY.md` and `gunicorn` in `requirements.txt`) are there. Render deploys from GitHub.

### B2. Create the database (TiDB Cloud Starter)
1. Sign up at tidbcloud.com (no credit card is needed for the free Starter plan) and create a **Starter** cluster in the region nearest to you.
2. Open the cluster and press **Connect**. Allow connections from anywhere (public access) if it asks, and generate a password.
3. Write down these four values: **host**, **port** (4000), **user** and **password**. Keep the password private.

### B3. Create the tables in the cloud database (from your laptop)
In PowerShell, in the project folder, set the values (use your own values) and run `init_db.py`:
```powershell
$env:DB_HOST = "gateway01.xxxx.prod.aws.tidbcloud.com"
$env:DB_PORT = "4000"
$env:DB_USER = "xxxx.root"
$env:DB_PASSWORD = "the-password-from-tidb"
$env:DB_SSL = "1"
$env:ADMIN_PASSWORD = "choose-a-strong-password"
py -m pip install -r requirements.txt
py init_db.py
```
The message `Database ready!` means the tables and the sample books are created. These variables exist only in this terminal window.
If you choose a remote database and forget `ADMIN_PASSWORD`, the script stops and asks for it, so the default password is never used online.

### B4. Create the web service (Render)
1. Sign up at render.com with your GitHub account (no credit card is needed for the free plan).
2. Press **New +**, then **Web Service**, and pick your repository.
3. Fill in:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
4. Under **Environment Variables** add: `DB_HOST`, `DB_PORT` (4000), `DB_USER`, `DB_PASSWORD`, `DB_NAME` (`library_db`), `DB_SSL` (`1`), and `SECRET_KEY`.
   Make a secret key with: `py -c "import secrets; print(secrets.token_hex(32))"`
5. Under **Advanced**, set **Health Check Path** to `/health`.
6. Press **Create Web Service**. The first build takes a few minutes. Then open the link that looks like `https://your-name.onrender.com`.

### B5. Check that it works
- The login page opens, and you can sign in with `admin@library.com` and the `ADMIN_PASSWORD` you chose.
- `https://your-name.onrender.com/health` shows `{"database":"connected","status":"ok"}`.

### B6. Things to know
- On the free plan the service goes to sleep after 15 minutes without visitors. The next visit needs about a minute to wake it up. Open the link a few minutes before a demo or viva.
- Every `git push` to GitHub deploys the new version automatically.
- Never put passwords in the code or in GitHub. They belong only in environment variables.
- Pages that need the database show a friendly error page if the database cannot be reached.

## Troubleshooting

| Problem | What to check |
|---|---|
| Build fails with a Python version message | In Render add the environment variable `PYTHON_VERSION` with a value such as `3.12.8` and deploy again |
| The app stops with "SECRET_KEY must be changed" | Add the `SECRET_KEY` environment variable in Render |
| "Can't connect to MySQL server" | Check `DB_HOST`, `DB_PORT` and that the database allows public connections |
| An SSL or certificate error | Check that `DB_SSL` is `1` and that `certifi` is in `requirements.txt` |
| "Access denied for user" | Check `DB_USER` (it usually looks like `xxxx.root`) and `DB_PASSWORD` |
| The librarian cannot sign in | Run `py init_db.py` again with the `ADMIN_PASSWORD` you want (this recreates the tables and removes old data) |
