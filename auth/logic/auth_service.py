from datetime import datetime, timedelta, timezone

from asyncpg.exceptions import UniqueViolationError
from fastapi import HTTPException, status

from auth.logic.passwords import hash_password, verify_password
from auth.logic.tokens import create_access_token
from auth.structs.dtos import ChangePasswordIn, ForgotPasswordIn
from db.tables import (
    Account,
    BlacklistedUser,
    HelperInstitutional,
    HelperPersonal,
    LoginHistory,
    Registration,
    SeekerInstitutional,
    SeekerPersonal,
)


async def signup(*, phone: str, password: str, role: str, capacity: str) -> dict:
    # Optional fast-path check (keeps error message clean)
    existing = await Account.objects().where(Account.phone == phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Phone already registered")

    is_banned = (
        await BlacklistedUser.objects().where(BlacklistedUser.phone == phone).first()
    )
    if is_banned:
        raise HTTPException(
            status_code=403,
            detail="This phone number is permanently banned from this platform.",
        )

    try:
        account = Account(
            phone=phone, password_hash=hash_password(password), is_active=True
        )
        await account.save()
    except UniqueViolationError:
        raise HTTPException(status_code=409, detail="Phone already registered")

    kind = None

    if role != "admin":
        reg = Registration(account=account.id, role=role, capacity=capacity)
        await reg.save()

        # Mirror profiles.get_my_profile default logic:
        # - seeker -> seeker_{capacity}
        # - helper -> helper_{capacity}
        # - both   -> seeker_{capacity} (default)
        side = role if role in ("seeker", "helper") else "seeker"
        kind = f"{side}_{capacity}"

    token = create_access_token(sub=str(account.id))
    return {"account": account, "access_token": token, "kind": kind}


async def signin(*, phone: str, password: str) -> dict:
    account = await Account.objects().where(Account.phone == phone).first()
    is_banned = (
        await BlacklistedUser.objects().where(BlacklistedUser.phone == phone).first()
    )
    if is_banned:
        raise HTTPException(
            status_code=403,
            detail="This phone number is permanently banned from this platform.",
        )
    if not account or not verify_password(password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    reg = await Registration.objects().where(Registration.account == account.id).first()

    if reg:
        await (
            LoginHistory(
                account=account.id, registration=reg.id, login_at=datetime.now()
            )
            .save()
            .run()
        )
    user_type = None
    if reg:
        if reg.role in ("seeker", "helper"):
            user_type = reg.role
        elif reg.role == "both":
            user_type = "seeker"  # default side
        elif reg.role == "admin":
            user_type = "admin"

    token = create_access_token(sub=str(account.id))

    return {
        "access_token": token,
        "type": user_type,
    }


async def get_me(*, account_id: str) -> dict:
    account = await Account.objects().where(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")

    reg = await Registration.objects().where(Registration.account == account_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    return {"accountId": str(account.id), "role": reg.role}


async def update_password(account_id: str, payload: ChangePasswordIn):
    # 1. Fetch account from DB
    account = await Account.objects().where(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # 2. Verify Old Password
    if not verify_password(payload.old_password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password (old password) is incorrect",
        )

    # 3. Hash and Update New Password
    account.password_hash = hash_password(payload.new_password)
    await account.save()

    return {"message": "Password updated successfully"}


async def reset_password(payload: ForgotPasswordIn):
    # 1. Check if passwords match
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # 2. Find the account by phone
    account = await Account.objects().where(Account.phone == payload.phone).first()

    if not account:
        raise HTTPException(
            status_code=404, detail="No account found with this phone number"
        )

    if verify_password(payload.new_password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The new password cannot be the same as your current password. Please choose a different one.",
        )
    # 3. Update with new hashed password
    account.password_hash = hash_password(payload.new_password)
    await account.save()

    return {"message": f"Password for {payload.phone} has been reset successfully"}


async def get_inactive_users_report(months: int = 3):
    # 1. Setup Timezone-aware Cutoff
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

    # 2. Get all registrations and their account info
    all_regs = await Registration.objects().prefetch(Registration.account).run()

    report_data = []

    for reg in all_regs:
        # 3. Get the absolute LATEST login for this specific registration
        latest_login = (
            await LoginHistory.objects()
            .where(LoginHistory.registration == reg.id)
            .order_by(LoginHistory.login_at, ascending=False)
            .first()
            .run()
        )

        last_login_at = latest_login.login_at if latest_login else None

        # 4. Filter Logic
        is_inactive = False
        if last_login_at is None or last_login_at < cutoff_date:
            is_inactive = True

        if is_inactive:
            report_data.append(
                {
                    "account_id": str(reg.account.id),  # <-- Added this line
                    "registration_id": str(reg.id),
                    "phone": reg.account.phone,
                    "role": reg.role,
                    "capacity": reg.capacity,
                    "last_login": last_login_at,
                    "status": "Never Logged In"
                    if last_login_at is None
                    else "Inactive",
                }
            )

    return report_data


async def check_user_activity_status(registration_id: str):
    # 1. FIX: Make the cutoff date timezone-aware (UTC)
    three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)

    # 2. Get Core Registration & Account info
    reg_data = (
        await Registration.objects()
        .where(Registration.id == registration_id)
        .prefetch(Registration.account)
        .first()
        .run()
    )

    if not reg_data:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Fetch the LATEST login from LoginHistory
    latest_login_record = (
        await LoginHistory.objects()
        .where(LoginHistory.registration == registration_id)
        .order_by(LoginHistory.login_at, ascending=False)
        .first()
        .run()
    )

    last_login = latest_login_record.login_at if latest_login_record else None

    # 4. Profile lookup logic (unchanged)
    role = reg_data.role
    capacity = reg_data.capacity
    kind = f"{role}_{capacity}"
    profile_map = {
        "seeker_personal": SeekerPersonal,
        "seeker_institutional": SeekerInstitutional,
        "helper_personal": HelperPersonal,
        "helper_institutional": HelperInstitutional,
    }
    profile_table = profile_map.get(kind)
    user_name = "Unknown"

    if profile_table:
        profile = (
            await profile_table.objects()
            .where(profile_table.registration == registration_id)
            .first()
            .run()
        )
        if profile:
            user_name = profile.name

    # 5. Logic check (This is where the error was happening)
    is_active_recently = False
    if last_login:
        # Both sides are now timezone-aware, so they can be compared
        is_active_recently = last_login > three_months_ago

    return {
        "user_details": {
            "name": user_name,
            "role": role,
            "phone": reg_data.account.phone,
            "last_login": last_login,
        },
        "is_active_in_last_3_months": is_active_recently,
        "last_login_date": last_login,
        "cutoff_date_used": three_months_ago,
    }
