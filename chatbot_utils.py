import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from pinecone import Pinecone, ServerlessSpec

import google.generativeai as genai

# Set API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # e.g., "us-east-1"

genai.configure(api_key=GOOGLE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
model = ChatGoogleGenerativeAI(model="models/gemini-1.5-pro-latest")
index_name = "pdf-chatbot"

# Ensure the index exists
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,  # Dimensions for MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
    )

index = pc.Index(index_name)

# Upload + Embed file into Pinecone
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
    index.upsert(vectors)

#  Scan uploaded_files directory
def index_uploaded_files():
    folder = "uploaded_files"
    for filename in os.listdir(folder):
        if filename.endswith(".pdf"):
            path = os.path.join(folder, filename)
            process_and_embed_file(path)

#  Create retriever based on file_name
def get_context_from_pinecone(file_name, query):
    query_embedding = embedding_function.embed_query(query)
    results = index.query(
        vector=query_embedding,
        top_k=5,
        include_metadata=True,
        filter={"file_name": {"$eq": file_name}},
    )
    matches = results.get("matches", [])
    return " ".join([m["metadata"]["text"] for m in matches]) if matches else "No relevant info found."

#  Get answer function
def get_answer(file_name: str, query: str) -> str:
    # Check if file_name is provided
    if not file_name:
        return " No file name provided. Please upload a PDF first."

    # Define retriever using Pinecone
    retriever = RunnableLambda(lambda q: get_context_from_pinecone(file_name, q))

    # Create prompt
    prompt = ChatPromptTemplate.from_template(
        """Answer the question using only the context from the file:\n{context}\n\nQuestion: {question}"""
    )

    # Define the full chain
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )

    try:
        # Invoke chain and return result
        return chain.invoke(query)
    except Exception as e:
        return f"Error during chat generation: {str(e)}"
