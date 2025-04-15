import os
import time
import fitz  # PyMuPDF
from dotenv import load_dotenv
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from models import SearchResult

# Load environment variables
load_dotenv()

# Access keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = "pdf-search-index"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Create Pinecone index if not exists
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    # Wait until index is ready
    while not pc.describe_index(INDEX_NAME).status['ready']:
        time.sleep(1)

# Load the index
index = pc.Index(INDEX_NAME)


# 1. Extract full text from PDF
def extract_text_from_pdf(file_path: str) -> str:
    doc = fitz.open(file_path)
    return "".join([page.get_text() for page in doc])

# 2. Chunk text using LangChain
def chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_text(text)

# 3. Get embedding from Gemini
def get_embedding(text: str) -> List[float]:
    res = genai.embed_content(
        model="models/embedding-001",
        content=text,
        task_type="retrieval_document"
    )
    embedding = res['embedding']
    print(f"Embedding size: {len(embedding)}")  # Check embedding size
    return embedding

# 4. Index one PDF
def index_pdf_to_pinecone(file_path: str) -> int:
    file_name = os.path.basename(file_path)
    text = extract_text_from_pdf(file_path)
    chunks = chunk_text(text)
    vectors = []
    print(f"Indexing {file_name}, with {len(chunks)} chunks.")  # Add logging

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        vectors.append((
            f"{file_name}_{i}", emb,
            {"text": chunk, "file_name": file_name, "source": "app_upload"}
        ))

    index.upsert(vectors)
    return len(chunks)

# 5. Index all uploaded PDFs
def index_uploaded_pdfs(upload_folder="./uploaded_files"):
    for file in os.listdir(upload_folder):
        if file.endswith(".pdf"):
            file_path = os.path.join(upload_folder, file)
            print(f"Indexing {file_path}...")
            indexed_chunks = index_pdf_to_pinecone(file_path)
            print(f"✅ Indexed {indexed_chunks} chunks from {file}")

# 6. Search uploaded files only
def search_pdf_by_context(query: str) -> List[SearchResult]:
    query_emb = get_embedding(query)
    print(f"Query Embedding: {query_emb[:5]}")  # Debugging: Check query embedding

    result = index.query(
        vector=query_emb,
        top_k=5, 
        include_metadata=True,
        filter={"source": {"$eq": "app_upload"}}  # Only search uploaded files
    )
    
    print(f"Search Result: {result}")  # Debugging: Check result

    seen = set()
    results: List[SearchResult] = []

    for match in result['matches']:
        metadata = match['metadata']
        file = metadata.get('file_name', 'unknown.pdf')
        snippet = metadata.get('text', '')[:200].replace("\n", " ") + "..."
        score = match.get('score', 0.0)

        if file not in seen:
            seen.add(file)
            results.append(SearchResult(file_name=file, snippet=snippet, score=score))
        print("hello -------------------------")
        print(result)
    return results

if __name__ == "__main__":
    # Create upload directory if it doesn't exist
    if not os.path.exists("./uploaded_files"):
        os.makedirs("./uploaded_files")
        print("Created ./uploaded_files directory")
    
    # Index all PDFs in the upload directory
    index_uploaded_pdfs("./uploaded_files")
    print("Indexing complete!")
