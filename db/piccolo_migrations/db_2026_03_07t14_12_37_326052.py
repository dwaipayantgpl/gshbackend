from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.choices import Choice
from piccolo.columns.column_types import Varchar

ID = "2026-03-07T14:12:37:326052"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.alter_column(
        table_class_name="BookingRequest",
        tablename="booking_request",
        column_name="status",
        db_column_name="status",
        params={
            "choices": [
                Choice(value="pending", display_name="pending"),
                Choice(value="accepted", display_name="accepted"),
                Choice(value="rejected", display_name="rejected"),
                Choice(value="cancelled", display_name="cancelled"),
            ]
        },
        old_params={"choices": None},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
