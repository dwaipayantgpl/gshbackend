import uuid

from fastapi import APIRouter, Body, Depends, HTTPException

from auth.logic.deps import get_current_registration, get_current_user_role
from db.tables import HelperService, Registration, SeekerPreference
from seeker.structs.dtos import SeekerPrefCreate
from piccolo.query.mixins import OnConflict
router = APIRouter()

@router.post("/addpreferences")
async def add_seeker_preference(
    data: SeekerPrefCreate, 
    user: Registration = Depends(get_current_registration)
):
    reg_id = user.id
    
    if not reg_id:
        raise HTTPException(status_code=400, detail="Registration ID not found in token")

    # 1. Try to find an existing preference for this registration and service
    existing = await SeekerPreference.objects().get(
        (SeekerPreference.registration == reg_id) & 
        (SeekerPreference.service == data.service_id)
    ).run()

    if existing:
        # 2. If it exists, update the fields
        existing.city = data.city
        existing.area = data.area
        existing.job_type = data.job_type
        await existing.save().run()
        message = "Preference updated successfully"
    else:
        # 3. If it doesn't exist, create a new record
        new_pref = SeekerPreference(
            registration=reg_id,
            service=data.service_id,
            city=data.city,
            area=data.area,
            job_type=data.job_type
        )
        await new_pref.save().run()
        message = "Preference added successfully"
    
    return {"message": message}


@router.get("/my-preferences", summary="Seeker: View my selected services")
async def get_my_preferences(user: Registration = Depends(get_current_registration)):
    preferences = await SeekerPreference.select(
        SeekerPreference.city,
        SeekerPreference.area,
        SeekerPreference.job_type,
        SeekerPreference.service.id.as_alias("service_id"),
        SeekerPreference.service.name.as_alias("service_name")
    ).where(
        SeekerPreference.registration == user.id
    ).run()

    return preferences


@router.delete("/preferences/{service_id}")
async def delete_specific_preference(
    service_id: uuid.UUID, 
    user = Depends(get_current_registration)
):
    reg_id = user.id

    query = SeekerPreference.delete().where(
        (SeekerPreference.registration == reg_id) & 
        (SeekerPreference.service == service_id)
    )
    result = await query.run()
    return {"message": "Preference removed successfully"}


# @router.get("/seeker/matched-helpers")
# async def get_helpers_by_preferences(user=Depends(get_current_user_role)):
#     # 1. Get Seeker's preferred service IDs
#     pref_ids = await SeekerPreference.select(SeekerPreference.service).where(
#         SeekerPreference.registration == user.registration_id
#     ).run()
    
#     ids = [p['service'] for p in pref_ids]

#     # 2. Find Helpers who provide ANY of those services
#     # We join HelperService to Registration to get Helper names/details
#     matched_helpers = await HelperService.select(
#         HelperService.helper.id.as_alias("registration_id"),
#         HelperService.service.name.as_alias("service_name"),
#         # Add profile joins here to get Name/Phone as we did before
#     ).where(
#         HelperService.service.isin(ids)
#     ).run()

#     return matched_helpers