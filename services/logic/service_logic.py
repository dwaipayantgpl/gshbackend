# services/logic/service_logic.py
from datetime import date
from fastapi import HTTPException, status
from db.tables import HelperInstitutional, HelperPersonal, HelperPreference, HelperService, JobRequestService, Registration, SeekerInstitutional, SeekerPersonal, Service
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

# async def get_admin_user_report():
#     # 1. Calculate counts
#     helpers_count = await Registration.count().where(Registration.role == 'helper')
#     seekers_count = await Registration.count().where(Registration.role == 'seeker')
    

#     # 2. Fetch full table with joins
#     # We select fields from Registration and follow the 'account' foreign key to get phone/name
#     raw_data = await Registration.select(
#         Registration.account.id,
#         Registration.account.phone,
#         Registration.role
#     ).run()

#     # Format the data for the DTO
#     user_list = [
#         {
#             "account_id": str(item["account.id"]),
#             "phone": item["account.phone"],
#             "role": item["role"]
#         } for item in raw_data
#     ]

#     return {
#         "total_helpers": helpers_count,
#         "total_seekers": seekers_count,
#         "users": user_list
#     }


async def get_admin_user_report():
    # 1. Calculate counts directly
    helpers_count = await Registration.count().where(Registration.role.is_in(['helper', 'both'])).run()
    seekers_count = await Registration.count().where(Registration.role.is_in(['seeker', 'both'])).run()

    # 2. Fetch Registration joined with Account for core data
    raw_data = await Registration.select(
        Registration.account.id,
        Registration.account.phone,
        Registration.account.is_active,
        Registration.role,
        Registration.capacity,
        Registration.id
    ).run()

    user_list = []

    for item in raw_data:
        reg_id = item["id"]
        role = item["role"]
        capacity = item["capacity"]
        
        # Default profile values
        name = "N/A"
        city = "N/A"
        area = "N/A"

        # 3. Dynamic Profile Lookup
        if role == 'helper':
            if capacity == 'personal':
                profile = await HelperPersonal.objects().where(HelperPersonal.registration == reg_id).first()
            else:
                profile = await HelperInstitutional.objects().where(HelperInstitutional.registration == reg_id).first()
        elif role == 'seeker':
            if capacity == 'personal':
                profile = await SeekerPersonal.objects().where(SeekerPersonal.registration == reg_id).first()
            else:
                profile = await SeekerInstitutional.objects().where(SeekerInstitutional.registration == reg_id).first()
        else:
            profile = None

        if profile:
            name = getattr(profile, 'name', 'N/A')
            city = getattr(profile, 'city', 'N/A')
            area = getattr(profile, 'area', 'N/A')

        user_list.append({
            "account_id": str(item["account.id"]),
            "phone": item["account.phone"],
            "role": role,
            "capacity": capacity,
            "is_active": item["account.is_active"],
            "name": name,
            "city": city,
            "area": area
        })

    return {
        "total_helpers": helpers_count,
        "total_seekers": seekers_count,
        "users": user_list
    }

async def get_growth_by_date(start: date, end: date):
    # Filter Registration table by the date the linked Account was created
    # We use >= for start and <= for end
    
    helpers = await Registration.count().where(
        (Registration.role == 'helper') &
        (Registration.account.created_at >= start) &
        (Registration.account.created_at <= end)
    )

    seekers = await Registration.count().where(
        (Registration.role == 'seeker') &
        (Registration.account.created_at >= start) &
        (Registration.account.created_at <= end)
    )

    return {
        "start_date": start,
        "end_date": end,
        "new_helpers": helpers,
        "new_seekers": seekers,
        "total_new_joins": helpers + seekers
    }
