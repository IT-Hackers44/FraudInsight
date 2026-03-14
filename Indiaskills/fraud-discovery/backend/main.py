from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import transactions, analysis, dashboard
import os

app = FastAPI(
    title="Emerging Cyber Fraud Discovery",
    description="Full-stack system for detecting emerging fraud patterns in financial transactions",
    version="1.0.0"
)

# Initialize database
init_db()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transactions.router)
app.include_router(analysis.router)
app.include_router(dashboard.router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Emerging Cyber Fraud Discovery",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "transactions": "/api/transactions",
            "analysis": "/api/analyze",
            "dashboard": "/api/dashboard/stats",
            "patterns": "/api/patterns",
            "chains": "/api/chains",
            "health": "/api/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
