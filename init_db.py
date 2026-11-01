"""Create the tables (and optionally the demo data) without needing the mysql command line.

    python init_db.py           create the database tables from schema.sql
    python init_db.py --demo    ...and also load sample_data.sql (demo@example.com / Demo@1234)

It uses the same MYSQL_* settings as the app (from .env or the environment), so the same command
works on your laptop and on a hosted MySQL service.
"""
import re
import sys
from pathlib import Path

import pymysql

import db
from config import Config

HERE = Path(__file__).resolve().parent


def read_statements(filename):
    """Split an .sql file into statements (comments removed)."""
    text = (HERE / filename).read_text(encoding="utf-8")
    text = re.sub(r"--[^\n]*", "", text)
    return [part.strip() for part in text.split(";") if part.strip()]


def run(conn, filename):
    with conn.cursor() as cur:
        for statement in read_statements(filename):
            if statement.upper().startswith(("CREATE DATABASE", "USE ")):
                continue  # the database is chosen by MYSQL_DB, not by the file
            cur.execute(statement)
    conn.commit()


def main():
    cfg = {name: getattr(Config, name) for name in dir(Config) if name.isupper()}
    name = cfg["MYSQL_DB"]
    if not re.fullmatch(r"\w+", name):
        sys.exit("MYSQL_DB may only contain letters, digits and underscores.")
    try:
        try:  # create the database when we are allowed to (a hosted service usually made it already)
            with db.connect(cfg, database=False) as admin, admin.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4")
        except pymysql.err.MySQLError as exc:
            print(f"Note: could not create the database ({exc.args[-1]}); assuming it already exists.")
        conn = db.connect(cfg)
        run(conn, "schema.sql")
        print(f"Tables are ready in database '{name}'.")
        if "--demo" in sys.argv:
            try:
                run(conn, "sample_data.sql")
                print("Demo data loaded. Log in with demo@example.com / Demo@1234")
            except pymysql.err.IntegrityError:
                conn.rollback()
                print("Demo data was already loaded earlier, nothing changed.")
        conn.close()
    except pymysql.err.MySQLError as exc:
        sys.exit(f"Could not use MySQL: {exc.args[-1]}\nCheck that MySQL is running and the MYSQL_* settings are right.")


if __name__ == "__main__":
    main()
