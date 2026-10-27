import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app


def get_db():
    if "db" not in g:
        cfg = current_app.config
        g.db = pymysql.connect(
            host=cfg["MYSQL_HOST"],
            port=cfg["MYSQL_PORT"],
            user=cfg["MYSQL_USER"],
            password=cfg["MYSQL_PASSWORD"],
            database=cfg["MYSQL_DB"],
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
        )
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
