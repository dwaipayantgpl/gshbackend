from difflib import SequenceMatcher
from typing import Any, Dict, List

from fastapi import HTTPException, status

from db.tables import (
    Account,
    HelperInstitutional,
    HelperPersonal,
    HelperSpecialPreferences,
    PreferenceLocation,
    PreferenceRequirements,
    PreferenceWork,
    Registration,
    HelperPreference,
    HelperPreferredService,
    HelperExperience,
    SeekerInstitutional,
    SeekerPersonal,
    SeekerPreferenceNew,
    Service,
)
from profiles.logic.profile_service import get_profile_base64_logic


# ----------------------------
# Internal helpers
# ----------------------------

async def _get_registration_by_account_id(account_id: str) -> Registration:
    reg = await Registration.objects().where(Registration.account == account_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg


def _ensure_helper(reg: Registration) -> None:
    if reg.role not in ("helper", "both"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only helpers can access this resource",
        )


async def _validate_service_ids(service_ids: list[str]) -> None:
    if not service_ids:
        return

    rows = await Service.objects().where(Service.id.is_in(service_ids)).columns(Service.id)
    found = {str(r["id"]) for r in rows}
    missing = [sid for sid in service_ids if sid not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"Invalid service_ids: {missing}")


def _validate_years(year_from: int | None, year_to: int | None) -> None:
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(status_code=400, detail="year_from cannot be greater than year_to")


# ----------------------------
# Public read (ANYONE)
# ----------------------------

async def get_preference_by_registration_id(*, registration_id: str) -> dict:
    pref = await HelperPreference.objects().where(
        HelperPreference.registration == registration_id
    ).first()

    if not pref:
        return {
            "registration_id": str(registration_id),
            "city": None,
            "area": None,
            "job_type": None,
            "preferred_service_ids": [],
        }

    pref_services = await HelperPreferredService.objects().where(
        HelperPreferredService.registration == registration_id
    ).columns(HelperPreferredService.service)

    return {
        "registration_id": str(registration_id),
        "city": pref.city,
        "area": pref.area,
        "job_type": pref.job_type,
        "preferred_service_ids": [str(r["service"]) for r in pref_services],
    }


async def list_experience_by_registration_id(*, registration_id: str) -> list[dict]:
    rows = await HelperExperience.objects().where(
        HelperExperience.registration == registration_id
    )

    return [
        {
            "id": str(r.id),
            "registration_id": str(registration_id),
            "year_from": r.year_from,
            "year_to": r.year_to,
            "service_id": str(r.service) if r.service else None,
            "city": r.city,
            "area": r.area,
            "description": r.description,
        }
        for r in rows
    ]


# ----------------------------
# Owner-only
# ----------------------------

async def get_my_preference(*, account_id: str) -> dict:
    reg = await _get_registration_by_account_id(account_id)
    _ensure_helper(reg)
    return await get_preference_by_registration_id(registration_id=str(reg.id))


async def upsert_my_preference(*, account_id: str, payload: dict) -> dict:
    reg = await _get_registration_by_account_id(account_id)
    _ensure_helper(reg)

    preferred_service_ids = payload.get("preferred_service_ids", [])
    await _validate_service_ids(preferred_service_ids)

    existing = await HelperPreference.objects().where(
        HelperPreference.registration == reg.id
    ).first()

    data = {
        "city": payload.get("city"),
        "area": payload.get("area"),
        "job_type": payload.get("job_type"),
    }

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        await existing.save()
    else:
        row = HelperPreference(registration=reg.id, **data)
        await row.save()

    await HelperPreferredService.delete().where(
        HelperPreferredService.registration == reg.id
    )

    if preferred_service_ids:
        await HelperPreferredService.insert(
            *[
                HelperPreferredService(registration=reg.id, service=sid)
                for sid in preferred_service_ids
            ]
        )

    return await get_my_preference(account_id=account_id)


async def list_my_experience(*, account_id: str) -> list[dict]:
    reg = await _get_registration_by_account_id(account_id)
    _ensure_helper(reg)
    return await list_experience_by_registration_id(registration_id=str(reg.id))


async def create_my_experience(*, account_id: str, payload: dict) -> dict:
    reg = await _get_registration_by_account_id(account_id)
    _ensure_helper(reg)

    _validate_years(payload.get("year_from"), payload.get("year_to"))

    service_id = payload.get("service_id")
    if service_id:
        await _validate_service_ids([service_id])

    row = HelperExperience(registration=reg.id, **payload)
    await row.save()

    return {
        "id": str(row.id),
        "registration_id": str(reg.id),
        "year_from": row.year_from,
        "year_to": row.year_to,
        "service_id": str(row.service) if row.service else None,
        "city": row.city,
        "area": row.area,
        "description": row.description,
    }


async def update_my_experience(*, account_id: str, experience_id: str, payload: dict) -> dict:
    reg = await _get_registration_by_account_id(account_id)
    _ensure_helper(reg)

    row = await HelperExperience.objects().where(
        HelperExperience.id == experience_id
    ).first()

    if not row or str(row.registration) != str(reg.id):
        raise HTTPException(status_code=404, detail="Experience not found")

    year_from = payload.get("year_from", row.year_from)
    year_to = payload.get("year_to", row.year_to)
    _validate_years(year_from, year_to)

    if "service_id" in payload and payload["service_id"]:
        await _validate_service_ids([payload["service_id"]])

    for k, v in payload.items():
        setattr(row, k, v)

    await row.save()

    return {
        "id": str(row.id),
        "registration_id": str(reg.id),
        "year_from": row.year_from,
        "year_to": row.year_to,
        "service_id": str(row.service) if row.service else None,
        "city": row.city,
        "area": row.area,
        "description": row.description,
    }


async def delete_my_experience(*, account_id: str, experience_id: str) -> dict:
    reg = await _get_registration_by_account_id(account_id)
    _ensure_helper(reg)

    row = await HelperExperience.objects().where(
        HelperExperience.id == experience_id
    ).first()

    if not row or str(row.registration) != str(reg.id):
        raise HTTPException(status_code=404, detail="Experience not found")

    await HelperExperience.delete().where(HelperExperience.id == experience_id)
    return {"deleted": True}


#---------------- post method -----------------

async def add_helper_preference_logic(data: Dict[str, Any], user_id: str):
    # 1. Check if record exists
    existing = await HelperPreference.objects().where(HelperPreference.registration == user_id).first().run()
    if existing:
        raise HTTPException(status_code=400, detail="Preferences already exist. Use PATCH to update.")

    # 2. Extract Data Maps
    loc_data = data.get("location", {})
    work_data = data.get("work_schedule", {})
    salary_data = data.get("salary_range", {})
    age_data = data.get("age_range", {})

    # 3. Create Shared Master Rows
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
        min_age=age_data.get("min"),         
        max_age=age_data.get("max"),         
        gender=data.get("gender", "any"),
        experience=str(data.get("experience", "0"))
    )
    details_row = await HelperSpecialPreferences.objects().create(
        skills=str(data.get("skills", "")),
        special_preferences=str(data.get("special_preferences", ""))
    )

    # 4. Link to all selected services
    service_ids = data.get("service_ids", [])
    if not service_ids:
         raise HTTPException(status_code=400, detail="At least one service_id is required.")

    for s_id in service_ids:
        await HelperPreference.objects().create(
            registration=user_id, 
            service=s_id,
            location=loc_row.id, 
            work=work_row.id,
            requirements=reqs_row.id, 
            helperpreference_details=details_row.id
        )
    return {"status": "success", "message": "Helper preferences initialized."}


