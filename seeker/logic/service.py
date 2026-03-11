
from difflib import SequenceMatcher
import uuid

from fastapi import HTTPException, status
from db.tables import (
    HelperPersonal, HelperPreference, ProfilePicture, Registration, SeekerPersonal, SeekerInstitutional, 
    SeekerPreferenceNew, Account
)
from profiles.logic.profile_service import get_profile_base64_logic


async def get_specific_seeker_full_details(target_id: str, current_reg: Registration):
    # --- 1. VALIDATE INPUT (Prevents the "undefined" crash) ---
    try:
        # Check if target_id is a valid UUID string
        valid_uuid = uuid.UUID(target_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Invalid ID format: '{target_id}' is not a valid UUID."
        )

    # --- 2. FETCH TARGET REGISTRATION ---
    # Supports looking up by Registration ID or Account ID
    reg_info = await Registration.objects().where(
        (Registration.id == valid_uuid) | (Registration.account == valid_uuid)
    ).prefetch(Registration.account).first().run()

    if not reg_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Seeker registration not found."
        )

    # --- 3. SECURITY & ROLE CHECK ---
    current_user_id = str(current_reg.id)
    target_seeker_id = str(reg_info.id)
    current_role = str(current_reg.role).lower().strip()

    is_owner = current_user_id == target_seeker_id
    is_admin = current_role == 'admin'
    is_helper = current_role == 'helper'

    # Check if ANY of the allowed roles match
    if not (is_owner or is_admin or is_helper):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Role '{current_role}' is not authorized to view this profile."
        )

    # Define the seeker_id we are actually querying for
    seeker_id = reg_info.id

    # --- 4. FETCH PROFILE (Personal or Institutional) ---
    profile_details = {}
    if reg_info.capacity == "personal":
        profile = await SeekerPersonal.objects().where(
            SeekerPersonal.registration == seeker_id
        ).first().run()
        if profile:
            profile_details = {
                "name": profile.name,
                "city": profile.city,
                "area": profile.area,
                "about": getattr(profile, 'about', None),
                "rating": float(getattr(profile, 'avg_rating', 0.0) or 0.0)
            }
    else:
        profile = await SeekerInstitutional.objects().where(
            SeekerInstitutional.registration == seeker_id
        ).first().run()
        if profile:
            profile_details = {
                "name": profile.name,
                "institution_type": getattr(profile, 'institution_type', None),
                "city": profile.city,
                "address": getattr(profile, 'address', None),
                "rating": float(getattr(profile, 'avg_rating', 0.0) or 0.0)
            }

    # --- 5. FETCH PREFERENCES ---
    s_prefs = await SeekerPreferenceNew.objects().where(
        SeekerPreferenceNew.registration == seeker_id
    ).prefetch(
        SeekerPreferenceNew.service,
        SeekerPreferenceNew.location, 
        SeekerPreferenceNew.work, 
        SeekerPreferenceNew.requirements,
        SeekerPreferenceNew.helper_details
    ).run()

    # --- 6. FETCH PROFILE PICTURE (FOR THE TARGET SEEKER) ---
    # We use seeker_id, so Admins see the Seeker's photo, not their own.
    pic_base64 = await get_profile_base64_logic(seeker_id)

    # --- 7. CONSTRUCT FINAL RESPONSE ---
    if not s_prefs:
        return {
            "status": "success",
            "seeker_id": str(seeker_id),
            "account_info": {
                "phone": reg_info.account.phone,
                "capacity": reg_info.capacity,
                "profile_picture": pic_base64
            },
            "profile": profile_details,
            "preferences": []
        }

    # Extract main data from the first preference object
    main_pref = s_prefs[0]
    matched_services = [{"id": str(p.service.id), "name": p.service.name} for p in s_prefs if p.service]

    return {
        "status": "success",
        "seeker_id": str(seeker_id),
        "account_info": {
            "phone": reg_info.account.phone,
            "capacity": reg_info.capacity,
            "is_active": getattr(reg_info.account, 'is_active', True),
            "profile_picture": pic_base64
        },
        "profile": profile_details,
        "services_required": matched_services,
        "location": {
            "city": main_pref.location.city if main_pref.location else None,
            "area": main_pref.location.area if main_pref.location else None
        },
        "work_details": {
            "job_type": main_pref.work.job_type if main_pref.work else None,
            "work_mode": main_pref.work.work_mode if main_pref.work else None,
            "working_days": main_pref.work.working_days if main_pref.work else None,
            "accommodation": main_pref.work.accommodation if main_pref.work else None
        },
        "requirements": {
            "salary_min": main_pref.requirements.min_salary if main_pref.requirements else None,
            "salary_max": main_pref.requirements.max_salary if main_pref.requirements else None,
            "gender_pref": main_pref.requirements.gender if main_pref.requirements else "Any",
            "age_range": f"{main_pref.requirements.min_age or 0} - {main_pref.requirements.max_age or 100}",
            "experience_required": main_pref.requirements.experience if main_pref.requirements else None
        },
        "additional_notes": {
            "skills_needed": main_pref.helper_details.skills if main_pref.helper_details else ""
        }
    }



