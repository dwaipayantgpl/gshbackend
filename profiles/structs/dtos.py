# profiles/structs/dtos.py
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# ----------------------------
# Request payloads (Swagger oneOf)
# ----------------------------

class SeekerPersonalUpsert(BaseModel):
    kind: Literal["seeker_personal"] = "seeker_personal"
    name: str
    city: str
    area: str


class SeekerInstitutionalUpsert(BaseModel):
    kind: Literal["seeker_institutional"] = "seeker_institutional"
    name: str
    city: str
    area: str
    institution_type: Optional[str] = None
    phone: Optional[str] = None


class HelperPersonalUpsert(BaseModel):
    kind: Literal["helper_personal"] = "helper_personal"
    name: str
    city: str
    area: str
    age: Optional[int] = None
    faith: Optional[str] = None
    languages: Optional[str] = None
    phone: Optional[str] = None
    years_of_experience: Optional[int] = None


class HelperInstitutionalUpsert(BaseModel):
    kind: Literal["helper_institutional"] = "helper_institutional"
    name: str
    city: str
    address: str
    phone: Optional[str] = None


# This is what you use in the endpoint signature:
# async def upsert_profile(payload: ProfileUpsertIn, ...)
ProfileUpsertIn = Annotated[
    Union[
        SeekerPersonalUpsert,
        SeekerInstitutionalUpsert,
        HelperPersonalUpsert,
        HelperInstitutionalUpsert,
    ],
    Field(discriminator="kind"),
]


# ----------------------------
# Response models
# ----------------------------

class ProfileOut(BaseModel):
    registration_id: str
    role: str
    phone:str
    capacity: str
    profile_kind: Optional[str] = None
    profile: dict = Field(default_factory=dict)
