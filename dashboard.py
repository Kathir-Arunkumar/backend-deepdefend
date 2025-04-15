from fastapi import APIRouter, File, UploadFile, HTTPException
from models import QueryRequest, SearchRequest, SearchResponse, SearchResult
from database import files_collection
import os
import shutil
from uuid import uuid4
from malware_scan_utils import scan_pdf_file
from extract_text import extract_text_from_pdf
from chatbot_utils import get_answer
from pdf_search_utils import index_pdf_to_pinecone, search_pdf_by_context

dashboard_router = APIRouter()

UPLOAD_DIR = "uploaded_files"
TEMP_DIR = "temp_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


# 🚀 Upload PDF (with malware scanning, text extraction, and indexing)
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

        text_content = extract_text_from_pdf(final_path)

        file_metadata = {
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": os.path.getsize(final_path),
            "storage_path": final_path,
            "extracted_text": text_content,
        }
        await files_collection.insert_one(file_metadata)

        try:
            chunk_count = index_pdf_to_pinecone(final_path, file.filename, text_content)
            await files_collection.update_one(
                {"file_name": file.filename},
                {"$set": {"indexed": True, "chunk_count": chunk_count}}
            )
        except Exception as e:
            await files_collection.update_one(
                {"file_name": file.filename},
                {"$set": {"indexed": False, "indexing_error": str(e)}}
            )

        return {"message": "File uploaded, scanned, processed, and indexed for search!", "file_name": file.filename}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 🤖 Chat with a specific PDF
@dashboard_router.post("/chat")
async def chat_with_pdf(request: QueryRequest):
    uploaded_dir = UPLOAD_DIR

    if not request.file_name or request.file_name.strip() == "":
        raise HTTPException(status_code=400, detail="Please upload a file to chat or provide a file name.")

    file_path = os.path.join(uploaded_dir, request.file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Specified PDF file not found.")

    answer = get_answer(file_name=request.file_name, query=request.query)
    return {"response": answer}


# 🔍 Semantic Search across PDFs
@dashboard_router.post("/search", response_model=SearchResponse)
async def search_pdfs(search_input: SearchRequest):
    try:
        if not search_input.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")
        results: list[SearchResult] = search_pdf_by_context(search_input.query)
        return {"matches": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 📂 List all uploaded PDFs
@dashboard_router.get("/files")
async def list_uploaded_files():
    try:
        files_cursor = files_collection.find(
            {}, {"_id": 0, "file_name": 1, "file_size": 1, "indexed": 1}
        )
        files = await files_cursor.to_list(length=None)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch uploaded files: {str(e)}")
