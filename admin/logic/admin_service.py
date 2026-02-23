from datetime import datetime, timedelta

from fastapi import HTTPException
from admin.structs.dtos import ComplaintCreate
from db.tables import (
     BlacklistedUser, BlockedUser, Complaint, HelperPreference, HelperService, JobRequestService, Registration, Account, SeekerPersonal, SeekerInstitutional, 
    HelperPersonal, HelperInstitutional, SeekerPreference, Service
)

async def get_last_month_user_report():
    # 1. Calculate the date 30 days ago
    one_month_ago = datetime.now() - timedelta(days=30)

    # 2. Fetch all registrations from the last month
    # We join with Account to get the phone number
    recent_registrations = await Registration.select(
        Registration.id,
        Registration.role,
        Registration.capacity,
        Registration.created_at,
        Registration.account.phone
    ).where(Registration.created_at >= one_month_ago).run()

    helpers_list = []
    seekers_list = []

    for reg in recent_registrations:
        reg_id = reg['id']
        capacity = reg['capacity']
        role = reg['role']
        
        # Determine the name based on role and capacity
        name = "Unknown"
        if role == 'helper':
            if capacity == 'personal':
                prof = await HelperPersonal.objects().where(HelperPersonal.registration == reg_id).first()
            else:
                prof = await HelperInstitutional.objects().where(HelperInstitutional.registration == reg_id).first()
            if prof: name = prof.name
            
            helpers_list.append({
                "name": name,
                "phone": reg['account.phone'],
                "capacity": capacity,
                "joined_at": reg['created_at']
            })
            
        elif role == 'seeker':
            if capacity == 'personal':
                prof = await SeekerPersonal.objects().where(SeekerPersonal.registration == reg_id).first()
            else:
                prof = await SeekerInstitutional.objects().where(SeekerInstitutional.registration == reg_id).first()
            if prof: name = prof.name
            
            seekers_list.append({
                "name": name,
                "phone": reg['account.phone'],
                "capacity": capacity,
                "joined_at": reg['created_at']
            })

    return {
        "time_period": "Last 30 Days",
        "total_new_helpers": len(helpers_list),
        "total_new_seekers": len(seekers_list),
        "helpers_details": helpers_list,
        "seekers_details": seekers_list
    }


# async def get_service_deep_analytics():
#     all_services = await Service.objects()
#     report = []

#     for s in all_services:
#         # 1. FETCH HELPERS
#         # Only select fields that actually exist in Registration/Account
#         helpers_data = await HelperService.select(
#             HelperService.helper.id,
#             HelperService.helper.capacity,
#             HelperService.helper.account.phone,
#         ).where(HelperService.service == s.id).run()

#         detailed_helpers = []
#         for h in helpers_data:
#             h_id = h['helper.id']
#             capacity = h['helper.capacity']
            
#             # Find the name in the correct table based on capacity
#             name = "Unknown"
#             if capacity == 'personal':
#                 profile = await HelperPersonal.objects().where(HelperPersonal.registration == h_id).first()
#                 if profile: name = profile.name
#             else:
#                 profile = await HelperInstitutional.objects().where(HelperInstitutional.registration == h_id).first()
#                 if profile: name = profile.name

#             # Get preference
#             pref = await HelperPreference.objects().where(HelperPreference.registration == h_id).first()
            
#             detailed_helpers.append({
#                 "name": name,
#                 "phone": h['helper.account.phone'],
#                 "capacity": capacity,
#                 "shift": pref.job_type if pref else "not_specified"
#             })

#         # 2. FETCH SEEKERS
#         seekers_data = await JobRequestService.select(
#             JobRequestService.job_request.seeker.id,
#             JobRequestService.job_request.seeker.capacity,
#             JobRequestService.job_request.job_type,
#             JobRequestService.job_request.seeker.account.phone
#         ).where(JobRequestService.service == s.id).run()