# -----   udate logic - patch method --------------------
async def update_helper_preference_logic(data: Dict[str, Any], user_id: str):
    current_prefs = await HelperPreference.objects().where(HelperPreference.registration == user_id).run()
    if not current_prefs:
        raise HTTPException(status_code=404, detail="No preferences found.")

    # Master IDs for shared data
    m_loc = current_prefs[0].location
    m_work = current_prefs[0].work
    m_req = current_prefs[0].requirements
    m_det = current_prefs[0].helperpreference_details

    # 1. Update Location
    if "location" in data:
        await PreferenceLocation.update({
            PreferenceLocation.city: data["location"].get("city"),
            PreferenceLocation.area: data["location"].get("area")
        }).where(PreferenceLocation.id == m_loc).run()

    # 2. Update Work
    if any(k in data for k in ["work_schedule", "job_type", "work_mode"]):
        w = data.get("work_schedule", {})
        await PreferenceWork.update({
            PreferenceWork.job_type: data.get("job_type"),
            PreferenceWork.work_mode: data.get("work_mode"),
            PreferenceWork.working_days: w.get("working_days_per_week"),
            PreferenceWork.weekly_off: w.get("weekly_off_day"),
            PreferenceWork.accommodation: w.get("accommodation_provided")
        }).where(PreferenceWork.id == m_work).run()

    # 3. Update Requirements
    if any(k in data for k in ["salary_range", "age_range", "gender", "experience"]):
        sal = data.get("salary_range", {})
        age = data.get("age_range", {})
        await PreferenceRequirements.update({
            PreferenceRequirements.min_salary: sal.get("min"),
            PreferenceRequirements.max_salary: sal.get("max"),
            PreferenceRequirements.min_age: age.get("min"),
            PreferenceRequirements.max_age: age.get("max"),
            PreferenceRequirements.gender: data.get("gender"),
            PreferenceRequirements.experience: str(data.get("experience"))
        }).where(PreferenceRequirements.id == m_req).run()

    # 4. Update Helper Specific Details
    if any(k in data for k in ["skills", "special_preferences"]):
        await HelperSpecialPreferences.update({
            HelperSpecialPreferences.skills: str(data.get("skills")),
            HelperSpecialPreferences.special_preferences: str(data.get("special_preferences"))
        }).where(HelperSpecialPreferences.id == m_det).run()

    # --- PART 2: MANAGE SERVICE ARRAYS ---
    existing_sids = {str(p.service) for p in current_prefs}
    
    add_sids = data.get("service_ids") or []         # Array: Add
    remove_sids = data.get("remove_service_ids") or [] # Array: Remove

    # 1. Process Removals
    valid_removals = []
    if remove_sids:
        # Only remove IDs that actually exist in the current profile
        valid_removals = [sid for sid in remove_sids if str(sid) in existing_sids]
        if valid_removals:
            await HelperPreference.delete().where(
                (HelperPreference.registration == user_id) & 
                (HelperPreference.service.is_in(valid_removals))
            ).run()

    # 2. Process Additions
    added_service_names: List[str] = []
    for s_id in add_sids:
        # Don't add if it's already there
        if str(s_id) not in existing_sids:
            await HelperPreference.objects().create(
                registration=user_id, 
                service=s_id,
                location=m_loc, 
                work=m_work,
                requirements=m_req, 
                helperpreference_details=m_det
            )
            # Fetch the name for the response
            service_obj = await Service.objects().get(Service.id == s_id).run()
            if service_obj:
                added_service_names.append(service_obj.name)

    # 3. Formatted Response
    return {
        "status": "success",
        "message": "Preferences updated globally.",
        "newly_added": added_service_names,
        "removed_count": len(valid_removals)
    }


