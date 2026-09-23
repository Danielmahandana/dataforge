"""
Darkroom DataForge - Development Server Runner
Starts the FastAPI backend server on http://127.0.0.1:8000
"""
import sys
import os
from pathlib import Path

# Add project root and backend directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  DARKROOM DATAFORGE - Backend Server")
    print("  Wits-merSETA Darkroom Document Intelligence Platform")
    print("  API Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
