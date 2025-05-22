#!/usr/bin/env python3
"""Test the actual LogAnalyzer methods that exist"""

import sys
sys.path.append('src')

def main():
    print("🚀 Working WatchDogAI Analyzer Test\n")
    
    try:
        print("1️⃣ Testing imports...")
        from watchdog.analyzer import LogAnalyzer
        print("✅ All imports successful!")
        
        print("\n2️⃣ Testing analyzer initialization...")
        analyzer = LogAnalyzer()
        print("✅ Analyzer initialized!")
        
        print("\n3️⃣ Checking available methods...")
        methods = [method for method in dir(analyzer) if not method.startswith('_') and callable(getattr(analyzer, method))]
        print(f"Available methods: {', '.join(methods)}")
        
        print("\n4️⃣ Testing log analysis...")
        
        # Test the actual method that exists
        if hasattr(analyzer, 'analyze_logs'):
            print("Testing analyze_logs method...")
            result = analyzer.analyze_logs(
                query="failed login attempt",
                context="security incident investigation"
            )
            
            if result:
                print(f"✅ Analysis completed!")
                print(f"   Issue: {result.issue}")
                print(f"   Severity: {result.severity}")
                print(f"   Category: {result.category}")
                print(f"   Confidence: {result.confidence}")
            else:
                print("⚠️  Analysis returned no results (normal if no logs match)")
                
        elif hasattr(analyzer, 'analyze_security_logs'):
            print("Testing analyze_security_logs method...")
            result = analyzer.analyze_security_logs("failed login attempt")
            print(f"✅ Analysis result: {result}")
            
        else:
            print("🔍 Let's try a different approach...")
            # Show what we can actually call
            for method_name in methods:
                method = getattr(analyzer, method_name)
                print(f"   - {method_name}: {method.__doc__ or 'No description'}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()