from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, ForeignKey, Serial, Varchar
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class HelperSpecialPreferences(
    Table, tablename="helper_special_preferences", schema=None
):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class PreferenceLocation(Table, tablename="preference_location", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class PreferenceRequirements(Table, tablename="preference_requirements", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
        secret=False,
    )


class PreferenceWork(Table, tablename="preference_work", schema=None):
    id = Serial(
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name="id",
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


ID = "2026-02-26T10:18:55:636364"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.add_table(
        class_name="HelperSpecialPreferences",
        tablename="helper_special_preferences",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="HelperSpecialPreferences",
        tablename="helper_special_preferences",
        column_name="skills",
        db_column_name="skills",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 500,
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

    manager.add_column(
        table_class_name="HelperSpecialPreferences",
        tablename="helper_special_preferences",
        column_name="special_preferences",
        db_column_name="special_preferences",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 1000,
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

    manager.drop_column(
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="area",
        db_column_name="area",
        schema=None,
    )

    manager.drop_column(
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="city",
        db_column_name="city",
        schema=None,
    )

    manager.drop_column(
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="job_type",
        db_column_name="job_type",
        schema=None,
    )

    manager.add_column(
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="helperpreference_details",
        db_column_name="helperpreference_details",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": HelperSpecialPreferences,
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
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="location",
        db_column_name="location",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PreferenceLocation,
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
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="requirements",
        db_column_name="requirements",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PreferenceRequirements,
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
        table_class_name="HelperPreference",
        tablename="helper_preference",
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

    manager.add_column(
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="work",
        db_column_name="work",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": PreferenceWork,
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

    manager.alter_column(
        table_class_name="HelperPreference",
        tablename="helper_preference",
        column_name="registration",
        db_column_name="registration",
        params={"unique": False},
        old_params={"unique": True},
        column_class=ForeignKey,
        old_column_class=ForeignKey,
        schema=None,
    )

    return manager
