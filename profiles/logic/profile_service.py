# profiles/logic/profile_service.py
from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from db.tables import (
    Account,
    HelperInstitutional,
    HelperPersonal,
    ProfilePicture,
    Registration,
    SeekerInstitutional,
    SeekerPersonal,
)
from profiles.structs.dtos import ProfileOut, ProfileUpsertIn

_KIND_META = {
    "seeker_personal": {
        "side": "seeker",
        "capacity": "personal",
        "table": SeekerPersonal,
    },
    "seeker_institutional": {
        "side": "seeker",
        "capacity": "institutional",
        "table": SeekerInstitutional,
    },
    "helper_personal": {
        "side": "helper",
        "capacity": "personal",
        "table": HelperPersonal,
    },
    "helper_institutional": {
        "side": "helper",
        "capacity": "institutional",
        "table": HelperInstitutional,
    },
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


async def _find_phone_number_by_registration(account_id: str) -> Account:
    find = await Account.objects().where(Account.id == account_id).first()
    if not find:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found for this account_id",
        )
    return find.phone


async def get_my_profile(*, account_id: str) -> ProfileOut:
    reg = await _get_registration_by_account_id(account_id)
    phoneno = await _find_phone_number_by_registration(reg.account)
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
            account_id=str(reg.account),
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
        account_id=str(reg.account),
        registration_id=str(reg.id),
        role=reg.role,
        phone=phoneno,
        capacity=reg.capacity,
        profile_kind=kind if row else None,
        profile=row.to_dict() if row else {},
    )


async def upsert_my_profile(*, account_id: str, payload: ProfileUpsertIn) -> ProfileOut:
    # 1. Get current registration and phone
    reg = await _get_registration_by_account_id(account_id)
    
    # Securely fetch account to get the phone number
    account_row = await Account.objects().where(Account.id == account_id).first()
    phoneno = account_row.phone if account_row else "N/A"
    
    kind = payload.kind
    _validate_payload_against_registration(reg=reg, kind=kind)

    meta = _KIND_META[kind]
    table = meta["table"]

    # 2. Extract update data (excluding the discriminator 'kind')
    # exclude_unset=True is key: it means we only update fields the frontend actually sent
    update_data = payload.model_dump(exclude={"kind"}, exclude_unset=True)

    # 3. Check if profile exists
    existing = await table.objects().where(table.registration == reg.id).first()

    if existing:
        # Update only the fields provided in the payload
        for key, value in update_data.items():
            setattr(existing, key, value)
        await existing.save().run()
        row = existing
    else:
        # Create new profile record
        row = table(registration=reg.id, **update_data)
        await row.save().run()

    # 4. Return unified profile response
    return ProfileOut(
        account_id=str(account_id),
        registration_id=str(reg.id),
        role=reg.role,
        phone=phoneno,
        capacity=reg.capacity,
        profile_kind=kind,
        profile=row.to_dict(),
    )


# 🔒 SECURITY: Fields that the user is NOT allowed to change via this API
PROTECTED_FIELDS = {
    "id", "registration", "account", "phone", 
    "avg_rating", "rating_count", "created_at"
}

async def patch_my_profile_smart(*, account_id: str, payload_data: dict) -> ProfileOut:
    """
    Smart Patch: Automatically determines the correct profile table 
    based on the user's Registration record and applies partial updates.
    """
    # 1. Look up the registration record to find role and capacity
    reg = await Registration.objects().where(Registration.account == account_id).first().run()
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Registration record not found for this account."
        )

    # 2. Determine the "Kind" (e.g., helper_personal)
    # Default to seeker if role is 'both' or 'admin' for profile purposes
    side = reg.role if reg.role in ("seeker", "helper") else "seeker"
    kind = f"{side}_{reg.capacity}"

    meta = _KIND_META.get(kind)
    if not meta:
        raise HTTPException(status_code=500, detail="Invalid profile configuration.")
    
    table = meta["table"]

    # 3. Fetch current account for the phone number (Safety check)
    account_row = await Account.objects().where(Account.id == account_id).first().run()
    phoneno = account_row.phone if account_row else "N/A"

    # 4. Check if a profile record already exists for this registration
    existing = await table.objects().where(table.registration == reg.id).first().run()

    if existing:
        # --- PARTIAL UPDATE ---
        for key, value in payload_data.items():
            # Only update if the field exists in DB and is NOT protected
            if hasattr(existing, key) and key not in PROTECTED_FIELDS:
                setattr(existing, key, value)
        
        await existing.save().run()
        row = existing
    else:
        # --- FIRST TIME CREATION ---
        # Strip out any protected fields sent in the initial payload
        clean_data = {k: v for k, v in payload_data.items() if k not in PROTECTED_FIELDS}
        row = table(registration=reg.id, **clean_data)
        await row.save().run()

    # 5. Return the unified response
    return ProfileOut(
        account_id=str(account_id),
        registration_id=str(reg.id),
        role=reg.role,
        phone=phoneno,
        capacity=reg.capacity,
        profile_kind=kind,
        profile=row.to_dict()
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
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    final_mime = mime_map.get(extension, "image/jpeg")

    # 4. Fetch Account Info
    reg = await Registration.objects().get(Registration.id == reg_id).run()
    if not reg:
        return {"status": "error", "message": "User registration not found."}

    account_id = reg.account

    # 5. Check Database for Existing Record
    existing = (
        await ProfilePicture.objects()
        .where(ProfilePicture.account == account_id)
        .first()
        .run()
    )

    if mode == "post" and existing:
        return {
            "status": "error",
            "message": "Picture already exists. Use PATCH to update.",
        }
    if mode == "patch" and not existing:
        return {
            "status": "error",
            "message": "No picture found. Use POST to upload first.",
        }

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
            await (
                ProfilePicture.update({ProfilePicture.file_path: relative_path})
                .where(ProfilePicture.account == account_id)
                .run()
            )
        else:
            await ProfilePicture.insert(
                ProfilePicture(account=account_id, file_path=relative_path)
            ).run()

        return {
            "status": "success",
            "path": str(file_save_path),
            "filename": unique_name,
            "mime_type": final_mime,
        }

    except Exception as e:
        return {"status": "error", "message": f"Internal Save Error: {str(e)}"}


async def get_profile_base64_logic(reg_id: str):
    reg = await Registration.objects().get(Registration.id == reg_id).run()

    if not reg:
        return None

    record = (
        await ProfilePicture.objects().get(ProfilePicture.account == reg.account).run()
    )

    if not record or not record.file_path:
        return None

    full_path = Path(r"C:\CompanyProject\gshbe") / record.file_path

    if not os.path.exists(full_path):
        print(f"File not found on disk: {full_path}")
        return None

    try:
        with open(full_path, "rb") as image_file:
            binary_data = image_file.read()
            base64_encoded = base64.b64encode(binary_data).decode("utf-8")

            ext = os.path.splitext(record.file_path)[1].lower().replace(".", "")
            mime_type = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"

            return f"data:{mime_type};base64,{base64_encoded}"
    except Exception as e:
        print(f"Error reading profile image file: {e}")
        return None
