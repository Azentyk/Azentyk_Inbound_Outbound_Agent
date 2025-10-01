# app/main.py
from fastapi import FastAPI, Request
from routes import voice
from utils.logger import setup_logging

# Initialize logging first
logger = setup_logging()

def create_app():
    app = FastAPI(title="Azentyk Voice API")

    # Include routers
    app.include_router(voice.router, prefix="")

    # Add middleware to log each request
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"➡️ Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"⬅️ Response: {response.status_code} for {request.url}")
        return response

    return app

app = create_app()

@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting Azentyk Voice API")

@app.on_event("shutdown")
async def shutdown():
    logger.info("🛑 Stopping Azentyk Voice API")
