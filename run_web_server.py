#!/usr/bin/env python3
"""
Development server for WatchDogAI Web Dashboard
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from watchdog.web_api import WatchDogAPI

if __name__ == "__main__":
    print("🔧 Starting WatchDogAI Development Server")
    print("📡 API will be available at: http://localhost:5001")
    print("🔍 API endpoints:")
    print("   GET  /api/health")
    print("   GET  /api/status") 
    print("   POST /api/upload")
    print("   POST /api/analyze")
    print("   POST /api/search")
    print("   POST /api/analyze-query")
    print("   GET  /api/report")
    print("\n⚠️  Make sure your .env file has ANTHROPIC_API_KEY set!")
    print("🛑 Press Ctrl+C to stop the server\n")
    
    api = WatchDogAPI()
    api.run(host='0.0.0.0', port=5001, debug=True)