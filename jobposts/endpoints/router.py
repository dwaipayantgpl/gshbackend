# jobs/endpoints/router.py
from fastapi import APIRouter, Depends, Query
from auth.logic.deps import get_current_account_id
from jobs.logic import job_service
from jobs.structs.dtos import JobRequestCreateIn, JobRequestOut
from typing import List

router = APIRouter(tags=["jobs"])

@router.post("/", response_model=JobRequestOut, summary="Post a new job requirement")
async def post_job(
    payload: JobRequestCreateIn, 
    account_id: str = Depends(get_current_account_id)
):
    """Allows a Seeker to post a new job request."""
    return await job_service.create_new_job(account_id, payload.model_dump())

@router.get("/", response_model=List[JobRequestOut], summary="Browse all open jobs")
async def browse_jobs(city: Optional[str] = Query(None)):
    """Allows Helpers to see all available jobs."""
    return await job_service.list_all_jobs(city)