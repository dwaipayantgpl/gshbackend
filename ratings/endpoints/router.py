from fastapi import APIRouter, Depends, HTTPException

from auth.logic.deps import get_current_registration
from db.tables import Registration, ServiceBooking
from ratings.logic import service
from ratings.structs.dtos import ReviewCreateSchema

router = APIRouter()

# endpoints/review_router.py

# @router.post("/rate")
# async def post_review(data: ReviewCreateSchema, current_user: Registration = Depends(get_current_registration)):
#     return await service.add_review_logic(str(current_user.id), str(data.helper_id), data.rating, data.comment)


@router.get("/my-given-reviews")
async def my_given_reviews(
    current_user: Registration = Depends(get_current_registration),
):
    return await service.get_seeker_reviews_given(str(current_user.id))


@router.get("/helper-stats/{helper_id}")
async def helper_stats(helper_id: str):
    return await service.get_helper_overall_rating(helper_id)


@router.post("/rate", summary="Seeker rates a Helper for a specific booking")
async def post_review(
    data: ReviewCreateSchema,
    current_user: Registration = Depends(get_current_registration),
):
    if current_user.role not in ["seeker", "both"]:
        raise HTTPException(status_code=403, detail="Only seekers can provide ratings.")

    return await service.add_review_logic(
        seeker_id=str(current_user.id),
        helper_id=str(data.helper_id),
        booking_id=str(data.booking_id),  # <--- Pass this now
        rating=data.rating,
        comment=data.comment,
    )


@router.get("/my-received-ratings", summary="Helper sees all reviews given to them")
async def my_received_reviews(
    current_user: Registration = Depends(get_current_registration),
):
    if current_user.role not in ["helper", "both"]:
        raise HTTPException(
            status_code=403, detail="Only helpers can view received reviews."
        )

    return await service.get_helper_reviews_with_names(str(current_user.id))


# ratings/endpoints/router.py


@router.get("/booking/{booking_id}")
async def get_booking_rating(
    booking_id: str, current_user: Registration = Depends(get_current_registration)
):
    # 1. Fetch the booking to check ownership
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id).run()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2. Security Check: Only involved parties or Admin can see it
    is_admin = current_user.role == "admin"
    is_seeker = str(booking.seeker) == str(current_user.id)
    is_helper = str(booking.helper) == str(current_user.id)

    if not (is_admin or is_seeker or is_helper):
        raise HTTPException(
            status_code=403, detail="You do not have permission to view this rating"
        )

    # 3. Get the Review
    review_data = await service.get_review_by_booking_logic(booking_id)

    if not review_data:
        raise HTTPException(status_code=404, detail="No rating found for this booking")

    return review_data
