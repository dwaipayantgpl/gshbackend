from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from auth.logic.deps import (
    get_current_account_id,
    get_current_registration,
)
from chat.logic import service
from db.tables import Registration
from helper.endpoints import router
from helper.logic import service
from helper.logic.service import (
    create_my_experience,
    delete_my_experience,
    get_my_preference,
    get_preference_by_registration_id,
    list_experience_by_registration_id,
    list_my_experience,
    update_my_experience,
    upsert_my_preference,
)
from helper.structs.dtos import (
    DeleteOut,
    HelperExperienceIn,
    HelperExperienceOut,
    HelperPreferenceOut,
    HelperPreferenceUpsertIn,
)

router = APIRouter(tags=["helper"])


# ----------------------------
# Public (ANYONE)
# ----------------------------


@router.get(
    "/{registration_id}/preferences",
    response_model=HelperPreferenceOut,
    status_code=status.HTTP_200_OK,
    summary="Get helper preference (public)",
    description=(
        "Public endpoint.\n\n"
        "Returns the helper's preference for the given `registration_id`.\n"
        "If the helper has never set preferences, returns an empty-but-stable object.\n\n"
        "Notes:\n"
        "- This endpoint does not require authentication.\n"
        "- `registration_id` is the helper's Registration.id.\n"
    ),
    responses={
        200: {
            "description": "Preference returned (stable shape)",
            "content": {
                "application/json": {
                    "examples": {
                        "filled": {
                            "summary": "Preference set",
                            "value": {
                                "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                                "city": "Kolkata",
                                "area": "Salt Lake",
                                "job_type": "part_time",
                                "preferred_service_ids": [
                                    "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1"
                                ],
                            },
                        },
                        "empty": {
                            "summary": "Preference not set yet",
                            "value": {
                                "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                                "city": None,
                                "area": None,
                                "job_type": None,
                                "preferred_service_ids": [],
                            },
                        },
                    }
                }
            },
        },
    },
)
async def get_public_preference(registration_id: str):
    return await get_preference_by_registration_id(registration_id=registration_id)


@router.get(
    "/{registration_id}/experience",
    response_model=list[HelperExperienceOut],
    status_code=status.HTTP_200_OK,
    summary="List helper experience (public)",
    description=(
        "Public endpoint.\n\n"
        "Lists all experience items belonging to the helper identified by `registration_id`.\n\n"
        "Notes:\n"
        "- This endpoint does not require authentication.\n"
        "- `registration_id` is the helper's Registration.id.\n"
    ),
    responses={
        200: {
            "description": "Experience list returned (may be empty)",
            "content": {
                "application/json": {
                    "examples": {
                        "non_empty": {
                            "summary": "Experience list",
                            "value": [
                                {
                                    "id": "3b91f6ad-7f6a-4c0c-8f5b-76ed17bd7c3a",
                                    "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                                    "year_from": 2019,
                                    "year_to": 2024,
                                    "service_id": "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1",
                                    "city": "Kolkata",
                                    "area": "Behala",
                                    "description": "Worked as a home nurse for elderly patients.",
                                }
                            ],
                        },
                        "empty": {
                            "summary": "No experiences yet",
                            "value": [],
                        },
                    }
                }
            },
        },
    },
)
async def get_public_experience(registration_id: str):
    return await list_experience_by_registration_id(registration_id=registration_id)


# ----------------------------
# Owner-only
# ----------------------------


@router.get(
    "/preferences/me",
    response_model=HelperPreferenceOut,
    status_code=status.HTTP_200_OK,
    summary="Get my helper preference (owner)",
    description=(
        "Owner-only endpoint.\n\n"
        "Returns the authenticated user's helper preference.\n"
        "If the helper has never set preferences, returns an empty-but-stable object.\n\n"
        "Access:\n"
        "- role=helper or role=both\n"
    ),
    responses={
        200: {
            "description": "Preference returned (stable shape)",
            "content": {
                "application/json": {
                    "example": {
                        "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                        "city": "Kolkata",
                        "area": "Salt Lake",
                        "job_type": "part_time",
                        "preferred_service_ids": [
                            "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1"
                        ],
                    }
                }
            },
        },
        403: {"description": "Only helpers can access this resource"},
        404: {"description": "Registration not found"},
    },
)
async def get_preference_me(account_id: str = Depends(get_current_account_id)):
    return await get_my_preference(account_id=account_id)


