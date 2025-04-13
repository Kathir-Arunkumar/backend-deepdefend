from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from models import FileMetadata
from database import files_collection
import os
import shutil
from uuid import uuid4

from malware_scan_utils import scan_pdf_file  # <-- make sure this exists

dashboard_router = APIRouter()

# Directories
UPLOAD_DIR = "uploaded_files"
TEMP_DIR = "temp_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Upload Endpoint with Scanning
@dashboard_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    try:
        # Step 1: Validate file type (Only allow PDFs)
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")

        # Step 2: Save temporarily
        temp_filename = f"{uuid4().hex}_{file.filename}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)

        with open(temp_path, "wb") as temp_file:
            temp_file.write(await file.read())

        # Step 3: Scan with ML model
        is_malicious = scan_pdf_file(temp_path)
        if is_malicious:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Malicious PDF detected. Upload blocked.")

        # Step 4: Move to permanent storage
        final_path = os.path.join(UPLOAD_DIR, file.filename)
        shutil.move(temp_path, final_path)

        # Step 5: Save metadata in MongoDB
        file_metadata = {
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": os.path.getsize(final_path),
            "storage_path": final_path,
        }
        await files_collection.insert_one(file_metadata)

        return {"message": "File uploaded and scanned successfully!", "file_name": file.filename}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
