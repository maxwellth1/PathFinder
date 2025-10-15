#!/usr/bin/env python3
"""
Health Check Test Suite for Path Finder Chatbot
Tests both FastAPI backend and Next.js frontend to ensure proper functionality
"""

import requests
import time
import sys
import subprocess
import json
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

class HealthChecker:
    def __init__(self):
        self.backend_url = "http://127.0.0.1:8000"
        self.frontend_url = "http://localhost:3000"
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
    
    def print_test(self, test_name: str, status: str, details: str = ""):
        """Print individual test results"""
        self.total_tests += 1
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{status_icon} {test_name:<40} [{status}]")
        if details:
            print(f"   └─ {details}")
        if status == "PASS":
            self.passed_tests += 1
    
    def test_backend_health(self) -> bool:
        """Test FastAPI backend health endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.print_test("Backend Health Check", "PASS", 
                                  f"Response: {data.get('message', 'OK')}")
                    return True
                else:
                    self.print_test("Backend Health Check", "FAIL", 
                                  f"Unhealthy status: {data}")
                    return False
            else:
                self.print_test("Backend Health Check", "FAIL", 
                              f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_test("Backend Health Check", "FAIL", 
                          f"Connection error: {str(e)}")
            return False
    
    def test_backend_info(self) -> bool:
        """Test FastAPI backend info endpoint"""
        try:
            response = requests.get(f"{self.backend_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "Zivo Jewelry Chatbot API" in data.get("message", ""):
                    self.print_test("Backend Info Endpoint", "PASS", 
                                  f"Version: {data.get('version', 'Unknown')}")
                    return True
                else:
                    self.print_test("Backend Info Endpoint", "FAIL", 
                                  f"Unexpected response: {data}")
                    return False
            else:
                self.print_test("Backend Info Endpoint", "FAIL", 
                              f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_test("Backend Info Endpoint", "FAIL", 
                          f"Connection error: {str(e)}")
            return False
    
    def test_frontend_availability(self) -> bool:
        """Test Next.js frontend availability"""
        try:
            response = requests.get(self.frontend_url, timeout=10)
            if response.status_code == 200:
                # Check if it's actually the Next.js app
                if "Zivo" in response.text or "next" in response.headers.get("x-powered-by", "").lower():
                    self.print_test("Frontend Availability", "PASS", 
                                  "Next.js application responding")
                    return True
                else:
                    self.print_test("Frontend Availability", "FAIL", 
                                  "Response doesn't appear to be Next.js app")
                    return False
            else:
                self.print_test("Frontend Availability", "FAIL", 
                              f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_test("Frontend Availability", "FAIL", 
                          f"Connection error: {str(e)}")
            return False
    
    def test_frontend_api_chat(self) -> bool:
        """Test Next.js chat API route (GET request for info)"""
        try:
            response = requests.get(f"{self.frontend_url}/api/chat", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "Chat API endpoint" in data.get("message", ""):
                    self.print_test("Frontend Chat API Route", "PASS", 
                                  f"Backend URL: {data.get('backend_url', 'Unknown')}")
                    return True
                else:
                    self.print_test("Frontend Chat API Route", "FAIL", 
                                  f"Unexpected response: {data}")
                    return False
            else:
                self.print_test("Frontend Chat API Route", "FAIL", 
                              f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_test("Frontend Chat API Route", "FAIL", 
                          f"Connection error: {str(e)}")
            return False
    
    def test_frontend_api_stream(self) -> bool:
        """Test Next.js stream API route (GET request for info)"""
        try:
            response = requests.get(f"{self.frontend_url}/api/chat/stream", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "Streaming Chat API endpoint" in data.get("message", ""):
                    self.print_test("Frontend Stream API Route", "PASS", 
                                  "Streaming endpoint available")
                    return True
                else:
                    self.print_test("Frontend Stream API Route", "FAIL", 
                                  f"Unexpected response: {data}")
                    return False
            else:
                self.print_test("Frontend Stream API Route", "FAIL", 
                              f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_test("Frontend Stream API Route", "FAIL", 
                          f"Connection error: {str(e)}")
            return False
    
    def test_backend_chat_endpoint(self) -> bool:
        """Test FastAPI chat endpoint with a simple message"""
        try:
            test_message = {"message": "Hello, this is a test message"}
            response = requests.post(
                f"{self.backend_url}/api/chat", 
                json=test_message, 
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("response"):
                    self.print_test("Backend Chat Endpoint", "PASS", 
                                  f"Response received: {len(data.get('response', ''))} chars")
                    return True
                else:
                    self.print_test("Backend Chat Endpoint", "FAIL", 
                                  f"Invalid response format: {data}")
                    return False
            else:
                self.print_test("Backend Chat Endpoint", "FAIL", 
                              f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.print_test("Backend Chat Endpoint", "FAIL", 
                          f"Connection error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all health check tests"""
        print("🚀 Starting Health Check Tests for Zivo Jewelry Chatbot")
        print(f"Backend URL: {self.backend_url}")
        print(f"Frontend URL: {self.frontend_url}")
        
        # Test Backend
        self.print_header("FastAPI Backend Tests")
        backend_health = self.test_backend_health()
        backend_info = self.test_backend_info()
        
        # Test Frontend
        self.print_header("Next.js Frontend Tests")
        frontend_available = self.test_frontend_availability()
        frontend_chat_api = self.test_frontend_api_chat()
        frontend_stream_api = self.test_frontend_api_stream()
        
        # Test Integration (only if backend is healthy)
        self.print_header("Integration Tests")
        if backend_health:
            backend_chat = self.test_backend_chat_endpoint()
        else:
            self.print_test("Backend Chat Endpoint", "SKIP", 
                          "Backend health check failed")
            backend_chat = False
        
        # Summary
        self.print_header("Test Summary")
        print(f"✅ Passed: {self.passed_tests}/{self.total_tests} tests")
        print(f"❌ Failed: {self.total_tests - self.passed_tests}/{self.total_tests} tests")
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 All tests passed! Your application is healthy and ready to use.")
            return True
        else:
            print(f"\n⚠️  Some tests failed. Please check the details above.")
            return False
    
    def run_with_retry(self, max_retries: int = 3, delay: int = 2):
        """Run tests with retry logic for server startup"""
        print(f"🔄 Running health checks with up to {max_retries} retries...")
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"\n🔄 Retry attempt {attempt + 1}/{max_retries}")
                time.sleep(delay)
            
            success = self.run_all_tests()
            if success:
                return True
        
        print(f"\n❌ Health checks failed after {max_retries} attempts")
        return False


def main():
    """Main function to run health checks"""
    print("🏥 Zivo Jewelry Chatbot - Health Check Suite")
    print("=" * 60)
    
    checker = HealthChecker()
    
    # Check if we should run with retries (useful for CI/CD)
    if len(sys.argv) > 1 and sys.argv[1] == "--retry":
        success = checker.run_with_retry()
    else:
        success = checker.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 