@router.put(
    "/preferences/me",
    response_model=HelperPreferenceOut,
    status_code=status.HTTP_200_OK,
    summary="Upsert my helper preference (owner)",
    description=(
        "Owner-only endpoint.\n\n"
        "Upserts helper preference for the authenticated helper.\n\n"
        "Semantics:\n"
        "- Patch-ish update: omitted fields remain unchanged.\n"
        "- `preferred_service_ids` replaces the entire set (deterministic).\n\n"
        "Validation:\n"
        "- Any provided service IDs must exist.\n\n"
        "Access:\n"
        "- role=helper or role=both\n"
    ),
    responses={
        200: {
            "description": "Preference upserted",
            "content": {
                "application/json": {
                    "examples": {
                        "updated": {
                            "summary": "Updated preference",
                            "value": {
                                "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                                "city": "Kolkata",
                                "area": "Salt Lake",
                                "job_type": "part_time",
                                "preferred_service_ids": [
                                    "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1"
                                ],
                            },
                        },
                        "partial": {
                            "summary": "Partial update (city only)",
                            "value": {
                                "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                                "city": "Kolkata",
                                "area": "Salt Lake",
                                "job_type": "part_time",
                                "preferred_service_ids": [],
                            },
                        },
                    }
                }
            },
        },
        400: {"description": "Invalid service_ids"},
        403: {"description": "Only helpers can access this resource"},
        404: {"description": "Registration not found"},
    },
)
async def put_preference_me(
    payload: HelperPreferenceUpsertIn,
    account_id: str = Depends(get_current_account_id),
):
    return await upsert_my_preference(
        account_id=account_id,
        payload=payload.model_dump(exclude_unset=True),
    )


@router.get(
    "/experience/me",
    response_model=list[HelperExperienceOut],
    status_code=status.HTTP_200_OK,
    summary="List my experience (owner)",
    description=(
        "Owner-only endpoint.\n\n"
        "Lists all experience items for the authenticated helper.\n\n"
        "Access:\n"
        "- role=helper or role=both\n"
    ),
    responses={
        200: {
            "description": "Experience list returned (may be empty)",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "3b91f6ad-7f6a-4c0c-8f5b-76ed17bd7c3a",
                            "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                            "year_from": 2019,
                            "year_to": 2024,
                            "service_id": "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1",
                            "city": "Kolkata",
                            "area": "Behala",
                            "description": "Worked as a home nurse for elderly patients.",
                        }
                    ]
                }
            },
        },
        403: {"description": "Only helpers can access this resource"},
        404: {"description": "Registration not found"},
    },
)
async def get_experience_me(account_id: str = Depends(get_current_account_id)):
    return await list_my_experience(account_id=account_id)


@router.post(
    "/experience/me",
    response_model=HelperExperienceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an experience item (owner)",
    description=(
        "Owner-only endpoint.\n\n"
        "Creates a new experience record for the authenticated helper.\n\n"
        "Validation:\n"
        "- If both years are provided, `year_from` must be <= `year_to`.\n"
        "- If `service_id` is provided, it must exist.\n\n"
        "Access:\n"
        "- role=helper or role=both\n"
    ),
    responses={
        201: {
            "description": "Experience created",
            "content": {
                "application/json": {
                    "example": {
                        "id": "3b91f6ad-7f6a-4c0c-8f5b-76ed17bd7c3a",
                        "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                        "year_from": 2019,
                        "year_to": 2024,
                        "service_id": "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1",
                        "city": "Kolkata",
                        "area": "Behala",
                        "description": "Worked as a home nurse for elderly patients.",
                    }
                }
            },
        },
        400: {"description": "Invalid years or invalid service_id"},
        403: {"description": "Only helpers can access this resource"},
        404: {"description": "Registration not found"},
    },
)
async def post_experience_me(
    payload: HelperExperienceIn,
    account_id: str = Depends(get_current_account_id),
):
    return await create_my_experience(
        account_id=account_id,
        payload=payload.model_dump(exclude_unset=True),
    )


