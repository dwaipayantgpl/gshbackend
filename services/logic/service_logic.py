# services/logic/service_logic.py
from fastapi import HTTPException, status
from db.tables import Registration, Service
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
    
    service_name=service.name
    await service.remove()
    return service_name

async def get_admin_user_report():
    # 1. Calculate counts
    helpers_count = await Registration.count().where(Registration.role == 'helper')
    seekers_count = await Registration.count().where(Registration.role == 'seeker')
    

    # 2. Fetch full table with joins
    # We select fields from Registration and follow the 'account' foreign key to get phone/name
    raw_data = await Registration.select(
        Registration.account.id,
        Registration.account.phone,
        Registration.role
    ).run()

    # Format the data for the DTO
    user_list = [
        {
            "account_id": str(item["account.id"]),
            "phone": item["account.phone"],
            "role": item["role"]
        } for item in raw_data
    ]

    return {
        "total_helpers": helpers_count,
        "total_seekers": seekers_count,
        "users": user_list
    }