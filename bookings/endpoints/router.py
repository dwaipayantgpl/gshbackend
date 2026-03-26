from typing import List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.logic.deps import get_current_registration
from bookings.logic import service
from bookings.structs.dtos import (
    BookingSummaryOut,
    BookingUpdateSchema,
    DirectBookingCreate,
)
from db.tables import Registration, ServiceBooking

router = APIRouter()


@router.post("/create", response_model=BookingSummaryOut)
async def create_booking(
    data: DirectBookingCreate,
    current_user: Registration = Depends(get_current_registration),
):
    if current_user.role not in ["seeker", "both"]:
        raise HTTPException(status_code=403, detail="Only seekers can create bookings.")

    # Pass the seeker_id and the validated data dictionary to logic
    return await service.create_service_booking_logic(
        str(current_user.id), data.model_dump()
    )


@router.patch(
    "/{booking_id}/update", summary="Seeker updates booking details (Only if pending)"
)
async def update_booking_details(
    booking_id: UUID,
    data: BookingUpdateSchema,
    current_user: Registration = Depends(get_current_registration),
):
    """
    Allows the seeker to update booking info ONLY while status is 'pending'.
    If accepted, rejected, or cancelled, this will return an error.
    """
    return await service.update_seeker_booking_logic(
        booking_id, str(current_user.id), data.model_dump()
    )


@router.get("/my-bookings", response_model=List[dict])
async def get_my_bookings(
    current_user: Registration = Depends(get_current_registration),
):
    """
    Returns all bookings made by the logged-in Seeker.
    """
    if current_user.role not in ["seeker", "both"]:
        raise HTTPException(
            status_code=403, detail="Only seekers can view booking history"
        )

    return await service.get_seeker_bookings_logic(str(current_user.id))


@router.patch("/{booking_id}/cancel", summary="Seeker cancels their own booking")
async def seeker_cancel_booking(
    booking_id: UUID, current_user: Registration = Depends(get_current_registration)
):
    """
    Allows a Seeker to cancel their booking.
    Works if the status is 'pending' or 'accepted'.
    """
    return await service.cancel_booking_by_seeker_logic(
        str(booking_id), str(current_user.id)
    )


@router.get(
    "/helper/{helper_id}/busy-dates", summary="Get unavailable dates for a helper"
)
async def get_helper_busy_dates(helper_id: UUID):
    """
    Returns a list of dates and time slots where this helper is already booked.
    Example Response: [{"date": "2026-03-15", "slot": "Morning"}]
    """
    return await service.get_helper_busy_dates_logic(str(helper_id))


@router.get("/my-requests", response_model=List[dict])
async def get_helper_requests(
    current_user: Registration = Depends(get_current_registration),
):
    # Fetch all bookings assigned to this helper that are still 'pending'
    requests = (
        await ServiceBooking.select(
            ServiceBooking.all_columns(),
            ServiceBooking.service.name.as_alias("service_type"),
        )
        .where(
            (ServiceBooking.helper == current_user.id)
            & (ServiceBooking.status == "pending")
        )
        .run()
    )

    return requests


@router.get("/helper/details/{booking_id}")
async def helper_view_booking(
    booking_id: str, current_user: Registration = Depends(get_current_registration)
):
    """
    Allows a Helper to see full details of a booking (Address, Seeker name, etc.)
    before they decide to accept or reject.
    """
    if current_user.role not in ["helper", "both", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    return await service.get_booking_details_for_helper(booking_id, current_user)


@router.patch("/helper/respond/{booking_id}")
async def helper_respond_to_booking(
    booking_id: str,
    new_status: Literal["accepted", "rejected"] = Query(...),
    current_user: Registration = Depends(get_current_registration),
):
    if current_user.role not in ["helper", "both"]:
        raise HTTPException(
            status_code=403, detail="Only helpers can respond to requests."
        )

    return await service.update_booking_status(booking_id, new_status, current_user)


@router.get("/helper/my-requests", response_model=List[dict])
async def get_helper_booking_requests(
    current_user: Registration = Depends(get_current_registration),
):
    """
    Returns all bookings/requests assigned to the logged-in Helper.
    """
    if current_user.role not in ["helper", "both"]:
        raise HTTPException(
            status_code=403, detail="Only helpers can view these requests"
        )

    return await service.get_helper_bookings_logic(str(current_user.id))
