from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form, Body,Request
from models import FileMetadata,QueryRequest
from database import files_collection
import os
import shutil
from uuid import uuid4
from malware_scan_utils import scan_pdf_file
from extract_text import extract_text_from_pdf
from chatbot_utils import get_answer
from pydantic import BaseModel


dashboard_router = APIRouter()

UPLOAD_DIR = "uploaded_files"
TEMP_DIR = "temp_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Upload Endpoint with Scanning + Text Extraction
@dashboard_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files allowed.")

        temp_filename = f"{uuid4().hex}_{file.filename}"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        with open(temp_path, "wb") as temp_file:
            temp_file.write(await file.read())

        is_malicious = scan_pdf_file(temp_path)
        if is_malicious:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Malicious PDF detected.")

        final_path = os.path.join(UPLOAD_DIR, file.filename)
        shutil.move(temp_path, final_path)

        # Extract text
        text_content = extract_text_from_pdf(final_path)

        # Save metadata + content
        file_metadata = {
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": os.path.getsize(final_path),
            "storage_path": final_path,
            "extracted_text": text_content,
        }
        await files_collection.insert_one(file_metadata)

        return {"message": "File uploaded, scanned, and processed!", "file_name": file.filename}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/chat")
async def chat_with_pdf(request: QueryRequest):
    uploaded_dir = "uploaded_files"

    if not request.file_name or request.file_name.strip() == "":
        raise HTTPException(status_code=400, detail="Please upload a file to chat or provide a file name.")

    if not os.path.exists(uploaded_dir) or not os.listdir(uploaded_dir):
        raise HTTPException(status_code=400, detail="No uploaded PDFs found. Please upload a file first.")

    file_path = os.path.join(uploaded_dir, request.file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Specified PDF file not found.")

    answer = get_answer(file_name=request.file_name, query=request.query)
    return {"response": answer}



