from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Varchar
from piccolo.columns.indexes import IndexMethod
from piccolo.columns.choices import Choice

ID = "2026-02-23T15:14:05:896078"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="db", description=DESCRIPTION
    )

    manager.add_column(
        table_class_name="SeekerPreference",
        tablename="seeker_preference",
        column_name="area",
        db_column_name="area",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 100,
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
        table_class_name="SeekerPreference",
        tablename="seeker_preference",
        column_name="city",
        db_column_name="city",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 100,
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
        table_class_name="SeekerPreference",
        tablename="seeker_preference",
        column_name="job_type",
        db_column_name="job_type",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": [
                Choice(value="part_time", display_name="part_time"),
                Choice(value="full_time", display_name="full_time"),
                Choice(value="one_time", display_name="one_time"),
                Choice(value="subscription", display_name="subscription"),
            ],
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    return manager
