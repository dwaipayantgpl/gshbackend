# services/endpoints/router.py
from fastapi import APIRouter, Depends, HTTPException, status # Fixed imports
from auth.logic.deps import get_current_account_id, require_admin
from db.tables import Service # Use consistent path
from services.logic import service_logic
from services.structs.dtos import ServiceCreateIn, ServiceOut

router = APIRouter()

@router.post("/", response_model=ServiceOut, summary="Create a service (Admin Only)")
async def create_service(
    payload: ServiceCreateIn,
    _admin: str = Depends(require_admin), 
    account_id: str = Depends(get_current_account_id)
):
    # Logic simplified: Use the table imported at the top
    service = Service(**payload.model_dump())
    await service.save()
    return service

@router.patch("/{service_id}", response_model=ServiceOut, summary="Admin Only: Update a service")
async def update_service(
    service_id: str,
    payload: ServiceCreateIn, # Or use ServiceUpdateIn for optional fields
    _admin: str = Depends(require_admin)
):
    return await service_logic.update_existing_service(
        service_id, 
        payload.model_dump(exclude_unset=True)
    )

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Admin Only: Delete a service")
async def delete_service(
    service_id: str,
    _admin: str = Depends(require_admin)
):
    await service_logic.delete_existing_service(service_id)
    return None # Returns 204 No Content

# services/endpoints/router.py (Add this to your existing file)
from typing import List

@router.get("/", response_model=List[ServiceOut], summary="List all services")
async def list_services():
    """
    Returns a list of all available services. 
    Accessible by anyone to browse the marketplace categories.
    """
    from db.tables import Service
    return await Service.objects().order_by(Service.name)