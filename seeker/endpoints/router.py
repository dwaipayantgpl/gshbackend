from typing import Any, Dict
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException,status

from auth.logic.deps import get_current_registration, get_current_user_role
from db.tables import HelperDetails, HelperInstitutional, HelperPersonal, HelperPreference, HelperService, PreferenceLocation, PreferenceRequirements, PreferenceWork, Registration, SeekerPreference, SeekerPreferenceNew
from seeker.structs.dtos import SeekerPrefCreate
from piccolo.query.mixins import OnConflict
from seeker.logic import service

router = APIRouter()


from db.tables import Service # Make sure to import your Service table


@router.post("/addpreferences")
async def add_seeker_preferences(
    data: Dict[str, Any], 
    user: Registration = Depends(get_current_registration)
):
    existing = await SeekerPreferenceNew.objects().where(SeekerPreferenceNew.registration == user.id).first().run()
    if existing:
        raise HTTPException(status_code=400, detail="Preferences already exist. Use PATCH to update.")

    loc_data = data.get("location", {})
    work_data = data.get("work_schedule", {})
    salary_data = data.get("salary_range", {})
    age_data = data.get("age_range", {}) # <-- Add this

    loc_row = await PreferenceLocation.objects().create(
        city=loc_data.get("city"), 
        area=loc_data.get("area")
    )
    work_row = await PreferenceWork.objects().create(
        job_type=data.get("job_type"),
        work_mode=data.get("work_mode"),
        working_days=work_data.get("working_days_per_week", 6),
        weekly_off=work_data.get("weekly_off_day", "Sunday"),
        accommodation=work_data.get("accommodation_provided", False)
    )
    reqs_row = await PreferenceRequirements.objects().create(
        min_salary=salary_data.get("min", 0), 
        max_salary=salary_data.get("max", 0),
        min_age=age_data.get("min"),         # <-- Fix: Added mapping
        max_age=age_data.get("max"),         # <-- Fix: Added mapping
        gender=data.get("gender", "any"),
        experience=data.get("experience", "0")
    )
    details_row = await HelperDetails.objects().create(
        skills=str(data.get("skills", ""))
    )

    for s_id in data.get("service_ids", []):
        await SeekerPreferenceNew.objects().create(
            registration=user.id, service=s_id,
            location=loc_row.id, work=work_row.id,
            requirements=reqs_row.id, helper_details=details_row.id
        )

    return {"status": "success", "message": "Preferences initialized."}


