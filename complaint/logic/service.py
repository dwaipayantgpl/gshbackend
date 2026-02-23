from complaint.structs.dtos import ComplaintCreate
from db.tables import Complaint, Account

async def submit_complaint(account_id: str, payload: ComplaintCreate):
    complaint = Complaint(
        account=account_id,
        subject=payload.subject,
        description=payload.description
    )
    await complaint.save()
    return {"message": "Complaint submitted successfully"}
from db.tables import (
    Complaint, Account, Registration, 
    SeekerPersonal, SeekerInstitutional, 
    HelperPersonal, HelperInstitutional
)

async def get_all_complaints():
    # 1. Fetch complaints and the basic account info
    complaints = await Complaint.select(
        Complaint.id,
        Complaint.subject,
        Complaint.description,
        Complaint.status,
        Complaint.created_at,
        Complaint.account.id.as_alias("account_id"),
        Complaint.account.phone.as_alias("phone")
    ).order_by(Complaint.created_at, ascending=False).run()

    # 2. For each complaint, find the name based on the account_id
    for item in complaints:
        acc_id = item["account_id"]
        user_name = "Unknown User"

        reg = await Registration.objects().get(Registration.account == acc_id).run()
        
        if reg:
            sp = await SeekerPersonal.select(SeekerPersonal.name).where(SeekerPersonal.registration == reg.id).first().run()
            si = await SeekerInstitutional.select(SeekerInstitutional.name).where(SeekerInstitutional.registration == reg.id).first().run()
            hp = await HelperPersonal.select(HelperPersonal.name).where(HelperPersonal.registration == reg.id).first().run()
            hi = await HelperInstitutional.select(HelperInstitutional.name).where(HelperInstitutional.registration == reg.id).first().run()

            # Assign the first name we find
            found_name = (sp or si or hp or hi)
            if found_name:
                user_name = found_name["name"]

        item["user_name"] = user_name

    return complaints

async def update_complaint_status(complaint_id: str, status: str):
    complaint = await Complaint.objects().get(Complaint.id == complaint_id)
    complaint.status = status
    await complaint.save()
    return {"message": f"Complaint status updated to {status}"}