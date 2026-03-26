from http.client import HTTPException

from piccolo.query.functions.aggregate import Avg

from db.tables import Review, SeekerInstitutional, SeekerPersonal


async def add_review_logic(
    seeker_id: str, helper_id: str, booking_id: str, rating: int, comment: str = None
):
    existing_review = (
        await Review.objects().where(Review.booking == booking_id).first().run()
    )
    if existing_review:
        raise HTTPException(
            status_code=400, detail="This booking has already been rated."
        )

    new_review = Review(
        booking=booking_id,
        seeker=seeker_id,
        helper=helper_id,
        rating=rating,
        comment=comment,
    )
    await new_review.save()
    # return {"message": "Rating submitted successfully for this booking."}
    return new_review


# For Seeker: "Who have I rated?"
async def get_seeker_reviews_given(seeker_id: str):
    return (
        await Review.select(
            Review.all_columns(),
            Review.helper.account.phone,  # See who they rated
        )
        .where(Review.seeker == seeker_id)
        .run()
    )


# For Helper: "What are my ratings?"
async def get_helper_reviews_received(helper_id: str):
    return await Review.select().where(Review.helper == helper_id).run()


async def get_helper_overall_rating(helper_id: str):
    # 1. Calculate Average
    result = (
        await Review.select(Avg(Review.rating)).where(Review.helper == helper_id).run()
    )
    avg_rating = result[0]["avg"] if result and result[0]["avg"] else 0

    # 2. Total Count
    total_reviews = await Review.count().where(Review.helper == helper_id).run()

    # 3. (Optional) Get individual star counts for a progress bar UI
    # This helps frontend show: 5 stars (10), 4 stars (2), etc.
    star_breakdown = {}
    for star in range(1, 6):
        count = (
            await Review.count()
            .where((Review.helper == helper_id) & (Review.rating == star))
            .run()
        )
        star_breakdown[f"{star}_star"] = count

    return {
        "helper_id": helper_id,
        "overall_rating": round(float(avg_rating), 1),
        "total_reviews": total_reviews,
        "star_breakdown": star_breakdown,
    }


# Update to your get_seeker_reviews_given logic
async def get_seeker_reviews_given(seeker_id: str):
    return (
        await Review.select(
            Review.all_columns(),
            Review.helper.id.as_alias("helper_reg_id"),
        )
        .where(Review.seeker == seeker_id)
        .run()
    )


async def get_helper_reviews_with_names(helper_id: str):
    # 1. Fetch all reviews for this helper
    # We prefetch registration and account to get the phone number easily
    reviews = (
        await Review.objects()
        .where(Review.helper == helper_id)
        .prefetch(Review.seeker, Review.seeker.account)
        .order_by(Review.created_at, ascending=False)
        .run()
    )

    # 2. Identify which seekers are personal vs institutional
    seeker_reg_ids = [r.seeker.id for r in reviews]

    # Batch fetch names from both profile tables
    p_profiles = {
        p.registration: p.name
        for p in await SeekerPersonal.objects()
        .where(SeekerPersonal.registration.is_in(seeker_reg_ids))
        .run()
    }
    i_profiles = {
        p.registration: p.name
        for p in await SeekerInstitutional.objects()
        .where(SeekerInstitutional.registration.is_in(seeker_reg_ids))
        .run()
    }

    results = []
    for r in reviews:
        # Determine name based on capacity/table existence
        seeker_name = (
            p_profiles.get(r.seeker.id)
            or i_profiles.get(r.seeker.id)
            or "Unknown Seeker"
        )

        results.append(
            {
                "review_id": str(r.id),
                "rating": r.rating,
                "comment": r.comment,
                "date": r.created_at.strftime("%Y-%m-%d"),
                "seeker_name": seeker_name,
                "seeker_phone": r.seeker.account.phone,
                "seeker_registration_id": str(r.seeker.id),
            }
        )

    return results


# ratings by booking id
async def get_review_by_booking_logic(booking_id: str):
    # Fetch review and join with related names
    review = (
        await Review.objects()
        .where(Review.booking == booking_id)
        .prefetch(Review.seeker, Review.helper)
        .first()
        .run()
    )

    if not review:
        return None

    return review