#         detailed_seekers = []
#         for sk in seekers_data:
#             sk_id = sk['job_request.seeker.id']
#             capacity = sk['job_request.seeker.capacity']

#             name = "Unknown"
#             if capacity == 'personal':
#                 profile = await SeekerPersonal.objects().where(SeekerPersonal.registration == sk_id).first()
#                 if profile: name = profile.name
#             else:
#                 profile = await SeekerInstitutional.objects().where(SeekerInstitutional.registration == sk_id).first()
#                 if profile: name = profile.name

#             detailed_seekers.append({
#                 "name": name,
#                 "phone": sk['job_request.seeker.account.phone'],
#                 "capacity": capacity,
#                 "shift": sk['job_request.job_type']
#             })

#         report.append({
#             "service_name": s.name,
#             "total_helpers": len(detailed_helpers), 
#             "total_seekers": len(detailed_seekers),
#             "helpers": detailed_helpers,
#             "seekers": detailed_seekers
#         })

#     return report

async def get_service_deep_analytics():
    all_services = await Service.objects()
    report = []

    for s in all_services:
        # --- 1. FETCH HELPERS ---
        helpers_data = await HelperService.select(
            HelperService.helper.id.as_alias("h_id"),
            HelperService.helper.capacity.as_alias("capacity"),
            HelperService.helper.account.phone.as_alias("phone"),
        ).where(HelperService.service == s.id).run()

        detailed_helpers = []
        for h in helpers_data:
            h_id = h['h_id']
            cap = h['capacity']
            
            # Name lookup logic
            name = "Unknown"
            Table = HelperPersonal if cap == 'personal' else HelperInstitutional
            profile = await Table.objects().where(Table.registration == h_id).first().run()
            if profile: name = profile.name

            # Preference lookup (for shift)
            pref = await HelperPreference.objects().where(HelperPreference.registration == h_id).first().run()
            
            detailed_helpers.append({
                "name": name,
                "phone": h['phone'],
                "capacity": cap,
                "shift": pref.job_type if pref else "not_specified"
            })

        # --- 2. FETCH SEEKERS (Using SeekerPreference instead of JobRequest) ---
        # Note: If you want people who just "selected" the service, use SeekerPreference
        seekers_data = await SeekerPreference.select(
            SeekerPreference.registration.id.as_alias("sk_id"),
            SeekerPreference.registration.capacity.as_alias("capacity"),
            SeekerPreference.registration.account.phone.as_alias("phone"),
            SeekerPreference.job_type.as_alias("shift")
        ).where(SeekerPreference.service == s.id).run()

        detailed_seekers = []
        for sk in seekers_data:
            sk_id = sk['sk_id']
            cap = sk['capacity']

            name = "Unknown"
            Table = SeekerPersonal if cap == 'personal' else SeekerInstitutional
            profile = await Table.objects().where(Table.registration == sk_id).first().run()
            if profile: name = profile.name

            detailed_seekers.append({
                "name": name,
                "phone": sk['phone'],
                "capacity": cap,
                "shift": sk['shift']
            })

        report.append({
            "service_name": s.name,
            "total_helpers": len(detailed_helpers), 
            "total_seekers": len(detailed_seekers),
            "helpers": detailed_helpers,
            "seekers": detailed_seekers
        })

    return report

