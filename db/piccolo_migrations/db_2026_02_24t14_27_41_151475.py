from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import (
    UUID,
    Boolean,
    ForeignKey,
    Integer,
    Serial,
    Varchar,
)
from piccolo.columns.defaults.uuid import UUID4
from piccolo.columns.indexes import IndexMethod
from piccolo.table import Table


class HelperDetails(Table, tablename="helper_details", schema=None):
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


ID = "2026-02-24T14:27:41:151475"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.add_table(
        class_name="PreferenceLocation",
        tablename="preference_location",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="PreferenceWork",
        tablename="preference_work",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="HelperDetails",
        tablename="helper_details",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="PreferenceRequirements",
        tablename="preference_requirements",
        schema=None,
        columns=None,
    )

    manager.drop_table(
        class_name="SeekerPreference", tablename="seeker_preference", schema=None
    )

    manager.add_column(
        table_class_name="PreferenceLocation",
        tablename="preference_location",
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
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="PreferenceLocation",
        tablename="preference_location",
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
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
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
        table_class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
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
        table_class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
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
        table_class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
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

    manager.add_column(
        table_class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
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
        table_class_name="SeekerPreferenceNew",
        tablename="seeker_preference_new",
        column_name="helper_details",
        db_column_name="helper_details",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": HelperDetails,
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
        table_class_name="PreferenceWork",
        tablename="preference_work",
        column_name="job_type",
        db_column_name="job_type",
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
        table_class_name="PreferenceWork",
        tablename="preference_work",
        column_name="work_mode",
        db_column_name="work_mode",
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
        table_class_name="PreferenceWork",
        tablename="preference_work",
        column_name="working_days",
        db_column_name="working_days",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 6,
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
        table_class_name="PreferenceWork",
        tablename="preference_work",
        column_name="weekly_off",
        db_column_name="weekly_off",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
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
        table_class_name="PreferenceWork",
        tablename="preference_work",
        column_name="accommodation",
        db_column_name="accommodation",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
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
        table_class_name="HelperDetails",
        tablename="helper_details",
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
        column_name="gender",
        db_column_name="gender",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 20,
            "default": "any",
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
        table_class_name="PreferenceRequirements",
        tablename="preference_requirements",
        column_name="min_age",
        db_column_name="min_age",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
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
        column_name="max_age",
        db_column_name="max_age",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
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
        column_name="experience",
        db_column_name="experience",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "0",
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
