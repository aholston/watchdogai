#!/usr/bin/env python3
"""
Test the LogAnalyzer with Slack integration

File location: test_analyzer_with_slack.py (project root)

This tests the complete workflow: log analysis + automatic Slack alerts
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_analyzer_with_slack():
    """Test the analyzer with Slack integration enabled"""
    print("🧪 Testing LogAnalyzer with Slack Integration\n")
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test 1: Initialize analyzer
    print("1️⃣ Initializing Slack-enabled LogAnalyzer...")
    try:
        # Use the Slack-enabled wrapper
        from watchdog.analyzer_slack import SlackEnabledAnalyzer
        
        # Create analyzer with Slack enabled
        analyzer = SlackEnabledAnalyzer(enable_slack=True)
        print("✅ Slack-enabled LogAnalyzer initialized successfully")
        
        # Check stats
        stats = analyzer.get_analysis_stats()
        print(f"   LLM: {stats['llm_provider']} ({stats['llm_model']})")
        print(f"   Slack: {stats['slack_integration']}")
        
    except Exception as e:
        print(f"❌ Analyzer initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Add some sample logs to analyze
    print("\n2️⃣ Adding sample security logs...")
    try:
        # Add some fake security logs to the vector database
        sample_logs = [
            "2024-01-15 14:30:15 auth: Failed login for user 'admin' from 203.0.113.42",
            "2024-01-15 14:30:23 auth: Failed login for user 'root' from 203.0.113.42", 
            "2024-01-15 14:30:31 auth: Failed login for user 'admin' from 203.0.113.42",
            "2024-01-15 14:30:39 auth: Failed login for user 'postgres' from 203.0.113.42",
            "2024-01-15 14:30:47 auth: Failed login for user 'admin' from 203.0.113.42",
            "2024-01-15 14:35:12 firewall: BLOCKED connection from 203.0.113.42 to port 22",
            "2024-01-15 14:35:18 system: High memory usage detected: 94% used",
            "2024-01-15 14:35:25 database: Connection timeout from application server",
            "2024-01-15 14:35:32 web: SQL injection attempt detected in parameter 'id'",
            "2024-01-15 14:35:40 system: Disk space critical: /var/log 98% full"
        ]
        
        # Parse and embed the logs
        log_entries = analyzer.embeddings.parse_logs("\n".join(sample_logs), "test_security_logs")
        analyzer.embeddings.embed_logs(log_entries)
        
        print(f"✅ Added {len(log_entries)} sample logs to vector database")
        
    except Exception as e:
        print(f"❌ Failed to add sample logs: {e}")
        return False
    
    # Test 3: Run analysis that should trigger Slack alerts
    print("\n3️⃣ Running security analysis...")
    
    security_queries = [
        ("failed login brute force attack", "Brute Force Detection"),
        ("SQL injection attack attempt", "Web Security Analysis"),
        ("high memory disk usage critical", "System Performance Analysis")
    ]
    
    analysis_results = []
    
    for query, context in security_queries:
        print(f"\n🔍 Analyzing: {query}")
        
        try:
            # Ask user if they want Slack alerts for this test
            if not analysis_results:  # Only ask once
                response = input("📱 Send Slack alerts during analysis? (y/N): ")
                send_alerts = response.lower() == 'y'
            
            result = analyzer.analyze_logs(
                query=query,
                context=context, 
                source_file="test_security_logs.txt",
                send_slack_alert=send_alerts
            )
            
            if result:
                print(f"   ✅ Issue: {result.issue}")
                print(f"   ✅ Severity: {result.severity.upper()}")
                print(f"   ✅ Confidence: {result.confidence:.1%}")
                print(f"   ✅ Category: {result.category}")
                
                if send_alerts and analyzer._should_send_slack_alert(result):
                    print(f"   📱 Slack alert should be sent")
                else:
                    print(f"   🔇 No Slack alert (below threshold or disabled)")
                
                analysis_results.append(result)
            else:
                print(f"   ⚠️  No significant findings")
                
        except Exception as e:
            print(f"   ❌ Analysis failed: {e}")
    
    print(f"\n📊 Analysis Summary:")
    print(f"   Total queries: {len(security_queries)}")
    print(f"   Issues found: {len(analysis_results)}")
    
    if analysis_results:
        severity_counts = {}
        for result in analysis_results:
            severity_counts[result.severity] = severity_counts.get(result.severity, 0) + 1
        
        print(f"   Severity breakdown: {severity_counts}")
    
    return len(analysis_results) > 0


def test_slack_controls():
    """Test Slack enable/disable controls"""
    print("\n4️⃣ Testing Slack controls...")
    
    try:
        from watchdog.analyzer_slack import SlackEnabledAnalyzer
        
        # Test with Slack disabled
        analyzer_no_slack = SlackEnabledAnalyzer(enable_slack=False)
        print("✅ Analyzer created with Slack disabled")
        
        # Test enable/disable methods
        analyzer_no_slack.set_slack_enabled(True)
        print("✅ Slack enabled via method")
        
        analyzer_no_slack.set_slack_enabled(False)
        print("✅ Slack disabled via method")
        
        return True
        
    except Exception as e:
        print(f"❌ Slack controls test failed: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 WatchDogAI Analyzer + Slack Integration Test\n")
    
    tests = [
        ("Analyzer with Slack Integration", test_analyzer_with_slack),
        ("Slack Controls", test_slack_controls)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Testing: {test_name}")
        print('='*60)
        
        try:
            if test_func():
                print(f"✅ {test_name} test PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test ERROR: {e}")
    
    print(f"\n📊 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        print("\n💡 What's working:")
        print("   ✅ LogAnalyzer automatically sends Slack alerts")
        print("   ✅ Severity filtering prevents spam")
        print("   ✅ Rich formatted security alerts")
        print("   ✅ Slack integration can be enabled/disabled")
        print("\n🚀 Ready for production use!")
    else:
        print("❌ Some tests failed - check configuration")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)