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