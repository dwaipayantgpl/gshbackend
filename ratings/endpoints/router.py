from http.client import HTTPException

from fastapi import APIRouter, Body, Depends

from auth.logic.deps import get_current_registration
from db.tables import Registration
from ratings.logic import service
from ratings.structs.dtos import ReviewCreateSchema
router = APIRouter()

# endpoints/review_router.py

@router.post("/rate")
async def post_review(data: ReviewCreateSchema, current_user: Registration = Depends(get_current_registration)):
    return await service.add_review_logic(str(current_user.id), str(data.helper_id), data.rating, data.comment)

@router.get("/my-given-reviews")
async def my_given_reviews(current_user: Registration = Depends(get_current_registration)):
    return await service.get_seeker_reviews_given(str(current_user.id))

@router.get("/helper-stats/{helper_id}")
async def helper_stats(helper_id: str):
    return await service.get_helper_overall_rating(helper_id)

# endpoints/review_router.py

@router.post("/rate", summary="Seeker rates a Helper")
async def post_review(
    data: ReviewCreateSchema, 
    current_user: Registration = Depends(get_current_registration)
):
    # Ensure only Seekers can rate (Optional check)
    if current_user.role not in ['seeker', 'both']:
        raise HTTPException(status_code=403, detail="Only seekers can provide ratings.")

    return await service.add_review_logic(
        seeker_id=str(current_user.id), 
        helper_id=str(data.helper_id), 
        rating=data.rating, 
        comment=data.comment
    )


@router.get("/my-received-ratings", summary="Helper sees all reviews given to them")
async def my_received_reviews(
    current_user: Registration = Depends(get_current_registration)
):
    if current_user.role not in ['helper', 'both']:
        raise HTTPException(status_code=403, detail="Only helpers can view received reviews.")
        
    return await service.get_helper_reviews_with_names(str(current_user.id))