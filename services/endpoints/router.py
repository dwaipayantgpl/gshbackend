# services/endpoints/router.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status  # Fixed imports

from auth.logic.deps import (
    get_current_account_id,
    get_current_registration,
    require_admin,
)
from db.tables import Registration, Service  # Use consistent path
from notifications.logic.service import NotificationService
from services.logic import service_logic
from services.structs.dtos import (
    DateRangeIn,
    ServiceCreateIn,
    ServiceOut,
    ServiceUpdateIn,
)

router = APIRouter()


@router.post(
    "/creat", response_model=ServiceOut, summary="Create a service (Admin Only)"
)
async def create_service(
    payload: ServiceCreateIn,
    _admin: str = Depends(require_admin),
    account_id: str = Depends(get_current_account_id),
):
    existing_service = (
        await Service.objects().where(Service.name == payload.name).first()
    )

    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service with name '{payload.name}' already exists.",
        )
    # Logic simplified: Use the table imported at the top
    service = Service(**payload.model_dump())
    await service.save()

    try:
        await NotificationService.broadcast_new_service(
            service_name=service.name,
            description=service.description or "",
            service_id=str(service.id),  # Crucial: Pass the ID as a string
        )
        print(f"✅ Global broadcast sent for {service.name}")
    except Exception as e:
        # Log error but don't fail the HTTP response
        print(f"❌ Broadcast Error: {e}")

    return service


@router.patch("/patch/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: uuid.UUID,  # Validates 36-char format
    payload: ServiceUpdateIn,  # Allows partial updates
    _admin: str = Depends(require_admin),
):
    return await service_logic.update_existing_service(
        str(service_id),
        payload.model_dump(exclude_unset=True),  # ignores missing fields
    )


@router.delete(
    "/delete/{service_id}",
    status_code=status.HTTP_200_OK,
    summary="Admin Only: Delete a service",
)
async def delete_service(service_id: str, _admin: str = Depends(require_admin)):
    service_name = await service_logic.delete_existing_service(service_id)

    # Safety check: if the service didn't exist, service_name might be None
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID {service_id} not found",
        )

    return {"message": f"Service '{service_name}' successfully deleted"}


# services/endpoints/router.py (Add this to your existing file)
from typing import List


@router.get("/getall", response_model=List[ServiceOut], summary="List all services")
async def list_services():
    """
    Returns a list of all available services.
    Accessible by anyone to browse the marketplace categories.
    """
    from db.tables import Service

    return await Service.objects().order_by(Service.name)


# user report
# C:\CompanyProject\gshbe\admin\endpoints\router.py


@router.get("/admin/user-report", summary="Get all Helper/Seeker details - PUBLIC")
async def admin_user_report():
    """
    PUBLIC ACCESS. Returns total counts and a detailed list
    of every helper and seeker. No token required.
    """
    return await service_logic.get_admin_user_report()


# check total head count between two specific dates
@router.post("/admin/analytics/range-report", summary="Admin: Growth between two dates")
async def get_range_report(payload: DateRangeIn, _admin: str = Depends(require_admin)):
    return await service_logic.get_growth_by_date(payload.start_date, payload.end_date)


@router.get("/service-participants/{service_id}")
async def get_service_participants(
    service_id: str, current_user: Registration = Depends(get_current_registration)
):
    """
    Returns all Helpers and Seekers registered for a specific service ID,
    including their names, contact info, and profile pictures.
    """
    return await service_logic.get_service_participants_logic(service_id)