@router.patch("/updatepreferences")
async def update_seeker_preferences(
    data: Dict[str, Any], 
    user: Registration = Depends(get_current_registration)
):
    current_prefs = await SeekerPreferenceNew.objects().where(SeekerPreferenceNew.registration == user.id).run()
    if not current_prefs:
        raise HTTPException(status_code=404, detail="No preferences found.")

    # Shared Master IDs
    m_loc = current_prefs[0].location
    m_work = current_prefs[0].work
    m_req = current_prefs[0].requirements
    m_det = current_prefs[0].helper_details

    # 1. Update Location
    if "location" in data:
        await PreferenceLocation.update({
            PreferenceLocation.city: data["location"].get("city"),
            PreferenceLocation.area: data["location"].get("area")
        }).where(PreferenceLocation.id == m_loc).run()

    # 2. Update Work
    if "work_schedule" in data or "job_type" in data or "work_mode" in data:
        work_upd = data.get("work_schedule", {})
        await PreferenceWork.update({
            PreferenceWork.job_type: data.get("job_type"),
            PreferenceWork.work_mode: data.get("work_mode"),
            PreferenceWork.working_days: work_upd.get("working_days_per_week"),
            PreferenceWork.weekly_off: work_upd.get("weekly_off_day"),
            PreferenceWork.accommodation: work_upd.get("accommodation_provided")
        }).where(PreferenceWork.id == m_work).run()

    # 3. Update Requirements (Salary, Age, Experience, Gender)
    sal_data = data.get("salary_range", {})
    age_data = data.get("age_range", {})
    await PreferenceRequirements.update({
        PreferenceRequirements.min_salary: sal_data.get("min"),
        PreferenceRequirements.max_salary: sal_data.get("max"),
        PreferenceRequirements.min_age: age_data.get("min"),
        PreferenceRequirements.max_age: age_data.get("max"),
        PreferenceRequirements.gender: data.get("gender"),
        PreferenceRequirements.experience: data.get("experience")
    }).where(PreferenceRequirements.id == m_req).run()

    # 4. Update Skills
    if "skills" in data:
        await HelperDetails.update({HelperDetails.skills: data.get("skills")}).where(HelperDetails.id == m_det).run()

   # --- 5. Service Management (REVISED) ---
    # --- 5. Service Management (Add & Remove) ---
    existing_sids = {str(p.service) for p in current_prefs}
    
    # FIX 1: Use 'or []' to prevent NoneType errors if keys are missing from 'data'
    new_sids = data.get("service_ids") or []
    remove_sids = data.get("remove_service_ids") or []
    
    added_names = []
    # FIX 2: Track actual removals to provide an accurate response count
    actual_removed_count = 0

    # Handle removals first
    if remove_sids:
        # We only want to delete what actually exists in the user's current prefs
        valid_removals = [sid for sid in remove_sids if str(sid) in existing_sids]
        
        if valid_removals:
            actual_removed_count = len(valid_removals)
            await SeekerPreferenceNew.delete().where(
                (SeekerPreferenceNew.registration == user.id) & 
                (SeekerPreferenceNew.service.is_in(valid_removals))
            ).run()

    # Handle additions
    for s_id in new_sids:
        # Check against existing IDs, excluding those we just marked for removal
        if str(s_id) not in existing_sids or s_id in remove_sids:
             # Logic to prevent double-adding if it was already there
             is_already_present = await SeekerPreferenceNew.objects().where(
                 (SeekerPreferenceNew.registration == user.id) & 
                 (SeekerPreferenceNew.service == s_id)
             ).first().run()
             
             if not is_already_present:
                await SeekerPreferenceNew.objects().create(
                    registration=user.id, service=s_id,
                    location=m_loc, work=m_work,
                    requirements=m_req, helper_details=m_det
                )
                svc = await Service.objects().get(Service.id == s_id).run()
                added_names.append(svc.name if svc else str(s_id))

    # --- 6. Final Integrity Check ---
    final_prefs_count = await SeekerPreferenceNew.count().where(
        SeekerPreferenceNew.registration == user.id
    ).run()

    if final_prefs_count == 0:
        await PreferenceLocation.delete().where(PreferenceLocation.id == m_loc).run()
        await PreferenceWork.delete().where(PreferenceWork.id == m_work).run()
        await PreferenceRequirements.delete().where(PreferenceRequirements.id == m_req).run()
        await HelperDetails.delete().where(HelperDetails.id == m_det).run()
        
        return {
            "status": "success", 
            "message": "All services removed. Profile data cleaned up."
        }

    return {
        "status": "success", 
        "message": "Preferences updated globally.", 
        "newly_added": added_names,
        "removed_count": actual_removed_count  # FIX 3: Return the calculated count
    }



@router.get("/my-preferences")
async def get_my_preferences(user: Registration = Depends(get_current_registration)):
    # 1. Fetch preferences with prefetched details
    preferences = await SeekerPreferenceNew.objects().where(
        SeekerPreferenceNew.registration == user.id
    ).prefetch(
        SeekerPreferenceNew.service,
        SeekerPreferenceNew.location,
        SeekerPreferenceNew.work,
        SeekerPreferenceNew.requirements,
        SeekerPreferenceNew.helper_details
    ).run() 

    if not preferences:
        return {
            "services": [],
            "details": None
        }

    # 2. Extract the Services into a simple array
    services_list = []
    for p in preferences:
        if p.service:
            services_list.append({
                "id": p.service.id,
                "name": p.service.name,
                "description": p.service.description
            })

    # 3. Grab common details from the first record
    # (Since they are all linked to the same master IDs)
    first = preferences[0]
    
    return {
        "services": services_list,
        "details": {
            "location": first.location.to_dict() if first.location else None,
            "work": first.work.to_dict() if first.work else None,
            "requirements": first.requirements.to_dict() if first.requirements else None,
            "helper_details": first.helper_details.to_dict() if first.helper_details else None,
        }
    }

