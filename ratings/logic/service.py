from http.client import HTTPException

from db.tables import Review, SeekerInstitutional, SeekerPersonal
from piccolo.query.functions.aggregate import Avg
async def add_review_logic(seeker_id: str, helper_id: str, rating: int, comment: str = None):
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    new_review = Review(
        seeker=seeker_id,
        helper=helper_id,
        rating=rating,
        comment=comment
    )
    await new_review.save()
    return {"message": "Review submitted successfully"}


# For Seeker: "Who have I rated?"
async def get_seeker_reviews_given(seeker_id: str):
    return await Review.select(
        Review.all_columns(),
        Review.helper.account.phone # See who they rated
    ).where(Review.seeker == seeker_id).run()

# For Helper: "What are my ratings?"
async def get_helper_reviews_received(helper_id: str):
    return await Review.select().where(Review.helper == helper_id).run()




async def get_helper_overall_rating(helper_id: str):
    # Calculate the average of the rating column
    result = await Review.select(Avg(Review.rating)).where(Review.helper == helper_id).run()
    
    # Piccolo returns a list; extract the average
    avg_rating = result[0]['avg'] if result and result[0]['avg'] else 0
    
    # Count total reviews
    total_reviews = await Review.count().where(Review.helper == helper_id).run()
    
    return {
        "overall_rating": round(float(avg_rating), 1),
        "total_reviews": total_reviews
    }

# Update to your get_seeker_reviews_given logic
async def get_seeker_reviews_given(seeker_id: str):
    return await Review.select(
        Review.all_columns(),
        Review.helper.id.as_alias("helper_reg_id"),
    ).where(Review.seeker == seeker_id).run()



async def get_helper_reviews_with_names(helper_id: str):
    # 1. Fetch all reviews for this helper
    # We prefetch registration and account to get the phone number easily
    reviews = await Review.objects().where(
        Review.helper == helper_id
    ).prefetch(Review.seeker, Review.seeker.account).order_by(
        Review.created_at, ascending=False
    ).run()

    # 2. Identify which seekers are personal vs institutional
    seeker_reg_ids = [r.seeker.id for r in reviews]
    
    # Batch fetch names from both profile tables
    p_profiles = {p.registration: p.name for p in await SeekerPersonal.objects().where(SeekerPersonal.registration.is_in(seeker_reg_ids)).run()}
    i_profiles = {p.registration: p.name for p in await SeekerInstitutional.objects().where(SeekerInstitutional.registration.is_in(seeker_reg_ids)).run()}

    results = []
    for r in reviews:
        # Determine name based on capacity/table existence
        seeker_name = p_profiles.get(r.seeker.id) or i_profiles.get(r.seeker.id) or "Unknown Seeker"
        
        results.append({
            "review_id": str(r.id),
            "rating": r.rating,
            "comment": r.comment,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "seeker_name": seeker_name,
            "seeker_phone": r.seeker.account.phone,
            "seeker_registration_id": str(r.seeker.id)
        })

    return results