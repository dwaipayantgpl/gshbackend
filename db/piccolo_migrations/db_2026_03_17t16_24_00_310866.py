from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text

ID = "2026-03-17T16:24:00:310866"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.alter_column(
        table_class_name="ChatMessage",
        tablename="chat_message",
        column_name="message",
        db_column_name="message",
        params={"nullable": True},
        old_params={"nullable": None},
        column_class=Text,
        old_column_class=Text,
        schema=None,
    )

    return manager
