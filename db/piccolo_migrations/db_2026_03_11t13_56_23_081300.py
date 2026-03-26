import decimal

from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Numeric

ID = "2026-03-11T13:56:23:081300"
VERSION = "1.32.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="db", description=DESCRIPTION)

    manager.alter_column(
        table_class_name="ServiceBooking",
        tablename="service_booking",
        column_name="total_price",
        db_column_name="total_price",
        params={"default": decimal.Decimal("0.00")},
        old_params={"default": decimal.Decimal("0")},
        column_class=Numeric,
        old_column_class=Numeric,
        schema=None,
    )

    return manager
