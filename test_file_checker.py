#!/usr/bin/env python3
"""Check WatchDogAI file structure and content"""

import os
from pathlib import Path

def check_file(file_path, description, min_size=100):
    """Check if a file exists and has content"""
    path = Path(file_path)
    if path.exists():
        size = path.stat().st_size
        status = "✅" if size > min_size else "⚠️ " if size > 0 else "❌"
        print(f"{status} {description}: {file_path} ({size} bytes)")
        
        # Show first few lines if file has content
        if size > 0 and size < 10000:
            try:
                with open(path, 'r') as f:
                    lines = f.readlines()[:3]
                    if lines:
                        first_line = lines[0].strip()[:60]
                        print(f"     First line: {first_line}...")
            except:
                pass
        return size > min_size
    else:
        print(f"❌ {description}: {file_path} NOT FOUND")
        return False

def main():
    print("🔍 WatchDogAI File Status Check\n")
    
    files_to_check = [
        ("src/watchdog/__init__.py", "Package init", 50),
        ("src/watchdog/config.py", "Configuration", 2000),
        ("src/watchdog/embeddings.py", "Embeddings", 5000),
        ("src/watchdog/analyzer.py", "Analyzer", 3000),
        ("src/watchdog/core.py", "Core (optional)", 10),
        ("test_analyzer.py", "Analyzer test", 1000),
        ("test_embeddings.py", "Embeddings test", 500),
        ("config/settings.yaml", "Settings YAML", 50),
        ("data/logs/sample_logs.txt", "Sample logs", 500),
        (".env", "Environment vars", 50),
        (".gitignore", "Git ignore", 100),
    ]
    
    print("📁 File Status:")
    good_files = 0
    total_files = len(files_to_check)
    
    for file_path, description, min_size in files_to_check:
        if check_file(file_path, description, min_size):
            good_files += 1
    
    print(f"\n📊 Summary: {good_files}/{total_files} files have sufficient content")
    
    if good_files < total_files:
        print(f"\n🔧 Files needing attention:")
        for file_path, description, min_size in files_to_check:
            path = Path(file_path)
            if path.exists() and path.stat().st_size < min_size:
                print(f"   {description}: {file_path}")

if __name__ == "__main__":
    main()