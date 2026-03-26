from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Integer
from piccolo.columns.indexes import IndexMethod

ID = "2026-02-24T14:37:15:639001"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.add_column(
        table_class_name="PreferenceRequirements",
        tablename="preference_requirements",
        column_name="max_salary",
        db_column_name="max_salary",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 20000,
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
        table_class_name="PreferenceRequirements",
        tablename="preference_requirements",
        column_name="min_salary",
        db_column_name="min_salary",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 15000,
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
