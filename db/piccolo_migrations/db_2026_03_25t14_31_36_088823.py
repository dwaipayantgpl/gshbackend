from piccolo.columns.choices import Choice
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Varchar
from piccolo.columns.indexes import IndexMethod


ID = "2026-03-25T14:31:36:088823"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="db", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="Notifiactions",
        tablename="notifiactions",
        column_name="category",
        db_column_name="category",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "booking_request",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": [
                Choice(value="chat", display_name="chat"),
                Choice(value="booking_request", display_name="booking_request"),
                Choice(value="booking_accepted", display_name="booking_accepted"),
                Choice(value="booking_rejected", display_name="booking_rejected"),
                Choice(value="rating_reminder", display_name="rating_reminder"),
                Choice(value="admin_broadcast", display_name="admin_broadcast"),
            ],
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
