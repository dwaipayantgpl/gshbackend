from piccolo.apps.migrations.auto.migration_manager import MigrationManager

ID = "2026-02-24T14:36:50:014710"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.drop_column(
        table_class_name="PreferenceRequirements",
        tablename="preference_requirements",
        column_name="max_salary",
        db_column_name="max_salary",
        schema=None,
    )

    manager.drop_column(
        table_class_name="PreferenceRequirements",
        tablename="preference_requirements",
        column_name="min_salary",
        db_column_name="min_salary",
        schema=None,
    )

    return manager