# --------- get method to check all details -------------------
async def get_helper_preference_logic(user_id: str):
    # 1. Fetch preferences and prefetch all linked tables
    preferences = await HelperPreference.objects().where(
        HelperPreference.registration == user_id
    ).prefetch(
        HelperPreference.service,
        HelperPreference.location,
        HelperPreference.work,
        HelperPreference.requirements,
        HelperPreference.helperpreference_details
    ).run() 

    if not preferences:
        return {"services": [], "details": None}

    # 2. Fetch Registration and Account (for Phone Number)
    # We prefetch account because every user has a phone number there
    reg = await Registration.objects().get(
        Registration.id == user_id
    ).prefetch(Registration.account).run()
    
    helper_age = None
    contact_phone = reg.account.phone if reg.account else None

    # 3. Branching for Profile Details
    if reg.capacity == "personal":
        profile = await HelperPersonal.objects().where(
            HelperPersonal.registration == user_id
        ).first().run()
        if profile:
            helper_age = profile.age
            # Personal helpers use Account phone (contact_phone already set above)
    else:
        profile = await HelperInstitutional.objects().where(
            HelperInstitutional.registration == user_id
        ).first().run()
        if profile and profile.phone:
            # Institutional helpers might have a specific business phone
            contact_phone = profile.phone

    # 4. Format services list
    services_list = [{
        "id": p.service.id,
        "name": p.service.name,
        "description": p.service.description
    } for p in preferences if p.service]

    first = preferences[0]
    
    # 5. Clean up requirements (removing Seeker-specific age ranges)
    req_dict = first.requirements.to_dict() if first.requirements else {}
    req_dict.pop("min_age", None)
    req_dict.pop("max_age", None)

    return {
        "services": services_list,
        "details": {
            "age": helper_age,
            "phone": contact_phone,  # Always fetched from Profile or Account
            "location": first.location.to_dict() if first.location else None,
            "work": first.work.to_dict() if first.work else None,
            "requirements": req_dict,
            "helper_details": first.helperpreference_details.to_dict() if first.helperpreference_details else None,
        }
    }
