import os
import pinecone
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Set API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # e.g., "us-east-1"

# Configure Google API for generative models
genai.configure(api_key=GOOGLE_API_KEY)

# Set up Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)
embedding_function = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",  # aka textembedding-gecko
    task_type="retrieval_document",  # Optional: can be "retrieval_query", etc.
    google_api_key=GOOGLE_API_KEY
)

model = ChatGoogleGenerativeAI(model="models/gemini-1.5-pro-latest")
index_name = "pdf-context-index"

# Ensure the index exists
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=768,  # Dimensions for MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
    )

index = pc.Index(index_name)

# Helper function to process and embed file
def process_and_embed_file(file_path):
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    embeddings = embedding_function.embed_documents([c.page_content for c in chunks])

    file_name = os.path.basename(file_path)

    # Insert with metadata
    vectors = [
        (f"{file_name}_{i}", emb, {"text": chunk.page_content, "file_name": file_name})
        for i, (emb, chunk) in enumerate(zip(embeddings, chunks))
    ]
    print(f"Indexing {len(vectors)} chunks from file: {file_name}")  # Log number of chunks
    index.upsert(vectors)

# Function to index uploaded PDF files
def index_uploaded_files():
    folder = "uploaded_files"
    for filename in os.listdir(folder):
        if filename.endswith(".pdf"):
            path = os.path.join(folder, filename)
            process_and_embed_file(path)

# Function to retrieve context from Pinecone based on file_name
def get_context_from_pinecone(file_name, query):
    query_embedding = embedding_function.embed_query(query)
    print(f"Query embedding: {query_embedding}")  # Log the query embedding
    results = index.query(
        vector=query_embedding,
        top_k=5,
        include_metadata=True,
        filter={"file_name": {"$eq": file_name}},
    )
    print(f"Results: {results}")  # Log the results from Pinecone
    matches = results.get("matches", [])
    return " ".join([m["metadata"]["text"] for m in matches]) if matches else "No relevant info found."

# Function to get the answer from the chatbot
def get_answer(file_name: str, query: str) -> str:
    # Check if file_name and query are provided
    if not file_name or not query:
        return " Please provide both a file name and a query."

    # Define retriever using Pinecone
    retriever = RunnableLambda(lambda q: get_context_from_pinecone(file_name, q))

    # Create prompt
    prompt = ChatPromptTemplate.from_template(
        """Answer the question using only the context from the file:\n{context}\n\nQuestion: {question}"""
    )

    # Define the full chain
    chain = (
        {"context": retriever, "question": RunnablePassthrough() }
        | prompt
        | model
        | StrOutputParser()
    )

    try:
        # Invoke the chain and return result
        return chain.invoke(query)
    except Exception as e:
        return f"❌ Error during chat generation: {str(e)}"
