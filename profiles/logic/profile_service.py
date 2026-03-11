# profiles/logic/profile_service.py
from __future__ import annotations
import base64
import os
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status, File
from db.tables import (
    Account,
    ProfilePicture,
    Registration,
    SeekerPersonal,
    SeekerInstitutional,
    HelperPersonal,
    HelperInstitutional,
)

from profiles.structs.dtos import ProfileOut, ProfileUpsertIn

_KIND_META = {
    "seeker_personal": {"side": "seeker", "capacity": "personal", "table": SeekerPersonal},
    "seeker_institutional": {"side": "seeker", "capacity": "institutional", "table": SeekerInstitutional},
    "helper_personal": {"side": "helper", "capacity": "personal", "table": HelperPersonal},
    "helper_institutional": {"side": "helper", "capacity": "institutional", "table": HelperInstitutional},
}


async def _get_registration_by_account_id(account_id: str) -> Registration:
    # Prefer .first() to avoid .get() throwing on "not found"
    reg = await Registration.objects().where(Registration.account == account_id).first()
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration not found for this account",
        )
    return reg


def _validate_payload_against_registration(*, reg: Registration, kind: str) -> None:
    meta = _KIND_META.get(kind)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown profile kind: {kind}",
        )

    # Capacity must match always
    if reg.capacity != meta["capacity"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Capacity mismatch: you are '{reg.capacity}', but payload is '{meta['capacity']}'",
        )

    # Role rules:
    # - seeker can only submit seeker_*
    # - helper can only submit helper_*
    # - both can submit either
    if reg.role != "both" and reg.role != meta["side"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role mismatch: you are '{reg.role}', but payload is for '{meta['side']}'",
        )

async def _find_phone_number_by_registration(account_id:str)->Account:
    find=await Account.objects().where(Account.id==account_id).first()
    if not find:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found for this account_id",
        )
    return find.phone

async def get_my_profile(*, account_id: str) -> ProfileOut:
    reg = await _get_registration_by_account_id(account_id)
    phoneno=await _find_phone_number_by_registration(reg.account)
    # Decide default kind for GET:
    # - if role is seeker => seeker_{capacity}
    # - if role is helper => helper_{capacity}
    # - if role is both   => seeker_{capacity} (default)
    side = reg.role if reg.role in ("seeker", "helper") else "seeker"
    kind = f"{side}_{reg.capacity}"

    meta = _KIND_META.get(kind)
    if not meta:
        # Should never happen unless role/capacity got new values
        return ProfileOut(
            registration_id=str(reg.id),
            role=reg.role,
            phone=phoneno,
            capacity=reg.capacity,
            profile_kind=None,
            profile={},
        )

    table = meta["table"]
    row = await table.objects().where(table.registration == reg.id).first()

    return ProfileOut(
        registration_id=str(reg.id),
        role=reg.role,
        phone=phoneno,
        capacity=reg.capacity,
        profile_kind=kind if row else None,
        profile=row.to_dict() if row else {},
    )


async def upsert_my_profile(*, account_id: str, payload: ProfileUpsertIn) -> ProfileOut:
    reg = await _get_registration_by_account_id(account_id)
    phoneno = await _find_phone_number_by_registration(reg.account)
    kind = payload.kind
    _validate_payload_against_registration(reg=reg, kind=kind)

    meta = _KIND_META[kind]
    table = meta["table"]

    # Upsert on (registration) which is unique for these profile tables
    existing = await table.objects().where(table.registration == reg.id).first()

    data = payload.model_dump(exclude={"kind"}, exclude_unset=True)

    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        await existing.save()
        row = existing
    else:
        row = table(registration=reg.id, **data)
        await row.save()

    return ProfileOut(
        registration_id=str(reg.id),
        role=reg.role,
        phone=phoneno,
        capacity=reg.capacity,
        profile_kind=kind,
        profile=row.to_dict(),
    )



UPLOAD_DIR = Path(r"C:\CompanyProject\gshbe\static\uploads\profile_pics")

async def save_profile_file_logic(reg_id: str, file: UploadFile, mode: str = "post"):
    # 1. Ensure directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 2. Extract and Validate Extension
    extension = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = [".jpg", ".jpeg", ".png"]

    if extension not in allowed_extensions:
        return {"status": "error", "message": "Only JPG and PNG files are allowed."}

    # 3. Determine the correct MIME type (Standardizing image/jpg to image/jpeg)
    # We use mimetypes.guess_type or a manual mapping for accuracy
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png"
    }
    final_mime = mime_map.get(extension, "image/jpeg")

    # 4. Fetch Account Info
    reg = await Registration.objects().get(Registration.id == reg_id).run()
    if not reg:
        return {"status": "error", "message": "User registration not found."}
    
    account_id = reg.account

    # 5. Check Database for Existing Record
    existing = await ProfilePicture.objects().where(
        ProfilePicture.account == account_id
    ).first().run()

    if mode == "post" and existing:
        return {"status": "error", "message": "Picture already exists. Use PATCH to update."}
    if mode == "patch" and not existing:
        return {"status": "error", "message": "No picture found. Use POST to upload first."}

    try:
        # 6. Generate unique filename to avoid collisions
        unique_name = f"profile_{account_id}_{uuid.uuid4().hex[:6]}{extension}"
        file_save_path = UPLOAD_DIR / unique_name

        # 7. Save binary content
        content = await file.read()
        with open(file_save_path, "wb") as f:
            f.write(content)

        relative_path = f"static/uploads/profile_pics/{unique_name}"

        # 8. Database Update/Insert
        if mode == "patch":
            # If replacing, you could delete the old file here
            await ProfilePicture.update({
                ProfilePicture.file_path: relative_path
            }).where(ProfilePicture.account == account_id).run()
        else:
            await ProfilePicture.insert(
                ProfilePicture(account=account_id, file_path=relative_path)
            ).run()

        return {
            "status": "success", 
            "path": str(file_save_path), 
            "filename": unique_name,
            "mime_type": final_mime 
        }

    except Exception as e:
        return {"status": "error", "message": f"Internal Save Error: {str(e)}"}




async def get_profile_base64_logic(reg_id: str):
    reg = await Registration.objects().get(Registration.id == reg_id).run()
    
    if not reg:
        return None


    record = await ProfilePicture.objects().get(
        ProfilePicture.account == reg.account
    ).run()

    if not record or not record.file_path:
        return None
    

    full_path = Path(r"C:\CompanyProject\gshbe") / record.file_path

    if not os.path.exists(full_path):
        print(f"File not found on disk: {full_path}")
        return None

    try:
        with open(full_path, "rb") as image_file:
            binary_data = image_file.read()
            base64_encoded = base64.b64encode(binary_data).decode('utf-8')
            
            ext = os.path.splitext(record.file_path)[1].lower().replace(".", "")
            mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
            
            return f"data:{mime_type};base64,{base64_encoded}"
    except Exception as e:
        print(f"Error reading profile image file: {e}")
        return None