"""
FastAPI application entry point.

Run with: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from poly_boost.api.routes import positions, trading, wallets
from poly_boost.api.dependencies import initialize_services


# Create FastAPI app
app = FastAPI(
    title="Polymarket Copy Trading Bot API",
    description="REST API for managing Polymarket copy trading operations",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    initialize_services()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Polymarket Copy Trading Bot API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(positions.router)
app.include_router(trading.router)
app.include_router(wallets.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
