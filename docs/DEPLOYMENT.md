# Putting the site on the internet for free

The app is a Flask program with a MySQL database, so it needs two free services:

| Part | Service | Why |
|---|---|---|
| The website (Flask) | [Render](https://render.com) free web service | Builds straight from your GitHub repository; no credit card |
| The MySQL database | [Aiven](https://aiven.io/free-mysql-database) free MySQL (1 GB) | A real MySQL server with a free plan; no credit card |

PythonAnywhere is not used because its free plan no longer includes MySQL for new accounts.
Free-tier rules change, so check the two sites if something below looks different.

## Steps (short version; the full illustrated guide is the shared document)

1. **Upload the latest code to GitHub** (never upload `.env`; `.gitignore` already blocks it).
2. **Aiven:** create a free MySQL service, copy Host, Port, User, Password and Database name, and download the CA certificate (`ca.pem`). Put `ca.pem` in the project folder and upload it too (it is a public certificate, not a secret).
3. **Create the tables** from your laptop: temporarily point `.env` at Aiven (add `MYSQL_SSL_CA=ca.pem`), then run `python init_db.py` (add `--demo` for the demo account).
4. **Render:** New + > Web Service > pick your repository, then
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --workers 1 --timeout 60`
   - Instance type: Free
5. **Environment variables on Render** (never in GitHub):

| Name | Value |
|---|---|
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB` | from the Aiven page |
| `MYSQL_SSL_CA` | `ca.pem` |
| `SECRET_KEY` | long random text: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SESSION_COOKIE_SECURE` | `1` |

6. Open `https://<your-service-name>.onrender.com/health`: it should show `{"status":"ok","database":"up"}`. Then sign up.

## Things to know
- A free Render site sleeps after 15 minutes without visitors; the next visit takes about a minute to wake it. Open it a few minutes before showing anyone.
- A free Aiven database can power itself off when it is idle; switch it on again from the Aiven console.
- Pushing new code to GitHub redeploys the site automatically.
- This is a learning project: do not enter real bank details.
