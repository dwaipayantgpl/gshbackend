from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import JSONB

ID = "2026-03-25T15:19:02:937575"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.alter_column(
        table_class_name="Notifiactions",
        tablename="notifiactions",
        column_name="metadata",
        db_column_name="metadata",
        params={"null": True},
        old_params={"null": False},
        column_class=JSONB,
        old_column_class=JSONB,
        schema=None,
    )

    return manager
