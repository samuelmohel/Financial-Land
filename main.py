import uvicorn
from fastapi import FastAPI
from api import router as api_router
from config import settings

# Initialize the FastAPI app
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version="1.0.0",
    description="Backend for the Financial Intelligence Platform powered by Gemini AI."
)

# Include the main query router
app.include_router(api_router, prefix="/v1")

@app.get("/")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}

if __name__ == "__main__":
    # This runs the application server
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT
    )