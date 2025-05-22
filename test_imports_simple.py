#!/usr/bin/env python3
"""Simple import test to identify missing content"""

import sys
sys.path.append('src')

def test_import(module_name, description):
    """Test importing a module"""
    try:
        print(f"Testing {description}...")
        module = __import__(module_name)
        print(f"✅ {description} imported successfully")
        
        # Show what's available
        items = [item for item in dir(module) if not item.startswith('_')]
        if items:
            print(f"   Available: {', '.join(items[:5])}{'...' if len(items) > 5 else ''}")
        else:
            print(f"   ⚠️  Module is empty")
        return True
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def test_function_import(module_name, function_name, description):
    """Test importing a specific function"""
    try:
        print(f"Testing {description}...")
        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)
        print(f"✅ {description} imported successfully")
        return True
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def main():
    print("🧪 Testing WatchDogAI Imports\n")
    
    # Test basic module imports
    tests = [
        ("watchdog", "Main package"),
        ("watchdog.config", "Config module"),
        ("watchdog.embeddings", "Embeddings module"), 
        ("watchdog.analyzer", "Analyzer module"),
    ]
    
    print("1️⃣ Testing module imports:")
    for module_name, description in tests:
        test_import(module_name, description)
        print()
    
    # Test specific function imports
    print("2️⃣ Testing specific functions:")
    function_tests = [
        ("watchdog.config", "get_config", "get_config function"),
        ("watchdog.embeddings", "LogEmbeddings", "LogEmbeddings class"),
        ("watchdog.analyzer", "LogAnalyzer", "LogAnalyzer class"),
    ]
    
    for module_name, function_name, description in function_tests:
        test_function_import(module_name, function_name, description)
        print()
    
    print("3️⃣ Testing end-to-end flow:")
    try:
        from watchdog.config import get_config
        from watchdog.embeddings import LogEmbeddings  
        from watchdog.analyzer import LogAnalyzer
        
        print("✅ All core imports working!")
        print("   Ready to test with actual data")
    except Exception as e:
        print(f"❌ End-to-end import failed: {e}")

if __name__ == "__main__":
    main()