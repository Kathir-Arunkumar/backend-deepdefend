from fastapi import FastAPI
from auth import auth_router
from dashboard import dashboard_router

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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)