@router.delete("/preferences/{service_id}")
async def delete_seeker_preference(
    service_id: uuid.UUID, 
    user: Registration = Depends(get_current_registration)
):
    # 1. Find the preference to be deleted
    pref_to_delete = await SeekerPreferenceNew.objects().where(
        (SeekerPreferenceNew.registration == user.id) & 
        (SeekerPreferenceNew.service == service_id)
    ).first().run()

    if not pref_to_delete:
        raise HTTPException(status_code=404, detail="Service preference not found.")

    # 2. Check how many total preferences the user has
    all_user_prefs = await SeekerPreferenceNew.objects().where(
        SeekerPreferenceNew.registration == user.id
    ).run()

    # 3. Store the Master IDs before deleting the link
    m_loc = pref_to_delete.location
    m_work = pref_to_delete.work
    m_req = pref_to_delete.requirements
    m_det = pref_to_delete.helper_details

    # 4. Delete the link to this specific service
    await SeekerPreferenceNew.delete().where(
        SeekerPreferenceNew.id == pref_to_delete.id
    ).run()

    # 5. Cleanup Sub-tables ONLY if this was the last service
    if len(all_user_prefs) == 1:
        await PreferenceLocation.delete().where(PreferenceLocation.id == m_loc).run()
        await PreferenceWork.delete().where(PreferenceWork.id == m_work).run()
        await PreferenceRequirements.delete().where(PreferenceRequirements.id == m_req).run()
        await HelperDetails.delete().where(HelperDetails.id == m_det).run()
        
        return {"message": "Deleted the last service and cleaned up all associated details."}

    return {"message": f"Service removed. {len(all_user_prefs) - 1} services remaining."}


@router.get("/helper-feed", summary="Seeker: See matching helpers based on preferences")
async def get_helper_feed(user: Registration = Depends(get_current_registration)):
    # 1. Get all preferences for this seeker
    seeker_prefs = await SeekerPreference.select(
        SeekerPreference.service,
        SeekerPreference.city,
        SeekerPreference.area
    ).where(SeekerPreference.registration == user.id).run()

    if not seeker_prefs:
        return {"message": "No preferences set. Add some to see helpers!", "helpers": []}

    # 2. Build the query filter
    # We want to find helpers who match Service AND City AND Area
    # for ANY of the seeker's preference sets.
    match_filters = []
    for pref in seeker_prefs:
        match_filters.append(
            (HelperPreference.service == pref['service']) &
            (HelperPreference.city == pref['city']) &
            (HelperPreference.area == pref['area'])
        )

    # Combine filters with OR (|) logic
    final_filter = match_filters[0]
    for f in match_filters[1:]:
        final_filter |= f

    # 3. Fetch matching helpers with their Profile details
    # We join HelperPreference -> Registration -> Profile
    matching_helpers = await HelperPreference.select(
        HelperPreference.city,
        HelperPreference.area,
        HelperPreference.job_type,
        HelperPreference.service.name.as_alias("service_name"),
        HelperPreference.registration.id.as_alias("helper_id"),
        HelperPreference.registration.capacity.as_alias("capacity"),
    ).where(final_filter).run()

    # 4. Attach Names/Phones (Looping to attach profiles)
    feed = []
    for h in matching_helpers:
        # Determine which profile table to look in
        ProfileTable = HelperPersonal if h['capacity'] == 'personal' else HelperInstitutional
        profile = await ProfileTable.objects().where(
            ProfileTable.registration == h['helper_id']
        ).first().run()

        feed.append({
            "helper_name": profile.name if profile else "Unknown Helper",
            "service": h['service_name'],
            "location": f"{h['area']}, {h['city']}",
            "job_type": h['job_type'],
            "helper_id": h['helper_id']
        })

    return feed


@router.get("/seeker-details/{target_id}")
async def get_seeker_details_endpoint(
    target_id: str, 
    current_reg: Registration = Depends(get_current_registration) 
):
    return await service.get_specific_seeker_full_details(target_id, current_reg)


 # find the helpers for seeker
@router.get("/find-my-helpers")
async def find_my_helpers(user: Registration = Depends(get_current_registration)):
    # Ensure only seekers can call this
    if user.role != "seeker":
        raise HTTPException(status_code=403, detail="Only Seekers can search for Helpers.")
        
    return await service.get_matches_for_seeker_logic(user.id)
        
    

@router.get("/seeker-side details")
async def find_my_ss(user:Registration=Depends(get_current_registration)):
    if user.role!="seeker":
        raise HTTPException(status_code=403)
    
    return await service.get_matches_for_seeker_logic()

 