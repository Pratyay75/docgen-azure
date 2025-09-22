import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# ---------------------------
# Load environment variables
# ---------------------------
load_dotenv()

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# Import routers
# ---------------------------
from app.routes.document_routes import router as documents_router
from app.routes.template_routes import router as templates_router
from app.routes.user_routes import router as users_router
from app.routes.company_routes import router as companies_router
from app.routes.admin_routes import router as admin_router
from app.routes.config_routes import router as config_router

# ---------------------------
# Initialize FastAPI app
# ---------------------------
app = FastAPI(
    title="DocGen Backend",
    version="1.0.0",
    description="Backend service for document generation and management."
)

# ---------------------------
# CORS Middleware
# ---------------------------
allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Register routers (API routes under /api/*)
# ---------------------------
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(templates_router, prefix="/api/templates", tags=["templates"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(companies_router, prefix="/api/companies", tags=["companies"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(config_router, prefix="/api/config", tags=["config"])

# ---------------------------
# Serve React frontend (built files)
# ---------------------------
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), "frontend/build")

if os.path.exists(FRONTEND_BUILD_DIR):
    logger.info(f"✅ Serving React frontend from {FRONTEND_BUILD_DIR}")

    # Serve static files (JS, CSS, images)
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_BUILD_DIR, "static")), name="static")

    # SPA fallback: serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api/"):  # don’t override API routes
            return {"error": "API route not found"}
        index_path = os.path.join(FRONTEND_BUILD_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend not built yet. Please run npm run build."}

# ---------------------------
# Root endpoint
# ---------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "DocGen backend running"}
