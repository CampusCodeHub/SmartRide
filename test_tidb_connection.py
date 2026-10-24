
import os

import pymysql
from dotenv import load_dotenv

load_dotenv()

required = [
    "TIDB_HOST",
    "TIDB_PORT",
    "TIDB_USER",
    "TIDB_PASSWORD",
    "TIDB_DATABASE",
]

missing = [key for key in required if not os.getenv(key)]

if missing:
    raise SystemExit(
        "Missing .env settings: " + ", ".join(missing)
    )

try:
    connection = pymysql.connect(
        host=os.environ["TIDB_HOST"],
        port=int(os.environ["TIDB_PORT"]),
        user=os.environ["TIDB_USER"],
        password=os.environ["TIDB_PASSWORD"],
        database=os.environ["TIDB_DATABASE"],
        connect_timeout=10,
        ssl={"ssl": True},
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE(), VERSION()")
            database, version = cursor.fetchone()

            print("Connection successful!")
            print("Database:", database)
            print("TiDB version:", version)
    finally:
        connection.close()

except Exception as error:
    print("Connection failed:", type(error).__name__)
    print("Check your connection settings and TiDB Cloud network access.")
    raise SystemExit(1)
