# services/logic/service_logic.py
from fastapi import HTTPException, status
from db.tables import Service
import uuid

async def update_existing_service(service_id: str, data: dict):
    service = await Service.objects().where(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Update only the fields provided in the request
    for key, value in data.items():
        if value is not None:
            setattr(service, key, value)
    
    await service.save()
    return service

async def delete_existing_service(service_id: str):
    service = await Service.objects().where(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    await service.remove()
    return {"detail": "Service deleted successfully"}