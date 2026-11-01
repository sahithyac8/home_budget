import os
import secrets

from dotenv import load_dotenv

load_dotenv()  # reads the local .env file if there is one (it is never uploaded to GitHub)

# If SECRET_KEY is missing, or is still one of the placeholder values from .env.example, use a random
# key for this run only. The app still starts, but everyone is logged out whenever it restarts.
_PLACEHOLDER_KEYS = {"", "change-me", "change-me-too", "change-me-in-production"}
_secret = os.environ.get("SECRET_KEY", "")
SECRET_KEY_IS_RANDOM = _secret in _PLACEHOLDER_KEYS


class Config:
    SECRET_KEY = secrets.token_hex(32) if SECRET_KEY_IS_RANDOM else _secret
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "home_budget")
    MYSQL_SSL_CA = os.environ.get("MYSQL_SSL_CA", "")  # path to a CA file; needed by hosted MySQL services
    CURRENCY = os.environ.get("CURRENCY", "₹")

    # Login cookie settings. SameSite=Lax means other websites cannot make the browser send the
    # cookie with a form post, which is our protection against cross-site request forgery.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE") == "1"  # set to 1 on the live site (HTTPS)
