from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, ForeignKey, Timestamptz
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class ServiceBooking(Table, tablename="service_booking", schema=None):
    id = UUID(
        default=UUID4(),
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


ID = "2026-03-12T15:36:08:329197"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.drop_column(
        table_class_name="ChatMessage",
        tablename="chat_message",
        column_name="service",
        db_column_name="service",
        schema=None,
    )

    manager.drop_column(
        table_class_name="ChatMessage",
        tablename="chat_message",
        column_name="timestamp",
        db_column_name="timestamp",
        schema=None,
    )

    manager.add_column(
        table_class_name="ChatMessage",
        tablename="chat_message",
        column_name="booking",
        db_column_name="booking",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": ServiceBooking,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="ChatMessage",
        tablename="chat_message",
        column_name="created_at",
        db_column_name="created_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "auto_now": True,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