def get_similarity(a: str, b: str) -> float:
    if not a or not b: return 0.0
    return SequenceMatcher(None, str(a).lower().strip(), str(b).lower().strip()).ratio()

async def get_matches_for_seeker_logic(user_id: str):
    # 1. Fetch Seeker's Preferences
    s_prefs = await SeekerPreferenceNew.objects().where(
        SeekerPreferenceNew.registration == user_id
    ).prefetch(
        SeekerPreferenceNew.service, SeekerPreferenceNew.location, 
        SeekerPreferenceNew.work, SeekerPreferenceNew.requirements,
        SeekerPreferenceNew.helper_details
    ).run()

    if not s_prefs:
        return []

    # Use the first preference as the primary anchor for city/work-type
    s_main = s_prefs[0]
    required_service_ids = [p.service.id for p in s_prefs]

    # 2. Query Potential Helpers
    # Match on same Services and same Job Type (Full-time/Part-time)
    potential_helpers = await HelperPreference.objects().where(
        (HelperPreference.service.is_in(required_service_ids)) &
        (HelperPreference.work.job_type == s_main.work.job_type)
    ).prefetch(
        HelperPreference.registration, HelperPreference.service, 
        HelperPreference.location, HelperPreference.work, 
        HelperPreference.requirements, HelperPreference.helperpreference_details
    ).run()

    grouped_results = {}

    for h in potential_helpers:
        # --- MANDATORY CITY CHECK ---
        if get_similarity(h.location.city, s_main.location.city) < 0.95:
            continue
        
        score = 0
        checks = 0

        # --- MATCHING CALCULATIONS ---
        # 1. Area Similarity
        area_sim = get_similarity(h.location.area, s_main.location.area)
        if area_sim > 0.8: score += 1
        checks += 1 

        # 2. Work Mode & Accommodation
        if h.work.work_mode == s_main.work.work_mode: score += 1
        if h.work.accommodation == s_main.work.accommodation: score += 1
        checks += 2

        # 3. Salary Range Match (Can seeker afford this helper?)
        if h.requirements.min_salary <= s_main.requirements.max_salary: score += 1
        checks += 1

        # 4. Gender Preference (Does helper match seeker's requirement?)
        if s_main.requirements.gender == "Any" or h.requirements.gender == s_main.requirements.gender:
            score += 1
        checks += 1

        match_pct = (score / checks) * 100 if checks > 0 else 0
        
        if match_pct >= 60:
            h_reg_id = str(h.registration.id)
            
            # If helper already in dict, add this service to their list
            if h_reg_id in grouped_results:
                grouped_results[h_reg_id]["match_details"]["matched_services"].append(h.service.name)
                continue

            # --- DATA COLLECTION ---
            account_record = await Account.objects().get(Account.id == h.registration.account).run()
            h_profile = await HelperPersonal.objects().where(
                HelperPersonal.registration == h.registration.id
            ).first().run()
            
            pic_base64 = await get_profile_base64_logic(user_id)
            grouped_results[h_reg_id] = {
                "match_details": {
                    "score": f"{round(match_pct)}%",
                    "matched_services": [h.service.name]
                },
                "helper_info": {
                    "registration_id": h_reg_id,
                    "name": h_profile.name if h_profile else "Anonymous Helper",
                    "profile_pic": pic_base64,
                    "rating": float(h_profile.avg_rating or 0.0) if h_profile else 0.0,
                    "rating_count": h_profile.rating_count if h_profile else 0,
                    "contact_phone": account_record.phone if account_record else None,
                    "age": h_profile.age if h_profile else "N/A"
                },
                "location": {
                    "city": h.location.city,
                    "area": h.location.area
                },
                "work_details": {
                    "job_type": h.work.job_type,
                    "work_mode": h.work.work_mode,
                    "working_days": h.work.working_days,
                    "weekly_off": h.work.weekly_off,
                    "accommodation": h.work.accommodation
                },
                "requirements": {
                   "salary_min_expected": h.requirements.min_salary, 
                   "salary_max_budget": s_main.requirements.max_salary,
                   "gender": h.requirements.gender,
                   "experience": h.requirements.experience,
                   "skills": h.helperpreference_details.skills if h.helperpreference_details else ""
                }
            }

    # Sort final list by score descending
    final_list = list(grouped_results.values())
    return sorted(final_list, key=lambda x: int(x['match_details']['score'].replace('%', '')), reverse=True)