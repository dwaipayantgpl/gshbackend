# C:\CompanyProject\gshbe\complaint\logic\service.py
import base64
import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from db.tables import (
    Complaint,
    HelperInstitutional,
    HelperPersonal,
    Registration,
    SeekerInstitutional,
    SeekerPersonal,
    ServiceBooking,
)

# Match your existing static structure
COMPLAINT_UPLOAD_DIR = Path(r"C:\CompanyProject\gshbe\static\uploads\complaints_proof")


async def save_complaint_proof_logic(account_id: str, file: UploadFile):
    os.makedirs(COMPLAINT_UPLOAD_DIR, exist_ok=True)

    extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".jpg", ".jpeg", ".png", ".pdf"]

    if extension not in allowed_extensions:
        return {
            "status": "error",
            "message": "Only JPG, PNG, and PDF files are allowed.",
        }

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
    if not relative_path:
        return None
    full_path = Path(r"C:\CompanyProject\gshbe") / relative_path

    if not os.path.exists(full_path):
        return None

    try:
        with open(full_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            ext = os.path.splitext(relative_path)[1].lower().replace(".", "")
            mime = (
                "application/pdf"
                if ext == "pdf"
                else f"image/{ext if ext != 'jpg' else 'jpeg'}"
            )
            return f"data:{mime};base64,{encoded}"
    except:
        return None


async def get_all_complaints():
    complaints = (
        await Complaint.select(
            Complaint.all_columns(), Complaint.account_id.phone.as_alias("phone")
        )
        .order_by(Complaint.created_at, ascending=False)
        .run()
    )

    for item in complaints:
        # --- Base64 Logic ---
        if item["proof_image"]:
            item["proof_image"] = await get_proof_base64_from_path(item["proof_image"])

        # 1. IDENTIFY THE REPORTER (The person who clicked 'Submit')
        reporter_name = "Unknown User"
        reporter_reg = (
            await Registration.objects()
            .where(Registration.account == item["account_id"])
            .first()
            .run()
        )

        if reporter_reg:
            # Check all 4 tables for the reporter's name
            sp = (
                await SeekerPersonal.objects()
                .where(SeekerPersonal.registration == reporter_reg.id)
                .first()
                .run()
            )
            si = (
                await SeekerInstitutional.objects()
                .where(SeekerInstitutional.registration == reporter_reg.id)
                .first()
                .run()
            )
            hp = (
                await HelperPersonal.objects()
                .where(HelperPersonal.registration == reporter_reg.id)
                .first()
                .run()
            )
            hi = (
                await HelperInstitutional.objects()
                .where(HelperInstitutional.registration == reporter_reg.id)
                .first()
                .run()
            )
            profile = sp or si or hp or hi
            if profile:
                reporter_name = getattr(profile, "name", "Unknown User")

        item["user_name"] = reporter_name  # This is the "Customer Name" in your UI
        item["registration_id"] = str(reporter_reg.id) if reporter_reg else None

        # 2. IDENTIFY THE "OTHER PARTY" (The Accused)
        item["helper_id"] = None
        item["helper_name"] = "N/A"
        item["helper_phone"] = "N/A"

        if item["booking_id"] and reporter_reg:
            booking = (
                await ServiceBooking.objects()
                .where(ServiceBooking.id == item["booking_id"])
                .first()
                .run()
            )

            if booking:
                # Determine who the complaint is AGAINST
                # If reporter is the seeker, accused is the helper
                # If reporter is the helper, accused is the seeker
                is_reporter_seeker = str(reporter_reg.id) == str(booking.seeker)
                accused_reg_id = (
                    booking.helper if is_reporter_seeker else booking.seeker
                )

                item["helper_id"] = str(accused_reg_id)

                # Fetch Accused Account/Phone
                acc_reg = (
                    await Registration.objects()
                    .where(Registration.id == accused_reg_id)
                    .prefetch(Registration.account)
                    .first()
                    .run()
                )
                if acc_reg and acc_reg.account:
                    item["helper_phone"] = acc_reg.account.phone

                # Fetch Accused Name
                # We check seeker tables if the helper complained, and vice-versa
                a_sp = (
                    await SeekerPersonal.objects()
                    .where(SeekerPersonal.registration == accused_reg_id)
                    .first()
                    .run()
                )
                a_si = (
                    await SeekerInstitutional.objects()
                    .where(SeekerInstitutional.registration == accused_reg_id)
                    .first()
                    .run()
                )
                a_hp = (
                    await HelperPersonal.objects()
                    .where(HelperPersonal.registration == accused_reg_id)
                    .first()
                    .run()
                )
                a_hi = (
                    await HelperInstitutional.objects()
                    .where(HelperInstitutional.registration == accused_reg_id)
                    .first()
                    .run()
                )

                accused_profile = a_sp or a_si or a_hp or a_hi
                if accused_profile:
                    item["helper_name"] = getattr(accused_profile, "name", "Unknown")

    return complaints


async def update_complaint_status(complaint_id: str, status: str):
    complaint = await Complaint.objects().get(Complaint.id == complaint_id).run()
    if not complaint:
        return {"error": "Not found"}
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
    complaints = (
        await Complaint.select(
            Complaint.all_columns(), Complaint.account_id.phone.as_alias("phone")
        )
        .where(Complaint.account_id == acc_uuid)
        .order_by(Complaint.created_at, ascending=False)
        .run()
    )

    for item in complaints:
        # Convert path to Base64 for the frontend
        if item["proof_image"]:
            item["proof_image"] = await get_proof_base64_from_path(item["proof_image"])

        # Name lookup logic
        user_name = "Unknown User"
        # Use the found registration directly or re-fetch to be safe
        sp = (
            await SeekerPersonal.objects()
            .where(SeekerPersonal.registration == reg.id)
            .first()
            .run()
        )
        si = (
            await SeekerInstitutional.objects()
            .where(SeekerInstitutional.registration == reg.id)
            .first()
            .run()
        )
        hp = (
            await HelperPersonal.objects()
            .where(HelperPersonal.registration == reg.id)
            .first()
            .run()
        )
        hi = (
            await HelperInstitutional.objects()
            .where(HelperInstitutional.registration == reg.id)
            .first()
            .run()
        )

        profile = sp or si or hp or hi
        if profile:
            user_name = getattr(profile, "name", "Unknown User")

        item["user_name"] = user_name

    return complaints


async def delete_resolved_complaint(complaint_id: str):
    complaint = (
        await Complaint.objects().where(Complaint.id == complaint_id).first().run()
    )

    if not complaint:
        return {"status": "error", "message": "Complaint not found in records."}

    if complaint.status != "resolved":
        return {
            "status": "error",
            "message": f"Cannot delete. Complaint status is '{complaint.status}'. Only 'resolved' items can be removed.",
        }

    await Complaint.delete().where(Complaint.id == complaint_id).run()

    return {"status": "success", "message": "Complaint has been permanently removed."}
