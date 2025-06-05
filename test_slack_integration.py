#!/usr/bin/env python3
"""
Test script for Slack integration

File location: test_slack_integration.py (project root)

Usage:
1. Set SLACK_WEBHOOK_URL in your .env file
2. Run: python test_slack_integration.py
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_slack_setup():
    """Test Slack integration setup and configuration"""
    print("🧪 Testing WatchDogAI Slack Integration\n")
    
    # Check environment variables
    print("1️⃣ Checking environment configuration...")
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    channel = os.getenv("SLACK_CHANNEL", "#security-alerts")
    username = os.getenv("SLACK_USERNAME", "WatchDogAI")
    min_severity = os.getenv("SLACK_MIN_SEVERITY", "medium")
    
    if webhook_url:
        print(f"✅ SLACK_WEBHOOK_URL: configured")
        print(f"✅ SLACK_CHANNEL: {channel}")
        print(f"✅ SLACK_USERNAME: {username}")
        print(f"✅ SLACK_MIN_SEVERITY: {min_severity}")
    else:
        print("❌ SLACK_WEBHOOK_URL not found in environment")
        print("💡 Add to your .env file:")
        print("   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        print("   SLACK_CHANNEL=#security-alerts")
        print("   SLACK_USERNAME=WatchDogAI")
        print("   SLACK_MIN_SEVERITY=medium")
        return False
    
    # Test imports
    print("\n2️⃣ Testing imports...")
    try:
        from watchdog.integrations.slack import SlackNotifier, test_slack_integration
        print("✅ Slack integration module imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test SlackNotifier initialization
    print("\n3️⃣ Testing SlackNotifier initialization...")
    try:
        notifier = SlackNotifier()
        print(f"✅ SlackNotifier initialized")
        print(f"   Enabled: {notifier.enabled}")
        print(f"   Channel: {notifier.channel}")
        print(f"   Username: {notifier.username}")
        
        if not notifier.enabled:
            print("❌ Slack integration not enabled - check webhook URL")
            return False
            
    except Exception as e:
        print(f"❌ SlackNotifier initialization failed: {e}")
        return False
    
    # Test status method
    print("\n4️⃣ Testing status method...")
    try:
        status = notifier.get_status()
        print(f"✅ Status: {status}")
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False
    
    return True


def test_slack_message():
    """Test sending an actual Slack message"""
    print("\n5️⃣ Testing actual Slack message sending...")
    
    try:
        from watchdog.integrations.slack import test_slack_integration
        
        # Ask user for confirmation
        response = input("🤔 Send test message to Slack? (y/N): ")
        if response.lower() != 'y':
            print("⏭️  Skipping message test")
            return True
        
        print("📤 Sending test message to Slack...")
        success = test_slack_integration()
        
        if success:
            print("✅ Test message sent successfully!")
            print("   Check your Slack channel for the message")
            return True
        else:
            print("❌ Test message failed")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False


def test_security_recommendation():
    """Test sending a SecurityRecommendation to Slack"""
    print("\n6️⃣ Testing SecurityRecommendation integration...")
    
    try:
        from watchdog.integrations.slack import send_security_alert
        from watchdog.analyzer import SecurityRecommendation
        
        # Ask user for confirmation
        response = input("🤔 Send sample security alert to Slack? (y/N): ")
        if response.lower() != 'y':
            print("⏭️  Skipping security alert test")
            return True
        
        # Create sample security recommendation
        sample_recommendation = SecurityRecommendation(
            issue="Multiple failed login attempts detected",
            recommendation="Implement fail2ban to block suspicious IP addresses. Review authentication logs for patterns.",
            severity="high",
            confidence=0.92,
            category="security",
            affected_systems=["web-server", "auth-service"],
            timeline="immediate",
            log_evidence=[
                "2024-01-01 14:30:15 auth: Failed login for user 'admin' from 203.0.113.42",
                "2024-01-01 14:30:23 auth: Failed login for user 'root' from 203.0.113.42",
                "2024-01-01 14:30:31 auth: Failed login for user 'admin' from 203.0.113.42"
            ]
        )
        
        print("📤 Sending sample security alert to Slack...")
        success = send_security_alert(sample_recommendation, "test_logs.txt")
        
        if success:
            print("✅ Security alert sent successfully!")
            print("   Check your Slack channel for the formatted alert")
            return True
        else:
            print("❌ Security alert failed")
            return False
            
    except Exception as e:
        print(f"❌ Error sending security alert: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 WatchDogAI Slack Integration Test\n")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    tests = [
        ("Setup & Configuration", test_slack_setup),
        ("Slack Message", test_slack_message), 
        ("Security Alert", test_security_recommendation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Testing: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                print(f"✅ {test_name} test PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            print(f"❌ {test_name} test ERROR: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Slack integration tests passed!")
        print("\n💡 Next steps:")
        print("   1. Add Slack alerts to your log analysis workflow")
        print("   2. Configure severity thresholds")
        print("   3. Test with real log files")
    else:
        print("❌ Some tests failed - check configuration and try again")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)