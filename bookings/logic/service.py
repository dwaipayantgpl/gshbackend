from datetime import timedelta
from uuid import UUID
import uuid
from fastapi import HTTPException

from db.tables import  HelperInstitutional, HelperPersonal, Registration, SeekerInstitutional, SeekerPersonal, Service, ServiceBooking
from notifications.logic.service import NotificationService
from profiles.logic.profile_service import get_profile_base64_logic


async def create_service_booking_logic(seeker_id: str, data: dict):
    # 1. Save the detailed booking
    booking = ServiceBooking(
        seeker=seeker_id,
        customer_name=data['customer_name'],
        customer_phone=data['customer_phone'],
        address=data['address'],
        city=data['city'],
        area=data['area'],
        pin_code=data['pin_code'],
        service=data['service_id'],
        helper=data['helper_id'],
        booking_date=data['booking_date'],
        time_slot=data['time_slot'],
        work_details=data['work_details'],
        duration=data['duration'],
        preferences=data.get('preferences'),
        payment_method=data['payment_method'],
        total_price=data['total_price']
    )
    await booking.save()

    # 2. Fetch helper and service names for the summary response
    # (Assuming you've pre-fetched these or can join them)
    helper_info = await HelperPersonal.objects().where(
        HelperPersonal.registration == data['helper_id']
    ).first().run()
    
    service_info = await Service.objects().get(Service.id == data['service_id'])
    
    seeker_profile = await Registration.objects().get(Registration.id == seeker_id).run()
    seeker_name = seeker_profile.account if seeker_profile else "A Seeker"

    try:
        target_helper_id = data.get('helper_id') or data.get('helper')
        
        await NotificationService.trigger(
            user_id=str(target_helper_id),
            title="New Booking Request",
            content=f"You have a booking new request from {data['customer_name']}.",
            booking_id=str(booking.id)
        )
    except Exception as e:
        print(f"Notification Error: {e}")

    # 3. Return the Step 9 Summary
    return {
        "booking_id": booking.id,
        "helper_name": helper_info.name if helper_info else "Assigned Maid",
        "service_name": service_info.name,
        "booking_date": booking.booking_date,
        "time_slot": booking.time_slot,
        "address": booking.address,
        "total_price": float(booking.total_price),
        "status": booking.status
    }


# bookings/logic/service.py

async def update_seeker_booking_logic(booking_id: UUID, seeker_id: str, data: dict):
    # 1. Fetch the booking
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id)
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2. Safety: Only the seeker who created it can edit it
    if str(booking.seeker) != seeker_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this booking")

    # 3. YOUR CORE LOGIC: Check status
    if booking.status != "pending":
        raise HTTPException(
            status_code=400, 
            detail=f"Updates not allowed. Booking is already {booking.status}."
        )

    # 4. Apply only the fields that were sent in the request
    # Filter out None values so we don't overwrite good data with nulls
    update_data = {k: v for k, v in data.items() if v is not None}
    
    for key, value in update_data.items():
        setattr(booking, key, value)

    await booking.save()
    return {"message": "Booking updated successfully", "booking_id": str(booking.id)}


# async def get_seeker_bookings_logic(seeker_id: str):
#     # 1. Fetch bookings with service name and helper_id
#     bookings = await ServiceBooking.select(
#         ServiceBooking.all_columns(),
#         ServiceBooking.service.name.as_alias("service_name"),
#         ServiceBooking.helper.id.as_alias("helper_reg_id") 
#     ).where(
#         ServiceBooking.seeker == seeker_id
#     ).order_by(
#         ServiceBooking.created_at, ascending=False
#     ).run()

#     if not bookings:
#         return []

#     # 2. Collect all unique helper registration IDs from the bookings
#     helper_ids = list(set([b["helper_reg_id"] for b in bookings]))

#     # 3. Batch fetch names from HelperPersonal table
#     # (Assuming most helpers are 'personal'. If you use both, you'd check HelperInstitutional too)
#     helper_profiles = await HelperPersonal.select(
#         HelperPersonal.registration,
#         HelperPersonal.name
#     ).where(
#         HelperPersonal.registration.is_in(helper_ids)
#     ).run()

#     # Create a mapping for O(1) lookup: { "reg_id": "Name" }
#     name_map = {str(p["registration"]): p["name"] for p in helper_profiles}

#     # 4. Attach the names to the booking objects
#     for b in bookings:
#         b["helper_name"] = name_map.get(str(b["helper_reg_id"]), "Unknown Helper")

#     return bookings


