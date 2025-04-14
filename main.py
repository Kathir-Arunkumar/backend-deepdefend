from fastapi import FastAPI
from auth import auth_router
from dashboard import dashboard_router
from pyngrok import ngrok
import uvicorn
# main.py
from chatbot_utils import index_uploaded_files

# Call this at app startup
index_uploaded_files()


# Initialize FastAPI app
app = FastAPI()

# Include authentication routes
app.include_router(auth_router, prefix="/auth")

# Include Dashboard Routes
app.include_router(dashboard_router, prefix="/dashboard")

# Root Endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the Login System!"}




if __name__ == "__main__":
    port = 8000
    ngrok.set_auth_token("2vEKBq30aFmJhwsUb577SZW5bkw_5DdN9KsR6ECiWVFprkVEZ")
    ngrok_tunnel = ngrok.connect(port)
    print(f"Public URL: {ngrok_tunnel.public_url}")
    uvicorn.run(app, host="0.0.0.0",port=port)