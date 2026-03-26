# db/piccolo_app.py
import os

from piccolo.conf.apps import AppConfig, table_finder

CURRENT_DIRECTORY = os.path.dirname(__file__)

APP_CONFIG = AppConfig(
    app_name="db",
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "piccolo_migrations"),
    table_classes=table_finder(modules=["db.tables"]),
)