async def get_seeker_bookings_logic(seeker_id: str):
    # 1. Fetch bookings with service name and helper_id
    bookings = await ServiceBooking.select(
        ServiceBooking.all_columns(),
        ServiceBooking.service.name.as_alias("service_name"),
        ServiceBooking.helper.id.as_alias("helper_reg_id") 
    ).where(
        ServiceBooking.seeker == seeker_id
    ).order_by(
        ServiceBooking.created_at, ascending=False
    ).run()

    if not bookings:
        return []

    # 2. Collect unique helper IDs
    helper_ids = list(set([b["helper_reg_id"] for b in bookings]))

    # 3. Batch fetch from BOTH Personal and Institutional tables
    # Personal helpers usually have City/Area
    personal_data = await HelperPersonal.select(
        HelperPersonal.registration,
        HelperPersonal.name,
        HelperPersonal.city,
        HelperPersonal.area
    ).where(HelperPersonal.registration.is_in(helper_ids)).run()

    # Institutional helpers usually have a full Address
    institutional_data = await HelperInstitutional.select(
        HelperInstitutional.registration,
        HelperInstitutional.name,
        HelperInstitutional.city,
        HelperInstitutional.address
    ).where(HelperInstitutional.registration.is_in(helper_ids)).run()

    # Create a unified mapping: { "reg_id": {"name": "...", "address": "..."} }
    helper_info_map = {}

    for p in personal_data:
        reg_id = str(p["registration"])
        # Format address as "City, Area" for personal helpers
        address_str = f"{p['city']}, {p['area']}" if p['city'] and p['area'] else (p['city'] or p['area'] or "Address not provided")
        helper_info_map[reg_id] = {"name": p["name"], "address": address_str}

    for i in institutional_data:
        reg_id = str(i["registration"])
        # Format address as "Full Address, City" for institutions
        address_str = f"{i['address']}, {i['city']}" if i['address'] and i['city'] else (i['address'] or i['city'] or "Address not provided")
        helper_info_map[reg_id] = {"name": i["name"], "address": address_str}

    # 4. Attach the names and addresses to the booking objects
    for b in bookings:
        info = helper_info_map.get(str(b["helper_reg_id"]), {})
        b["helper_name"] = info.get("name", "Unknown Helper")
        b["helper_address"] = info.get("address", "N/A")

    return bookings


async def cancel_booking_by_seeker_logic(booking_id: str, seeker_id: str):
    # 1. Fetch the booking
    booking = await ServiceBooking.objects().get(ServiceBooking.id == booking_id)
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # 2. Security: Ensure this seeker actually owns this booking
    if str(booking.seeker) != seeker_id:
        raise HTTPException(status_code=403, detail="You can only cancel your own bookings")

    # 3. State Check: Can't cancel if already finished or already cancelled
    if booking.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed service")
    
    if booking.status == "cancelled":
        return {"message": "Booking is already cancelled"}

    # 4. Update Status
    booking.status = "cancelled"
    await booking.save()

    return {
        "message": "Booking cancelled successfully",
        "booking_id": str(booking.id),
        "status": "cancelled"
    }

#get bookings details for helper
async def get_booking_details_for_helper(booking_id: str, current_reg: Registration):
    # 1. Validate UUID
    try:
        b_uuid = uuid.UUID(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Booking ID")

    # 2. Fetch Booking using the Table Class Name
    # We use 'ServiceBooking' to call objects(), not 'booking'
    booking_record = await ServiceBooking.objects().where(
        ServiceBooking.id == b_uuid
    ).prefetch(ServiceBooking.seeker, ServiceBooking.service).first().run()

    if not booking_record:
        raise HTTPException(status_code=404, detail="Booking not found")
    if str(booking_record.helper) != str(current_reg.id) and str(current_reg.role).lower() != 'admin':
        raise HTTPException(status_code=403, detail="This booking is not assigned to you.")

    return booking_record

# helper can change the booking status 
async def update_booking_status(booking_id: str, new_status: str, current_reg: Registration):
    if new_status not in ['accepted', 'rejected']:
        raise HTTPException(status_code=400, detail="Use 'accepted' or 'rejected' only.")

    booking_obj = await get_booking_details_for_helper(booking_id, current_reg)
    
    if booking_obj.status != 'pending':
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot {new_status}. Booking is currently {booking_obj.status}."
        )

    # --- ADDED: Conflict Validation ---
    if new_status == 'accepted':
        # Check if the helper already has an accepted booking at this time
        conflict = await ServiceBooking.objects().where(
            (ServiceBooking.helper == current_reg.id) &
            (ServiceBooking.booking_date == booking_obj.booking_date) &
            (ServiceBooking.time_slot == booking_obj.time_slot) &
            (ServiceBooking.status == 'accepted')
        ).first().run()

        if conflict:
            raise HTTPException(
                status_code=400, 
                detail="You already have an accepted booking for this date and time slot."
            )
    # ----------------------------------

    booking_obj.status = new_status
    await booking_obj.save().run() # Added .run() for safety
    
    # 1. Fetch Helper's Name
    helper_profile = await HelperPersonal.objects().where(
        HelperPersonal.registration == current_reg.id
    ).first().run()
    display_name = helper_profile.name if (helper_profile and helper_profile.name) else (current_reg.account or "A Helper")
    
    # 2. Fetch Seeker's Name (REQUIRED for the Helper's notification)
    seeker_reg = await Registration.objects().get(Registration.id == booking_obj.seeker).run()
    seeker_name = seeker_reg.account if seeker_reg else "The Seeker"

    action = "accepted" if new_status == "accepted" else "rejected"

    # --- MAIN STATUS NOTIFICATION ---
    try:
        target_id = str(booking_obj.seeker.id if hasattr(booking_obj.seeker, 'id') else booking_obj.seeker)
        from notifications.logic.service import NotificationService
        
        await NotificationService.trigger(
            user_id=target_id,
            title=f"Booking {action.capitalize()}",
            content=f"{display_name} has {action} your booking request.",
            booking_id=str(booking_id)
        )
        print(f"✅ Success: Notification triggered for {target_id} with name {display_name}")
    except Exception as e:
        print(f"❌ Notification Error: {e}")

    # --- RATING NOTIFICATIONS (ONLY IF ACCEPTED) ---
    if new_status == 'accepted':
        try:
            # 1. FIX THE SEEKER ID
            # Use .id to get the UUID, then str() to make it a string
            clean_seeker_id = str(booking_obj.seeker.id if hasattr(booking_obj.seeker, 'id') else booking_obj.seeker)
            
            # 2. FIX THE HELPER ID 
            # current_reg is the helper; use its ID directly
            clean_helper_id = str(current_reg.id)

            # --- TO SEEKER ---
            await NotificationService.trigger(
                user_id=clean_seeker_id, # FIXED
                title="Rate your Helper! ⭐",
                content=f"Once the work is done, don't forget to rate {display_name}!",
                booking_id=str(booking_id)
            )

            seeker_reg = await Registration.objects().get(Registration.id == booking_obj.seeker).run()

