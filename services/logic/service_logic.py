# services/logic/service_logic.py
import base64
import uuid
from datetime import date
from pathlib import Path

from fastapi import HTTPException, status

from db.tables import (
    HelperInstitutional,
    HelperPersonal,
    HelperPreference,
    ProfilePicture,
    Registration,
    SeekerInstitutional,
    SeekerPersonal,
    SeekerPreferenceNew,
    Service,
)
from profiles.logic.profile_service import get_profile_base64_logic
from ratings.logic.service import get_helper_overall_rating


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

    service_name = service.name
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


async def _encode_image_from_path(relative_path: str) -> str | None:
    """
    Helper to convert a file path to a base64 Data URL.
    Returns None if the path is empty or the file does not exist.
    """
    if not relative_path:
        return None

    # Base directory for your project
    base_dir = Path(r"C:\CompanyProject\gshbe")
    full_path = base_dir / relative_path

    if not full_path.exists():
        return None

    try:
        with open(full_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            ext = full_path.suffix.lower().replace(".", "")
            # Determine correct mime type
            mime = "image/png" if ext == "png" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
    except Exception:
        # Silently fail and return None if file is corrupted or unreadable
        return None


# C:\CompanyProject\gshbe\admin\logic\service.py


async def get_admin_user_report():
    # 1. Fetch aggregate counts
    helpers_count = (
        await Registration.count()
        .where(Registration.role.is_in(["helper", "both"]))
        .run()
    )

    seekers_count = (
        await Registration.count()
        .where(Registration.role.is_in(["seeker", "both"]))
        .run()
    )

    # 2. Fetch all Registration records with Account details
    raw_data = await Registration.select(
        Registration.account.id,  # This is the account_id
        Registration.account.phone,
        Registration.account.is_active,
        Registration.role,
        Registration.capacity,
        Registration.id,  # This is the registration_id
    ).run()

    # --- BATCH FETCH PROFILE PICTURE PATHS ---
    acc_ids = [item["account.id"] for item in raw_data]
    all_pics = (
        await ProfilePicture.objects()
        .where(ProfilePicture.account.is_in(acc_ids))
        .run()
    )
    pic_map = {str(p.account): p.file_path for p in all_pics}

    user_list = []

    # 3. LOOP THROUGH USERS AND ENRICH DATA
    for item in raw_data:
        reg_id_str = str(item["id"])
        acc_id_str = str(item["account.id"])  # Extracted here
        role = item["role"]
        capacity = item["capacity"]

        rating_stats = await get_helper_overall_rating(reg_id_str)

        assigned_services = []
        if role in ["helper", "both"]:
            pref_data = (
                await HelperPreference.select(
                    HelperPreference.service.name.as_alias("s_name")
                )
                .where(HelperPreference.registration == reg_id_str)
                .run()
            )
            assigned_services = [s["s_name"] for s in pref_data]

        # Dynamic Profile Lookup
        profile = None
        if role in ["helper", "both"]:
            table = HelperPersonal if capacity == "personal" else HelperInstitutional
            profile = (
                await table.objects()
                .where(table.registration == reg_id_str)
                .first()
                .run()
            )
        else:
            table = SeekerPersonal if capacity == "personal" else SeekerInstitutional
            profile = (
                await table.objects()
                .where(table.registration == reg_id_str)
                .first()
                .run()
            )

        file_path = pic_map.get(acc_id_str)
        encoded_pic = await _encode_image_from_path(file_path) if file_path else None

        # 4. Add to the final report list
        user_list.append(
            {
                "account_id": acc_id_str,  # <--- NEW FIELD ADDED
                "registration_id": reg_id_str,
                "name": getattr(profile, "name", "N/A") if profile else "N/A",
                "role": role,
                "phone": item["account.phone"],
                "is_active": item["account.is_active"],
                "profile_picture": encoded_pic,
                "rating": rating_stats,
                "allocated_services": assigned_services,
                "location": {
                    "city": getattr(profile, "city", "N/A") if profile else "N/A",
                    "area": (
                        getattr(profile, "area", "N/A")
                        if hasattr(profile, "area")
                        else "N/A"
                    ),
                },
            }
        )

    return {
        "status": "success",
        "summary": {
            "total_helpers": helpers_count,
            "total_seekers": seekers_count,
            "total_users": len(user_list),
        },
        "users": user_list,
    }


async def get_growth_by_date(start: date, end: date):

    helpers = await Registration.count().where(
        (Registration.role == "helper")
        & (Registration.account.created_at >= start)
        & (Registration.account.created_at <= end)
    )

    seekers = await Registration.count().where(
        (Registration.role == "seeker")
        & (Registration.account.created_at >= start)
        & (Registration.account.created_at <= end)
    )

    return {
        "start_date": start,
        "end_date": end,
        "new_helpers": helpers,
        "new_seekers": seekers,
        "total_new_joins": helpers + seekers,
    }


# async def get_service_participants_logic(service_id: str):
#     try:
#         service_uuid = uuid.UUID(service_id)
#     except (ValueError, TypeError, AttributeError):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Invalid Service ID format: '{service_id}'",
#         )

#     # --- 2. FETCH PREFERENCES ---
#     h_prefs = (
#         await HelperPreference.objects()
#         .where(HelperPreference.service == service_uuid)
#         .prefetch(HelperPreference.registration, HelperPreference.registration.account)
#         .run()
#     )

#     s_prefs = (
#         await SeekerPreferenceNew.objects()
#         .where(SeekerPreferenceNew.service == service_uuid)
#         .prefetch(
#             SeekerPreferenceNew.registration, SeekerPreferenceNew.registration.account
#         )
#         .run()
#     )

#     # --- 3. BATCH FETCH PROFILES (Checking both Personal and Institutional) ---
#     helper_reg_ids = [hp.registration.id for hp in h_prefs]
#     seeker_reg_ids = [sp.registration.id for sp in s_prefs]

#     # Helpers
#     h_personal = (
#         await HelperPersonal.objects()
#         .where(HelperPersonal.registration.is_in(helper_reg_ids))
#         .run()
#     )
#     h_institutional = (
#         await HelperInstitutional.objects()
#         .where(HelperInstitutional.registration.is_in(helper_reg_ids))
#         .run()
#     )

#     # Seekers
#     s_personal = (
#         await SeekerPersonal.objects()
#         .where(SeekerPersonal.registration.is_in(seeker_reg_ids))
#         .run()
#     )
#     s_institutional = (
#         await SeekerInstitutional.objects()
#         .where(SeekerInstitutional.registration.is_in(seeker_reg_ids))
#         .run()
#     )

#     # Create unified dictionaries
#     h_profiles = {p.registration: p for p in h_personal + h_institutional}
#     s_profiles = {p.registration: p for p in s_personal + s_institutional}

#     # --- 4. PROCESS HELPERS ---
#     helpers_list = []
#     for hp in h_prefs:
#         reg = hp.registration
#         profile = h_profiles.get(reg.id)

#         helpers_list.append(
#             {
#                 "account_id": str(reg.account.id),
#                 "registration_id": str(reg.id),
#                 "name": getattr(
#                     profile, "name", "Unknown Helper"
#                 ),  # Use getattr for safety
#                 "phone": reg.account.phone,
#                 "profile_picture": await get_profile_base64_logic(reg.id),
#                 "city": getattr(profile, "city", "N/A"),
#                 "capacity": reg.capacity,
#             }
#         )

#     # --- 5. PROCESS SEEKERS ---
#     seekers_list = []
#     for sp in s_prefs:
#         reg = sp.registration
#         profile = s_profiles.get(reg.id)

#         seekers_list.append(
#             {
#                 "account_id": str(reg.account.id),
#                 "registration_id": str(reg.id),
#                 "name": getattr(profile, "name", "Unknown Seeker"),
#                 "phone": reg.account.phone,
#                 "profile_picture": await get_profile_base64_logic(reg.id),
#                 "city": getattr(profile, "city", "N/A"),
#                 "capacity": reg.capacity,
#             }
#         )

#     return {
#         "service_id": str(service_uuid),
#         "helpers_count": len(helpers_list),
#         "seekers_count": len(seekers_list),
#         "helpers": helpers_list,
#         "seekers": seekers_list,
#     }


async def get_service_participants_logic(service_id: str):
    try:
        service_uuid = uuid.UUID(service_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Service ID format: '{service_id}'",
        )

    # --- 1. FETCH PREFERENCES ---
    h_prefs = (
        await HelperPreference.objects()
        .where(HelperPreference.service == service_uuid)
        .prefetch(HelperPreference.registration, HelperPreference.registration.account)
        .run()
    )

    s_prefs = (
        await SeekerPreferenceNew.objects()
        .where(SeekerPreferenceNew.service == service_uuid)
        .prefetch(
            SeekerPreferenceNew.registration, SeekerPreferenceNew.registration.account
        )
        .run()
    )

    # --- 2. BATCH FETCH ALL POSSIBLE PROFILES ---
    all_reg_ids = list(
        set(
            [hp.registration.id for hp in h_prefs]
            + [sp.registration.id for sp in s_prefs]
        )
    )

    # Fetch from all 4 tables to ensure no "Unknown" users
    h_pers = (
        await HelperPersonal.objects()
        .where(HelperPersonal.registration.is_in(all_reg_ids))
        .run()
    )
    h_inst = (
        await HelperInstitutional.objects()
        .where(HelperInstitutional.registration.is_in(all_reg_ids))
        .run()
    )
    s_pers = (
        await SeekerPersonal.objects()
        .where(SeekerPersonal.registration.is_in(all_reg_ids))
        .run()
    )
    s_inst = (
        await SeekerInstitutional.objects()
        .where(SeekerInstitutional.registration.is_in(all_reg_ids))
        .run()
    )

    # Build a master lookup dictionary {registration_id: profile_object}
    # We prioritize the "role-specific" profile, but allow fallback to any profile found
    master_profiles = {}
    for p in h_pers + h_inst + s_pers + s_inst:
        master_profiles[p.registration] = p

    # --- 3. PROCESS HELPERS ---
    helpers_list = []
    for hp in h_prefs:
        reg = hp.registration
        profile = master_profiles.get(reg.id)

        helpers_list.append(
            {
                "account_id": str(reg.account.id),
                "registration_id": str(reg.id),
                "name": getattr(profile, "name", "User")
                if profile
                else f"User {reg.account.phone[-4:]}",
                "phone": reg.account.phone,
                "profile_picture": await get_profile_base64_logic(reg.id),
                "city": getattr(profile, "city", "N/A"),
                "capacity": reg.capacity,
            }
        )

    # --- 4. PROCESS SEEKERS ---
    seekers_list = []
    for sp in s_prefs:
        reg = sp.registration
        # Look for seeker profile first, but fallback to helper profile if they are cross-registered
        profile = master_profiles.get(reg.id)

        seekers_list.append(
            {
                "account_id": str(reg.account.id),
                "registration_id": str(reg.id),
                "name": getattr(profile, "name", "User")
                if profile
                else f"User {reg.account.phone[-4:]}",
                "phone": reg.account.phone,
                "profile_picture": await get_profile_base64_logic(reg.id),
                "city": getattr(profile, "city", "N/A"),
                "capacity": reg.capacity,
            }
        )

    return {
        "service_id": str(service_uuid),
        "helpers_count": len(helpers_list),
        "seekers_count": len(seekers_list),
        "helpers": helpers_list,
        "seekers": seekers_list,
    }


async def create_service():
    SeekerPersonal.avg_rating = "check that evey element"
