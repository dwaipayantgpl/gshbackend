# profiles/endpoints/router.py
import base64

from fastapi import APIRouter, Depends, Body, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from auth.logic.deps import get_current_account_id, get_current_registration
from profiles.logic import profile_service
from db.tables import Registration
from profiles.logic.profile_service import get_my_profile, upsert_my_profile
from profiles.structs.dtos import ProfileOut, ProfileUpsertIn

router = APIRouter()

@router.get("/me", response_model=ProfileOut, summary="Get My Profile")
async def me_profile(account_id: str = Depends(get_current_account_id)):
    return await get_my_profile(account_id=account_id)


@router.put(
    "/me",
    response_model=ProfileOut,
    summary="Upsert Profile",
    description=(
        "Send exactly one payload shape. Choose by setting `kind`.\n\n"
        "- `seeker_personal` => {name, city, area}\n"
        "- `seeker_institutional` => {name, city, area, institution_type?, phone?}\n"
        "- `helper_personal` => {name, city, area, age?, faith?, languages?, phone?, years_of_experience?}\n"
        "- `helper_institutional` => {name, city, address, phone?}\n"
    ),
)
async def upsert_profile(
    payload: ProfileUpsertIn = Body(
        ...,
        openapi_examples={
            "seeker_personal": {
                "summary": "Seeker • Personal",
                "value": {
                    "kind": "seeker_personal",
                    "name": "Akash",
                    "city": "Kolkata",
                    "area": "Salt Lake",
                },
            },
            "seeker_institutional": {
                "summary": "Seeker • Institutional",
                "value": {
                    "kind": "seeker_institutional",
                    "name": "ABC Hospital",
                    "city": "Kolkata",
                    "area": "Park Street",
                    "institution_type": "Hospital",
                    "phone": "9999999999",
                },
            },
            "helper_personal": {
                "summary": "Helper • Personal",
                "value": {
                    "kind": "helper_personal",
                    "name": "Akash",
                    "city": "Kolkata",
                    "area": "Salt Lake",
                    "languages": "English,Hindi,Bengali",
                    "years_of_experience": 3,
                },
            },
            "helper_institutional": {
                "summary": "Helper • Institutional",
                "value": {
                    "kind": "helper_institutional",
                    "name": "Care Agency X",
                    "city": "Mumbai",
                    "address": "Andheri East",
                    "phone": "8888888888",
                },
            },
        },
    ),
    account_id: str = Depends(get_current_account_id),
):
    return await upsert_my_profile(account_id=account_id, payload=payload)



# @router.post("/picture")
# async def upload_picture(
#     file: UploadFile = File(...),
#     current_reg: Registration = Depends(get_current_registration)
# ):
#     result = await profile_service.save_profile_file_logic(str(current_reg.id), file, mode="post")
    
#     if result.get("status") == "error":
#         # This will now correctly trigger if the extension is wrong
#         raise HTTPException(status_code=400, detail=result["message"])
    
#     return FileResponse(
#         path=result["path"],
#         filename=result["filename"],
#         media_type=result["mime_type"],
#         content_disposition_type="inline"
#     )


@router.post("/picture")
async def upload_picture(
    file: UploadFile = File(...),
    current_reg: Registration = Depends(get_current_registration)
):
    result = await profile_service.save_profile_file_logic(str(current_reg.id), file, mode="post")
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    file_path = result["path"]
    
    try:
        # 1. Read the binary content of the saved file
        with open(file_path, "rb") as image_file:
            binary_data = image_file.read()
            
            # 2. Encode to base64
            base64_encoded = base64.b64encode(binary_data).decode('utf-8')
            
            # 3. Format as a Data URL (optional, but very helpful for frontends)
            # Example: "data:image/png;base64,iVBORw0KGgoAAAANSUhEU..."
            mime_type = result.get("mime_type", "image/jpeg")
            base64_string = f"data:{mime_type};base64,{base64_encoded}"

        return {
            "status": "success",
            "image_base64": base64_string,
            "filename": result["filename"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")


@router.patch("/picture")
async def update_picture(
    file: UploadFile = File(...),
    current_reg: Registration = Depends(get_current_registration)
):
    result = await profile_service.save_profile_file_logic(str(current_reg.id), file, mode="patch")
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    file_path = result["path"]
    
    try:
        # 1. Read the binary content of the saved file
        with open(file_path, "rb") as image_file:
            binary_data = image_file.read()
            
            # 2. Encode to base64
            base64_encoded = base64.b64encode(binary_data).decode('utf-8')
            
            # 3. Format as a Data URL (optional, but very helpful for frontends)
            # Example: "data:image/png;base64,iVBORw0KGgoAAAANSUhEU..."
            mime_type = result.get("mime_type", "image/jpeg")
            base64_string = f"data:{mime_type};base64,{base64_encoded}"

        return {
            "status": "success",
            "image_base64": base64_string,
            "filename": result["filename"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")
    

@router.get("/picture/base64")
async def get_my_picture(
    current_reg: Registration = Depends(get_current_registration)
):
    base64_str = await profile_service.get_profile_base64_logic(str(current_reg.id))
    
    if not base64_str:
        raise HTTPException(
            status_code=404, 
            detail="Profile picture not found. Please upload one first."
        )

    # Returning the exact same structure as your POST/PATCH
    return {
        "status": "success",
        "image_base64": base64_str
    }