# 2. Get the clean Name (if 'account' is an ID, you might need a different field like 'full_name')
            seeker_display_name = seeker_reg.account if seeker_reg else "the Seeker"
            # --- TO HELPER ---
            await NotificationService.trigger(
                user_id=clean_helper_id, # FIXED
                title="Rate the Seeker! ⭐",
                content=f"Once you finish the job, please rate your experience with {seeker_display_name}.",
                booking_id=str(booking_id)
            )
            
            print(f"✅ Rating reminders sent to {display_name} and {seeker_name}")
        except Exception as e:
            print(f"❌ Rating Notification Error: {e}")

    return {
        "status": "success", 
        "message": f"You have {new_status} the booking.",
        "booking_id": booking_id
    }



async def get_helper_busy_dates_logic(helper_id: str):
    # Fetch all bookings for this helper that aren't cancelled
    bookings = await ServiceBooking.select(
        ServiceBooking.booking_date,
        ServiceBooking.time_slot
    ).where(
        (ServiceBooking.helper == helper_id) & 
        (ServiceBooking.status.not_in(['cancelled', 'rejected']))
    ).run()

    # Return a clean list of date strings and their slots
    return [
        {"date": b["booking_date"].isoformat(), "slot": b["time_slot"]} 
        for b in bookings
    ]



async def get_helper_bookings_logic(helper_id: str):
    # 1. Fetch bookings where the user is the Helper
    bookings = await ServiceBooking.select(
        ServiceBooking.all_columns(),
        ServiceBooking.service.name.as_alias("service_name"),
        ServiceBooking.seeker.id.as_alias("seeker_reg_id"),
        ServiceBooking.seeker.account.id.as_alias("seeker_account_id"),
        ServiceBooking.seeker.account.phone.as_alias("seeker_phone")
    ).where(
        ServiceBooking.helper == helper_id
    ).order_by(
        ServiceBooking.created_at, ascending=False
    ).run()

    if not bookings:
        return []

    # 2. Batch fetch Seeker names
    seeker_ids = list(set([b["seeker_reg_id"] for b in bookings]))
    
    # Check both Personal and Institutional seeker tables
    p_profiles = await SeekerPersonal.select(SeekerPersonal.registration, SeekerPersonal.name).where(SeekerPersonal.registration.is_in(seeker_ids)).run()
    i_profiles = await SeekerInstitutional.select(SeekerInstitutional.registration, SeekerInstitutional.name).where(SeekerInstitutional.registration.is_in(seeker_ids)).run()

    # Create a unified name map
    name_map = {str(p["registration"]): p["name"] for p in p_profiles}
    name_map.update({str(i["registration"]): i["name"] for i in i_profiles})

    # 3. Attach details and Profile Pictures
    for b in bookings:
        s_id = str(b["seeker_reg_id"])
        b["seeker_name"] = name_map.get(s_id, "Unknown Seeker")
        # Reuse your existing image logic if available
        b["seeker_profile_picture"] = await get_profile_base64_logic(s_id) 

    return bookings