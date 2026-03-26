# db/piccolo_conf.py
import os

from dotenv import load_dotenv
from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

load_dotenv()

DB = PostgresEngine(
    config={
        "database": os.getenv("DBNAME"),
        "user": os.getenv("DBUSER"),
        "password": os.getenv("DBPASS"),
        "host": os.getenv("DBHOST"),
        "port": int(os.getenv("DBPORT", "5432")),
    }
)

# Register your app(s)
APP_REGISTRY = AppRegistry(apps=["db.piccolo_app"])
