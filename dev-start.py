#!/usr/bin/env python3
"""
Development script to start both FastAPI backend and Next.js frontend
"""
import subprocess
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor

# Ensure UTF-8 output on Windows consoles to support emoji/log symbols
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

def start_backend():
    """Start the FastAPI backend server"""
    print("🐍 Starting FastAPI backend server...")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "src.api:app", 
            "--host", "127.0.0.1", 
            "--port", "8000", 
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n🐍 Backend server stopped")
    except Exception as e:
        print(f"❌ Backend server error: {e}")

def start_frontend():
    """Start the Next.js frontend server"""
    print("⚛️ Starting Next.js frontend server...")
    try:
        subprocess.run([
            "npm", "run", "dev"
        ], check=True, shell=True, cwd="frontend")
    except KeyboardInterrupt:
        print("\n⚛️ Frontend server stopped")
    except Exception as e:
        print(f"❌ Frontend server error: {e}")

def main():
    """Start both servers concurrently"""
    print("🚀 Starting Zivo Jewelry Chatbot Development Environment")
    print("-" * 60)
    
    # Start both servers in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            # Submit both tasks
            backend_future = executor.submit(start_backend)
            frontend_future = executor.submit(start_frontend)
            
            # Wait for both to complete (they won't unless interrupted)
            backend_future.result()
            frontend_future.result()
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down development environment...")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 