@router.put(
    "/experience/me/{experience_id}",
    response_model=HelperExperienceOut,
    status_code=status.HTTP_200_OK,
    summary="Update an experience item (owner)",
    description=(
        "Owner-only endpoint.\n\n"
        "Updates an existing experience record.\n\n"
        "Semantics:\n"
        "- Patch-style update: omitted fields remain unchanged.\n\n"
        "Validation:\n"
        "- If both years are provided (post-merge), `year_from` must be <= `year_to`.\n"
        "- If `service_id` is provided, it must exist.\n\n"
        "Access:\n"
        "- role=helper or role=both\n"
    ),
    responses={
        200: {
            "description": "Experience updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": "3b91f6ad-7f6a-4c0c-8f5b-76ed17bd7c3a",
                        "registration_id": "0f1d3f8a-2db9-4d4a-8b31-7e2b3b8c4c8e",
                        "year_from": 2019,
                        "year_to": 2024,
                        "service_id": "b2b9c9c2-9d0b-4c6f-9e5b-2d4cefd1d5c1",
                        "city": "Kolkata",
                        "area": "Behala",
                        "description": "Worked as a home nurse for elderly patients.",
                    }
                }
            },
        },
        400: {"description": "Invalid years or invalid service_id"},
        403: {"description": "Only helpers can access this resource"},
        404: {"description": "Experience not found or registration not found"},
    },
)
async def put_experience_me(
    experience_id: str,
    payload: HelperExperienceIn,
    account_id: str = Depends(get_current_account_id),
):
    return await update_my_experience(
        account_id=account_id,
        experience_id=experience_id,
        payload=payload.model_dump(exclude_unset=True),
    )


@router.delete(
    "/experience/me/{experience_id}",
    response_model=DeleteOut,
    status_code=status.HTTP_200_OK,
    summary="Delete an experience item (owner)",
    description=(
        "Owner-only endpoint.\n\n"
        "Deletes an experience item owned by the authenticated helper.\n\n"
        "Access:\n"
        "- role=helper or role=both\n"
    ),
    responses={
        200: {
            "description": "Deleted",
            "content": {"application/json": {"example": {"deleted": True}}},
        },
        403: {"description": "Only helpers can access this resource"},
        404: {"description": "Experience not found or registration not found"},
    },
)
async def del_experience_me(
    experience_id: str,
    account_id: str = Depends(get_current_account_id),
):
    return await delete_my_experience(
        account_id=account_id, experience_id=experience_id
    )


@router.post("/addpreferences")
async def add_helper_preferences(
    data: Dict[str, Any], user: Registration = Depends(get_current_registration)
):
    return await service.add_helper_preference_logic(data, user.id)


@router.patch("/updatepreferences")
async def update_helper_preferences(
    data: Dict[str, Any], user: Registration = Depends(get_current_registration)
):
    return await service.update_helper_preference_logic(data, user.id)


@router.get("/my-preferences")
async def get_my_preferences(user: Registration = Depends(get_current_registration)):
    return await service.get_helper_preference_logic(user.id)


# find matched seekers
@router.get("/find-my-seekers")
async def find_my_seekers(user: Registration = Depends(get_current_registration)):
    return await service.get_matches_for_helper_logic(user.id)


# find helpers details using helper id
# app/routers/helper.py
@router.get("/helper-details/{target_id}")
async def get_helper_details_endpoint(
    target_id: str, current_reg: Registration = Depends(get_current_registration)
):
    return await service.get_specific_helper_full_details(target_id, current_reg)
