from pydantic import BaseModel, Field, model_validator

from auth.structs.enums import Capacity, Role


class SignUpIn(BaseModel):
    phone: str = Field(..., examples=["+919876543210"], description="E.164 preferred")
    password: str = Field(..., min_length=8, examples=["CorrectHorseBatteryStaple"])
    role: Role
    capacity: Capacity


class SignInIn(BaseModel):
    phone: str = Field(..., examples=["+919876543210"])
    password: str = Field(..., min_length=8, examples=["CorrectHorseBatteryStaple"])


class TokenOut(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer")


class SignUpOut(TokenOut):
    kind: str | None = Field(
        None,
        description="Default profile kind for this account (e.g. seeker_personal).",
    )


class SignInOut(TokenOut):
    type: str | None = Field(
        None,
        description="Active user side after signin: seeker or helper. None for admin.",
        examples=["seeker"],
    )


class AccountOut(BaseModel):
    id: str
    phone: str
    is_active: bool


class MeOut(BaseModel):
    accountId: str
    role: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        return self


class ForgotPasswordIn(BaseModel):
    phone: str
    new_password: str = Field(min_length=8)
    confirm_password: str
