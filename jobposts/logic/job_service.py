# jobs/logic/job_service.py
from datetime import datetime, timezone

from fastapi import HTTPException

from db.tables import JobRequest, JobRequestService, Registration


async def create_new_job(account_id: str, payload: dict):
    # 1. Find the Seeker's Registration ID
    reg = await Registration.objects().where(Registration.account == account_id).first()
    if not reg or reg.role not in ["seeker", "both"]:
        raise HTTPException(status_code=403, detail="Only seekers can post jobs")

    # 2. Extract service IDs before saving the JobRequest
    service_ids = payload.pop("service_ids", [])

    # 3. Create the Job Request
    job = JobRequest(
        seeker=reg.id,
        headline=payload["headline"],
        description=payload["description"],
        city=payload["city"],
        area=payload["area"],
        contact_phone=payload.get("contact_phone"),
        job_type=payload["job_type"],
        created_at=datetime.now(timezone.utc),
    )
    await job.save()

    # 4. Link the services to the job (Many-to-Many)
    if service_ids:
        for s_id in service_ids:
            await JobRequestService(job_request=job.id, service=s_id).save()

    return job


async def list_all_jobs(city: str = None):
    query = JobRequest.objects().where(JobRequest.status == "open")
    if city:
        query = query.where(JobRequest.city == city)
    return await query.order_by(JobRequest.created_at, ascending=False)