async def admin_delete_user_permanently(account_id: str): # Reason removed from here
    # 1. Get the account
    account = await Account.objects().where(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Add to Blacklist (Updated to match your new table schema)
    await BlacklistedUser.insert(
        BlacklistedUser(
            phone=account.phone, 
            banned_at=datetime.now()
            # reason=reason removed because column is gone
        )
    )

    # 3. Find Registration to clean up profiles
    reg = await Registration.objects().where(Registration.account == account_id).first()
    if reg:
        # Delete profile data first (Child tables)
        await SeekerPersonal.delete().where(SeekerPersonal.registration == reg.id)
        await SeekerInstitutional.delete().where(SeekerInstitutional.registration == reg.id)
        await HelperPersonal.delete().where(HelperPersonal.registration == reg.id)
        await HelperInstitutional.delete().where(HelperInstitutional.registration == reg.id)
        
        # Delete the registration itself
        await reg.remove()

    # 4. Finally, remove the Account
    await account.remove()
    return {"message": "User deleted and phone number blacklisted permanently."}


#block-unblock
async def block_user_logic(account_id: str):
    # Check if already blocked
    exists = await BlockedUser.objects().where(BlockedUser.account == account_id).first()
    if exists:
        return {"message": "User is already blocked."}
    
    await BlockedUser.insert(BlockedUser(account=account_id))
    return {"message": f"User blocked successfully"}

# --- UNBLOCK USER ---
async def unblock_user_logic(account_id: str):
    blocked_record = await BlockedUser.objects().where(BlockedUser.account == account_id).first()
    if not blocked_record:
        raise HTTPException(status_code=404, detail="User was not in the block list.")
    
    await blocked_record.remove()
    return {"message": "User unblocked successfully."}

# --- get all user blocked data -----------
async def get_all_blocked_users():
    blocked_list = await BlockedUser.select(
        BlockedUser.account.id.as_alias("account_id"),
        BlockedUser.account.phone.as_alias("phone"),
        BlockedUser.blocked_at
    ).run()

    results = []

    for entry in blocked_list:
        acc_id = entry["account_id"]
        
        # 2. Get Registration details (Role & Capacity)
        reg = await Registration.objects().get(
            Registration.account == acc_id
        ).run()

        if reg:
            # 3. Fetch Name based on capacity and role
            user_name = "Unknown"
            
            # Check Seeker tables
            sp = await SeekerPersonal.select(SeekerPersonal.name).where(SeekerPersonal.registration == reg.id).first().run()
            si = await SeekerInstitutional.select(SeekerInstitutional.name).where(SeekerInstitutional.registration == reg.id).first().run()
            
            # Check Helper tables
            hp = await HelperPersonal.select(HelperPersonal.name).where(HelperPersonal.registration == reg.id).first().run()
            hi = await HelperInstitutional.select(HelperInstitutional.name).where(HelperInstitutional.registration == reg.id).first().run()

            # Assign found name
            found_name_obj = (sp or si or hp or hi)
            if found_name_obj:
                user_name = found_name_obj["name"]

            # 4. Build the final object
            results.append({
                "account_id": acc_id,
                "name": user_name,
                "phone": entry["phone"],
                "role": reg.role,
                "capacity": reg.capacity,
                "blocked_at": entry["blocked_at"]
            })

    return results


#get helper data
async def get_helper_status_stats():
  
    helper_filter = Registration.role.is_in(['helper', 'both'])
    total_helpers = await Registration.count().where(helper_filter).run()
    active_helpers = await Registration.count().where(
        helper_filter & (Registration.account.is_active == True)
    ).run()

    inactive_helpers = total_helpers - active_helpers

    return {
        "summary": {
            "total_helpers": total_helpers,
            "active_helpers": active_helpers,
            "inactive_helpers": inactive_helpers
        }
    }

#Complain 
async def submit_complaint(account_id: str, payload: ComplaintCreate):
    complaint = Complaint(
        account=account_id,
        subject=payload.subject,
        description=payload.description
    )
    await complaint.save()
    return {"message": "Complaint submitted successfully"}

async def get_all_complaints():
    # Join with Account to show the phone number of the person complaining
    return await Complaint.select(
        Complaint.id,
        Complaint.subject,
        Complaint.description,
        Complaint.status,
        Complaint.created_at,
        Complaint.account.id.as_alias("account_id"),
        Complaint.account.phone.as_alias("phone")
    ).order_by(Complaint.created_at, ascending=False).run()

async def update_complaint_status(complaint_id: str, status: str):
    complaint = await Complaint.objects().get(Complaint.id == complaint_id)
    complaint.status = status
    await complaint.save()
    return {"message": f"Complaint status updated to {status}"}