# ---------------  Find the matched seekers ------------------

def get_similarity(a: str, b: str) -> float:
    if not a or not b: return 0.0
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio()


async def get_matches_for_helper_logic(user_id: str):
    # 1. Fetch Helper Identity & Actual Age
    reg_info = await Registration.objects().get(Registration.id == user_id).run()
    
    helper_age = None
    if reg_info.capacity == "personal":
        profile = await HelperPersonal.objects().where(HelperPersonal.registration == user_id).first().run()
        helper_age = profile.age if profile else None

    # 2. Fetch Helper's Preferences
    h_prefs = await HelperPreference.objects().where(
        HelperPreference.registration == user_id
    ).prefetch(
        HelperPreference.service, HelperPreference.location, HelperPreference.work, 
        HelperPreference.requirements, HelperPreference.helperpreference_details
    ).run()

    if not h_prefs:
        return []

    h_main = h_prefs[0]
    offered_services = [p.service for p in h_prefs]

    # 3. Query Potential Seekers
    potential_seekers = await SeekerPreferenceNew.objects().where(
        (SeekerPreferenceNew.service.is_in(offered_services)) &
        (SeekerPreferenceNew.work.job_type == h_main.work.job_type)
    ).prefetch(
        SeekerPreferenceNew.registration, SeekerPreferenceNew.service, 
        SeekerPreferenceNew.location, SeekerPreferenceNew.work, 
        SeekerPreferenceNew.requirements, SeekerPreferenceNew.helper_details
    ).run()

    # Dictionary to group by seeker registration ID
    grouped_results = {}

    for s in potential_seekers:
        # --- MANDATORY CITY CHECK ---
        if get_similarity(s.location.city, h_main.location.city) < 0.95:
            continue
        
        score = 0
        checks = 0

        # --- MATCHING CALCULATIONS ---
        area_sim = get_similarity(s.location.area, h_main.location.area)
        if area_sim > 0.8: score += 1
        checks += 1 

        if s.work.work_mode == h_main.work.work_mode: score += 1
        if s.work.accommodation == h_main.work.accommodation: score += 1
        checks += 2

        if s.requirements.max_salary >= h_main.requirements.min_salary: score += 1
        checks += 1

        if helper_age:
            s_min = s.requirements.min_age or 0
            s_max = s.requirements.max_age or 100
            if s_min <= helper_age <= s_max: score += 1
            checks += 1

        match_pct = (score / checks) * 100 if checks > 0 else 0
        
        if match_pct >= 60:
            s_reg_id = str(s.registration.id)
            
            # If this seeker is already in our dictionary, just add the service
            if s_reg_id in grouped_results:
                grouped_results[s_reg_id]["match_details"]["matched_services"].append(s.service.name)
                # Keep the highest match score found
                current_score = int(grouped_results[s_reg_id]["match_details"]["score"].replace("%", ""))
                if match_pct > current_score:
                    grouped_results[s_reg_id]["match_details"]["score"] = f"{round(match_pct)}%"
                continue

            # Otherwise, perform the profile/account lookups once
            account_record = await Account.objects().get(Account.id == s.registration.account).run()
            contact_phone = account_record.phone if account_record else None

            if s.registration.capacity == 'personal':
                s_profile = await SeekerPersonal.objects().where(SeekerPersonal.registration == s.registration.id).first().run()
            else:
                s_profile = await SeekerInstitutional.objects().where(SeekerInstitutional.registration == s.registration.id).first().run()
                if s_profile and s_profile.phone:
                    contact_phone = s_profile.phone

            pic_base64 = await get_profile_base64_logic(s.registration.id)
            # Store the data in the dictionary
            grouped_results[s_reg_id] = {
                "match_details": {
                    "score": f"{round(match_pct)}%",
                    "matched_services": [s.service.name] # Start a list of services
                },
                "seeker_info": {
                    "registration_id": s_reg_id,
                    "capacity": s.registration.capacity,
                    "name": s_profile.name if s_profile else "Anonymous Seeker",
                    "profile_pic": pic_base64,
                    "rating": float(s_profile.avg_rating or 0.0),
                    "rating_count": s_profile.rating_count if s_profile else 0,
                    "institution_type": getattr(s_profile, 'institution_type', None) if s.registration.capacity == 'institutional' else None,
                    "contact_phone": contact_phone
                },
                "location": {
                    "city": s.location.city,
                    "area": s.location.area
                },
                "work_details": {
                    "job_type": s.work.job_type,
                    "work_mode": s.work.work_mode,
                    "working_days": s.work.working_days,
                    "weekly_off": s.work.weekly_off,
                    "accommodation": s.work.accommodation
                },
                "requirements": {
                    "salary_max": s.requirements.max_salary,
                    "gender_pref": s.requirements.gender,
                    "age_range": f"{s.requirements.min_age or 'Any'} - {s.requirements.max_age or 'Any'}",
                    "experience_needed": s.requirements.experience,
                    "skills_required": s.helper_details.skills if s.helper_details else ""
                }
            }

    # Convert dictionary back to a list and sort by score
    final_results = list(grouped_results.values())
    return sorted(final_results, key=lambda x: int(x['match_details']['score'].replace('%', '')), reverse=True)


