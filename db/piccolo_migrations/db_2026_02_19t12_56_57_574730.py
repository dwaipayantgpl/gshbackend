from click import Choice
from piccolo.columns.choices import Choice
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Text
from piccolo.columns.column_types import Timestamptz
from piccolo.columns.column_types import Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.indexes import IndexMethod


ID = "2026-02-19T12:56:57:574730"
VERSION = "1.30.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="db", description=DESCRIPTION
    )

    manager.add_table(
        class_name="BlacklistedUser",
        tablename="blacklisted_user",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="BlacklistedUser",
        tablename="blacklisted_user",
        column_name="phone",
        db_column_name="phone",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="BlacklistedUser",
        tablename="blacklisted_user",
        column_name="reason",
        db_column_name="reason",
        column_class_name="Text",
        column_class=Text,
        params={
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
        table_class_name="BlacklistedUser",
        tablename="blacklisted_user",
        column_name="banned_at",
        db_column_name="banned_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
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

    manager.alter_column(
        table_class_name="Registration",
        tablename="registration",
        column_name="role",
        db_column_name="role",
        params={
            "choices": [
                Choice(value="seeker", display_name="seeker"),
                Choice(value="helper", display_name="helper"),
                Choice(value="both", display_name="both"),
                Choice(value="admin", display_name="admin"),
            ]
        },
        old_params={
            "choices": [
                Choice(value="seeker", display_name="seeker"),
                Choice(value="helper", display_name="helper"),
                Choice(value="both", display_name="both"),
            ]
        },
        column_class=Varchar,
        old_column_class=Varchar,
        schema=None,
    )

    return manager
