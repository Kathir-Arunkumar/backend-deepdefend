from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from models import FileMetadata
from database import files_collection
from auth_utils import get_current_user_id
import os
import shutil

dashboard_router = APIRouter()

# Directory to store uploaded files locally
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Create directory if not exists

# File Upload Endpoint
@dashboard_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    visibility: str = Form(...),  # Accept 'private' or 'public' from the frontend
    user_id: str = Depends(get_current_user_id)
):
    try:
        # Define the file path
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        # Save file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Store file metadata in MongoDB
        file_metadata = {
            "user_id": user_id,
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": file.size,
            "storage_path": file_path,
            "visibility": visibility  # 'private' or 'public'
        }
        await files_collection.insert_one(file_metadata)

        return {
            "message": "File uploaded successfully!",
            "file_name": file.filename,
            "visibility": visibility
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
