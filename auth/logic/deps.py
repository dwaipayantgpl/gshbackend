# app/auth/logic/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from auth.logic.tokens import decode_access_token
from db.tables import Registration

bearer = HTTPBearer(auto_error=True)

def get_current_account_id(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    try:
        payload = decode_access_token(creds.credentials)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return str(sub)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

# add this 
async def get_current_user_role(account_id: str = Depends(get_current_account_id)) -> str:
    reg = await Registration.objects().where(Registration.account == account_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg.role

async def get_current_registration(account_id: str = Depends(get_current_account_id)):
    reg = await Registration.objects().where(Registration.account == account_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg  # This returns the whole object, not just a string

async def require_admin(role: str = Depends(get_current_user_role)):
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin access required"
        )
    return role