async def get_specific_helper_full_details(target_id: str, current_reg: Registration):
    # 1. FETCH REGISTRATION (Check both ID types)
    reg_info = await Registration.objects().where(
        (Registration.id == target_id) | (Registration.account == target_id)
    ).prefetch(Registration.account).first().run()

    if not reg_info:
        raise HTTPException(status_code=404, detail="Helper not found.")

    # 2. SECURITY CHECK
    is_owner = str(current_reg.id) == str(reg_info.id)
    is_privileged = current_reg.role in ['admin', 'seeker']

    if not (is_owner or is_privileged):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to view this profile."
        )

    helper_id = reg_info.id

    # 3. FETCH PROFILE (Personal or Institutional)
    profile_details = {}
    if reg_info.capacity == "personal":
        profile = await HelperPersonal.objects().where(
            HelperPersonal.registration == helper_id
        ).first().run()
        if profile:
            profile_details = {
                "name": profile.name,
                "age": profile.age,
                # FIXED: 'gender' is not in HelperPersonal, it's usually in requirements 
                # or perhaps you intended to use 'faith' or 'languages' here?
                # I'm removing 'gender' from here to stop the crash.
                "experience": getattr(profile, 'years_of_experience', None),
                "city": profile.city,
                "area": profile.area
            }
    else:
        profile = await HelperInstitutional.objects().where(
            HelperInstitutional.registration == helper_id
        ).first().run()
        if profile:
            profile_details = {
                "name": profile.name,
                "city": profile.city,
                "address": profile.address
            }

    # 4. FETCH ALL PREFERENCES
    h_prefs = await HelperPreference.objects().where(
        HelperPreference.registration == helper_id
    ).prefetch(
        HelperPreference.service,
        HelperPreference.location, 
        HelperPreference.work, 
        HelperPreference.requirements,
        HelperPreference.helperpreference_details
    ).run()

    if not h_prefs:
        return {"registration": reg_info, "profile": profile_details, "preferences": []}

    main_pref = h_prefs[0]
    services = [{"id": str(p.service.id), "name": p.service.name} for p in h_prefs]
    
    base64_pic=await get_profile_base64_logic(current_reg.id)
    # 5. CONSTRUCT FULL RESPONSE
    return {
        "status": "success",
        "helper_id": str(helper_id),
        "account_info": {
            "phone": reg_info.account.phone,
            "capacity": reg_info.capacity,
            "is_active": reg_info.account.is_active, # FIXED: table uses 'is_active',
            "profile_picture":base64_pic

        },
        "profile": profile_details,
        "services": services,
        "location": {
            "city": main_pref.location.city if main_pref.location else None,
            "area": main_pref.location.area if main_pref.location else None
        },
        "work_details": {
            "job_type": main_pref.work.job_type if main_pref.work else None,
            "work_mode": main_pref.work.work_mode if main_pref.work else None,
            "working_days": main_pref.work.working_days if main_pref.work else None
        },
        "requirements": {
            "min_salary": main_pref.requirements.min_salary if main_pref.requirements else None,
            "max_salary": main_pref.requirements.max_salary if main_pref.requirements else None,
            "gender_pref": main_pref.requirements.gender if main_pref.requirements else None # This is where gender lives
        },
        "additional_details": {
            "skills": main_pref.helperpreference_details.skills if main_pref.helperpreference_details else None,
            "special_preferences": main_pref.helperpreference_details.special_preferences if main_pref.helperpreference_details else None
        }
    }