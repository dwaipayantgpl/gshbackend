# app/auth/endpoints/router.py
from fastapi import APIRouter, status, Depends
from auth.logic import auth_service
from auth.structs.dtos import ChangePasswordIn, ForgotPasswordIn, SignUpIn, SignInIn, SignInOut, SignUpOut
from auth.logic.auth_service import signup, signin
from auth.structs.dtos import MeOut
from auth.logic.deps import get_current_account_id
from auth.logic.auth_service import get_me
router = APIRouter()

@router.post(
    "/signup",
    summary="Sign up with phone + password",
    description="Creates Account + Registration. Returns a JWT access token.",
    response_model=SignUpOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Created"},
        409: {"description": "Phone already registered"},
    },
)
async def signup_endpoint(payload: SignUpIn):
    result = await signup(
        phone=payload.phone,
        password=payload.password,
        role=payload.role.value,
        capacity=payload.capacity.value,
    )
    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "kind": result["kind"],
    }

@router.post(
    "/signin",
    summary="Sign in with phone + password",
    description="Verifies password and returns a JWT access token.",
    response_model=SignInOut,
    responses={
        200: {"description": "OK"},
        401: {"description": "Invalid phone or password"},
        403: {"description": "Account disabled"},
    },
)
async def signin_endpoint(payload: SignInIn):
    token = await signin(phone=payload.phone, password=payload.password)
    return {
        "access_token": token["access_token"],
        "token_type": "bearer",
        "type": token.get("type"),
    }

@router.get(
    "/me",
    summary="Get current user identity",
    description="Requires a Bearer token. Returns accountId + role.",
    response_model=MeOut,
    responses={
        200: {"description": "OK"},
        401: {"description": "Invalid or expired token"},
        404: {"description": "Registration not found"},
    },
)
async def me_endpoint(account_id: str = Depends(get_current_account_id)):
    return await get_me(account_id=account_id)

#Change password
@router.post("/change-password", summary="Update user password")
async def change_password(
    payload: ChangePasswordIn,
    account_id: str = Depends(get_current_account_id) # Ensures user is logged in
):
    return await auth_service.update_password(account_id, payload)

#for get password
@router.post("/forgot-password", summary="Reset password using only phone (No OTP)")
async def forgot_password(payload: ForgotPasswordIn):
    return await auth_service.reset_password(payload)