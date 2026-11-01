import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app


def connect(cfg, database=True):
    """Open a MySQL connection from a config mapping (also used by init_db.py).

    Hosted MySQL services require an encrypted connection: set MYSQL_SSL_CA to the path of the
    certificate file they give you and the connection is encrypted and verified.
    """
    options = {}
    if cfg.get("MYSQL_SSL_CA"):
        # The server's certificate is checked against the CA file. Hosted services such as Aiven document
        # this as "verify CA", so the host name is not compared.
        options["ssl"] = {"ca": cfg["MYSQL_SSL_CA"], "check_hostname": False}
    return pymysql.connect(
        host=cfg["MYSQL_HOST"],
        port=cfg["MYSQL_PORT"],
        user=cfg["MYSQL_USER"],
        password=cfg["MYSQL_PASSWORD"],
        database=cfg["MYSQL_DB"] if database else None,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=10,
        **options,
    )


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config)
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query_all(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args or ())
        return list(cur.fetchall())


def query_one(sql, args=None):
    with get_db().cursor() as cur:
        cur.execute(sql, args or ())
        return cur.fetchone()


def execute(sql, args=None):
    """Run a write statement, commit, and return lastrowid. Rolls back on error."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args or ())
            last_id = cur.lastrowid
        conn.commit()
        return last_id
    except Exception:
        conn.rollback()
        raise


def execute_many(sql, rows):
    """Insert many rows in ONE transaction: either all are saved or none. Returns the row count."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
        return len(rows)
    except Exception:
        conn.rollback()
        raise


def run_in_transaction(work):
    """Run several statements as ONE transaction. `work(cursor)` does the writes and may return a value.

    Either everything inside `work` is saved or nothing is (used to create a user and the user's
    default categories together).
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            result = work(cur)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
