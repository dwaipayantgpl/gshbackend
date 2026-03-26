from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, ForeignKey, Text, Varchar
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class Account(Table, tablename="account", schema=None):
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


ID = "2026-03-13T12:02:15:694811"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.drop_column(
        table_class_name="Complaint",
        tablename="complaint",
        column_name="account",
        db_column_name="account",
        schema=None,
    )

    manager.drop_column(
        table_class_name="Complaint",
        tablename="complaint",
        column_name="admin_note",
        db_column_name="admin_note",
        schema=None,
    )

    manager.drop_column(
        table_class_name="Complaint",
        tablename="complaint",
        column_name="subject",
        db_column_name="subject",
        schema=None,
    )

    manager.add_column(
        table_class_name="Complaint",
        tablename="complaint",
        column_name="account_id",
        db_column_name="account_id",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Account,
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
        table_class_name="Complaint",
        tablename="complaint",
        column_name="booking_id",
        db_column_name="booking_id",
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
        table_class_name="Complaint",
        tablename="complaint",
        column_name="category",
        db_column_name="category",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "",
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

    manager.add_column(
        table_class_name="Complaint",
        tablename="complaint",
        column_name="proof_image",
        db_column_name="proof_image",
        column_class_name="Text",
        column_class=Text,
        params={
            "default": "",
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

    return manager
