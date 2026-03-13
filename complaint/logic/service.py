# C:\CompanyProject\gshbe\complaint\logic\service.py
import base64
import os
import uuid
from pathlib import Path
from fastapi import UploadFile

from db.tables import (
    Account, Complaint, Registration, SeekerPersonal, 
    SeekerInstitutional, HelperPersonal, HelperInstitutional, ServiceBooking
)

# Match your existing static structure
COMPLAINT_UPLOAD_DIR = Path(r"C:\CompanyProject\gshbe\static\uploads\complaints_proof")

async def save_complaint_proof_logic(account_id: str, file: UploadFile):
    os.makedirs(COMPLAINT_UPLOAD_DIR, exist_ok=True)

    extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".jpg", ".jpeg", ".png", ".pdf"]

    if extension not in allowed_extensions:
        return {"status": "error", "message": "Only JPG, PNG, and PDF files are allowed."}

    try:
        unique_name = f"proof_{account_id}_{uuid.uuid4().hex[:8]}{extension}"
        file_save_path = COMPLAINT_UPLOAD_DIR / unique_name

        content = await file.read()
        with open(file_save_path, "wb") as f:
            f.write(content)

        relative_path = f"static/uploads/complaints_proof/{unique_name}"
        
        return {"status": "success", "relative_path": relative_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def get_proof_base64_from_path(relative_path: str):
    if not relative_path: return None
    full_path = Path(r"C:\CompanyProject\gshbe") / relative_path

    if not os.path.exists(full_path): return None

    try:
        with open(full_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
            ext = os.path.splitext(relative_path)[1].lower().replace(".", "")
            mime = "application/pdf" if ext == "pdf" else f"image/{ext if ext != 'jpg' else 'jpeg'}"
            return f"data:{mime};base64,{encoded}"
    except: return None

async def get_all_complaints():
    complaints = await Complaint.select(
        Complaint.all_columns(),
        Complaint.account_id.phone.as_alias("phone")
    ).order_by(Complaint.created_at, ascending=False).run()

    for item in complaints:
        # --- Existing Base64 and Reporter Name Logic ---
        if item["proof_image"]:
            item["proof_image"] = await get_proof_base64_from_path(item["proof_image"])
        
        user_name = "Unknown User"
        registration_id = None 
        reg = await Registration.objects().where(Registration.account == item["account_id"]).first().run()
        if reg:
            registration_id = str(reg.id) 
            sp = await SeekerPersonal.objects().where(SeekerPersonal.registration == reg.id).first().run()
            si = await SeekerInstitutional.objects().where(SeekerInstitutional.registration == reg.id).first().run()
            hp = await HelperPersonal.objects().where(HelperPersonal.registration == reg.id).first().run()
            hi = await HelperInstitutional.objects().where(HelperInstitutional.registration == reg.id).first().run()
            profile = sp or si or hp or hi
            if profile: user_name = getattr(profile, 'name', "Unknown User")
        
        item["user_name"] = user_name
        item["registration_id"] = registration_id

        # --- NEW: Helper Details Lookup via Booking ID ---
        item["helper_id"] = None
        item["helper_name"] = "N/A"
        item["helper_phone"] = "N/A"

        if item["booking_id"]:
            # 1. Find the booking to get the helper's registration ID
            booking = await ServiceBooking.objects().get(ServiceBooking.id == item["booking_id"]).run()
            if booking and booking.helper:
                helper_reg_id = booking.helper # This is the registration ID of the helper
                item["helper_id"] = str(helper_reg_id)

                # 2. Get Helper's phone from Account table via Registration
                h_reg = await Registration.objects().get(Registration.id == helper_reg_id).run()
                if h_reg:
                    h_account = await Account.objects().get(Account.id == h_reg.account).run()
                    item["helper_phone"] = h_account.phone if h_account else "N/A"

                # 3. Get Helper's name (checking Personal and Institutional)
                h_p = await HelperPersonal.objects().where(HelperPersonal.registration == helper_reg_id).first().run()
                h_i = await HelperInstitutional.objects().where(HelperInstitutional.registration == helper_reg_id).first().run()
                
                h_profile = h_p or h_i
                if h_profile:
                    item["helper_name"] = getattr(h_profile, 'name', "Unknown Helper")

    return complaints


async def update_complaint_status(complaint_id: str, status: str):
    complaint = await Complaint.objects().get(Complaint.id == complaint_id).run()
    if not complaint: return {"error": "Not found"}
    complaint.status = status
    await complaint.save()
    return {"message": f"Status updated to {status}"}



async def get_user_complaint_history_logic(registration_id: str):
    try:
        # 1. Convert the incoming Registration ID (Seeker/Helper ID) to UUID
        reg_uuid = uuid.UUID(registration_id)
    except ValueError:
        return {"status": "error", "message": "Invalid Registration ID format"}

    # 2. Find the Account linked to this Registration
    reg = await Registration.objects().get(Registration.id == reg_uuid).run()
    if not reg:
        return {"status": "error", "message": "Registration record not found"}
    
    # This is the "Human ID" we use to find complaints
    acc_uuid = reg.account 

    # 3. Fetch all complaints using the Account ID
    complaints = await Complaint.select(
        Complaint.all_columns(),
        Complaint.account_id.phone.as_alias("phone")
    ).where(Complaint.account_id == acc_uuid).order_by(Complaint.created_at, ascending=False).run()

    for item in complaints:
        # Convert path to Base64 for the frontend
        if item["proof_image"]:
            item["proof_image"] = await get_proof_base64_from_path(item["proof_image"])
        
        # Name lookup logic
        user_name = "Unknown User"
        # Use the found registration directly or re-fetch to be safe
        sp = await SeekerPersonal.objects().where(SeekerPersonal.registration == reg.id).first().run()
        si = await SeekerInstitutional.objects().where(SeekerInstitutional.registration == reg.id).first().run()
        hp = await HelperPersonal.objects().where(HelperPersonal.registration == reg.id).first().run()
        hi = await HelperInstitutional.objects().where(HelperInstitutional.registration == reg.id).first().run()
        
        profile = sp or si or hp or hi
        if profile: 
            user_name = getattr(profile, 'name', "Unknown User")
        
        item["user_name"] = user_name

    return complaints