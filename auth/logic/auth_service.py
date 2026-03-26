from datetime import datetime, timedelta

from asyncpg.exceptions import UniqueViolationError
from fastapi import HTTPException, status

from auth.logic.passwords import hash_password, verify_password
from auth.logic.tokens import create_access_token
from auth.structs.dtos import ChangePasswordIn, ForgotPasswordIn
from db.tables import Account, BlacklistedUser, LoginHistory, Registration


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
        await LoginHistory.insert(
            LoginHistory(
                account=account.id,
                registration=reg.id,
            )
        ).run()
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
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    report = (
        await Registration.select(
            # Registration.full_name,
            Registration.role,
            Account.phone,
        )
        .join(Account, Account.id == Registration.account)
        .where((Account.last_login < cutoff_date) | (Account.last_login is None))
        .run()
    )

    return report


async def check_user_activity_status(registration_id: str):
    # 1. Calculate the 3-month cutoff
    three_months_ago = datetime.now() - timedelta(days=90)

    # 2. Get User Details + Account info in one Join
    user_data = (
        await Registration.select(
            Registration.full_name, Registration.role, Account.phone, Account.last_login
        )
        .join(Account, Account.id == Registration.account)
        .where(Registration.id == registration_id)
        .first()
        .run()
    )

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Check if last_login is within the last 3 months
    last_login = user_data["last_login"]

    is_active_recently = False
    if last_login:
        # If last_login is newer (greater) than 3 months ago
        is_active_recently = last_login > three_months_ago

    return {
        "user_details": user_data,
        "is_active_in_last_3_months": is_active_recently,
        "last_login_date": last_login,
        "cutoff_date_used": three_months_ago,
    }
