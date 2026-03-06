from datetime import timedelta
from fastapi import HTTPException

from bookings.structs.dtos import ApplyToHelperSchema
from db.tables import BookingRequest
from notifications.logic.service import NotificationService

async def apply_for_service_logic(seeker_id: str, data: ApplyToHelperSchema):
    if str(seeker_id) == str(data.helper_reg_id):
        raise HTTPException(status_code=400, detail="You cannot apply to yourself.")
    buffer_start = data.scheduled_start - timedelta(minutes=30)
    buffer_end = data.scheduled_end + timedelta(minutes=30)

    is_busy = await BookingRequest.objects().where(
        (BookingRequest.helper == data.helper_reg_id) &
        (BookingRequest.status == "accepted") &
        (BookingRequest.scheduled_start < buffer_end) &
        (BookingRequest.scheduled_end > buffer_start)
    ).exists().run()

    if is_busy:
        raise HTTPException(status_code=409, detail="Helper is busy or traveling during this time.")

    # 3. Create the 'Application' (The Request)
    new_request = BookingRequest(
        seeker=seeker_id,
        helper=data.helper_reg_id,
        service=data.service_id,
        scheduled_start=data.scheduled_start,
        scheduled_end=data.scheduled_end,
        address=data.address,
        notes=data.notes
    )
    await new_request.save().run()
    await NotificationService.create_aleart(
        recipient_id=str(data.helper_reg_id),
        title="New Booking Request!",
        content="A Seeker wants to book you. Open the app to check details.",
        booking_id=new_request.id

    )
    return {"status": "success", "message": "Application sent to helper", "id": new_request.id}


async def get_received_applications(helper_reg_id:str):
    return await BookingRequest.select(
        BookingRequest.id,
        BookingRequest.scheduled_start,
        BookingRequest.scheduled_end,
        BookingRequest.address,
        BookingRequest.seeker.id.as_name("seeker_reg_id"),
        BookingRequest.seeker.account.id.as_name("seeker_account_id"),
        BookingRequest.service.name.as_name("service_name")
    ).where(
        (BookingRequest.helper == helper_reg_id) &
        (BookingRequest.status == "pending")
    ).run()


async def respond_to_application_logic(booking_id: str, helper_id: str, action: str):
    """
    Action should be 'accepted' or 'rejected'.
    """
    # 1. Get the specific request
    request = await BookingRequest.objects().get(BookingRequest.id == booking_id).run()
    
    if not request or str(request.helper) != str(helper_id):
        raise HTTPException(status_code=404, detail="Application not found or unauthorized.")

    if action == "rejected":
        await BookingRequest.update({
            BookingRequest.status: "rejected"
        }).where(BookingRequest.id == booking_id).run()
        return {"status": "success", "message": "Application rejected."}

    # 2. If accepting, run the 'Final Collision Check'
    buffer_start = request.scheduled_start - timedelta(minutes=30)
    buffer_end = request.scheduled_end + timedelta(minutes=30)

    collision = await BookingRequest.objects().where(
        (BookingRequest.helper == helper_id) &
        (BookingRequest.status == "accepted") &
        (BookingRequest.scheduled_start < buffer_end) &
        (BookingRequest.scheduled_end > buffer_start)
    ).exists().run()

    if collision:
        raise HTTPException(status_code=409, detail="You already have an accepted job at this time.")

    # 3. Finalize the Handshake
    await BookingRequest.update({
        BookingRequest.status: "accepted"
    }).where(BookingRequest.id == booking_id).run()

    return {"status": "success", "message": "Booking confirmed!"}