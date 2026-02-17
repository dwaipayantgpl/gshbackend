from fastapi import HTTPException, status
from asyncpg.exceptions import UniqueViolationError

from db.tables import Account, Registration
from auth.logic.passwords import hash_password, verify_password
from auth.logic.tokens import create_access_token


async def signup(*, phone: str, password: str, role: str, capacity: str) -> dict:
    # Optional fast-path check (keeps error message clean)
    existing = await Account.objects().where(Account.phone == phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Phone already registered")

    try:
        account = Account(phone=phone, password_hash=hash_password(password), is_active=True)
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
    if not account or not verify_password(password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    reg = await Registration.objects().where(Registration.account == account.id).first()

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
