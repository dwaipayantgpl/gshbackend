from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Varchar


ID = "2026-03-11T11:24:39:050045"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="db", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="ServiceBooking",
        tablename="service_booking",
        column_name="duration",
        db_column_name="duration",
        params={"null": True},
        old_params={"null": False},
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
