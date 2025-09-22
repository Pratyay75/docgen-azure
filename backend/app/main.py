# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers from app.routes
from app.routes.document_routes import router as documents_router
from app.routes.template_routes import router as templates_router
from app.routes.user_routes import router as users_router
from app.routes.company_routes import router as companies_router
from app.routes.admin_routes import router as admin_router
from app.routes.config_routes import router as config_router

# Initialize FastAPI app
app = FastAPI(
    title="DocGen Backend (JSON store, local dev)",
    version="1.0.0",
    description="Backend service for document generation and management."
)

# CORS Middleware (adjust allow_origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(templates_router, prefix="/api/templates", tags=["templates"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])  # ✅ documents router
app.include_router(companies_router, prefix="/api/companies", tags=["companies"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(config_router, prefix="/api/config", tags=["config"])

# Root endpoint
@app.get("/")
def root():
    return {"status": "ok", "message": "DocGen backend running"}
