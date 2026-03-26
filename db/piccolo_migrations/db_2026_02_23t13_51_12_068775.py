from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, ForeignKey
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class Registration(Table, tablename="registration", schema=None):
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


class Service(Table, tablename="service", schema=None):
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


ID = "2026-02-23T13:51:12:068775"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.add_table(
        class_name="SeekerPreference",
        tablename="seeker_preference",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="SeekerPreference",
        tablename="seeker_preference",
        column_name="registration",
        db_column_name="registration",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Registration,
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
        table_class_name="SeekerPreference",
        tablename="seeker_preference",
        column_name="service",
        db_column_name="service",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": Service,
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

    return manager
