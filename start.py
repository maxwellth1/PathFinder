#!/usr/bin/env python3
"""
Startup script for Zivo AI API deployment
"""
import os
import sys
import uvicorn
from pathlib import Path

def main():
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Add the project root to Python path
    sys.path.insert(0, str(script_dir))
    
    # Get port from environment
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting Zivo Jewelry Chatbot API server on {host}:{port}...")
    
    # Run the server
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main() 