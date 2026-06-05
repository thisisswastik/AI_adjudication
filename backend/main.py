import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database.database import engine, Base, SessionLocal
from backend.api.claims_router import router as claims_router
from backend.api.claims_router import seed_members

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    # Auto-seed members
    logger.info("Auto-seeding members...")
    db = SessionLocal()
    try:
        seed_members(db)
    except Exception as e:
        logger.error(f"Failed to auto-seed members: {str(e)}")
    finally:
        db.close()
        
    yield
    # Shutdown actions
    logger.info("Shutting down application...")

app = FastAPI(
    title="Plum OPD Claim Adjudication Engine",
    description="Automated claim reviews, structured document extraction, and medical necessity reasoning using Gemini 2.5 Flash.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, specify Streamlit origin
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"]
)

# Register API router
app.include_router(claims_router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "opd-adjudication-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
