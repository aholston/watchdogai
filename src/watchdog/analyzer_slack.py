"""
Slack-enabled wrapper for LogAnalyzer

File location: src/watchdog/analyzer_slack.py

This extends the existing LogAnalyzer with Slack notification capabilities
without modifying the original analyzer.py file.
"""

from typing import Optional, List
import os

from .analyzer import LogAnalyzer, SecurityRecommendation


class SlackEnabledAnalyzer:
    """Wrapper that adds Slack notifications to existing LogAnalyzer"""
    
    def __init__(self, enable_slack: bool = True):
        # Initialize the original analyzer
        self.analyzer = LogAnalyzer()
        self.slack_enabled = enable_slack
        self.slack_notifier = None
        
        if enable_slack:
            self._initialize_slack()
    
    def _initialize_slack(self):
        """Initialize Slack integration"""
        try:
            from .integrations.slack import SlackNotifier
            self.slack_notifier = SlackNotifier()
            
            if self.slack_notifier.enabled:
                print(f"✅ Slack integration enabled → {self.slack_notifier.channel}")
            else:
                print("💬 Slack integration available but not configured")
                
        except ImportError:
            print("⚠️  Slack integration module not found")
            self.slack_notifier = None
        except Exception as e:
            print(f"⚠️  Slack initialization error: {e}")
            self.slack_notifier = None
    
    def analyze_logs(self, query: str, context: str = "General log analysis", 
                    source_file: Optional[str] = None, 
                    send_slack_alert: bool = True) -> Optional[SecurityRecommendation]:
        """Analyze logs with optional Slack notifications"""
        
        # Use the original analyzer
        result = self.analyzer.analyze_logs(query, context)
        
        # Send Slack alert if enabled and conditions are met
        if result and send_slack_alert and self._should_send_slack_alert(result):
            self._send_slack_alert(result, source_file)
        
        return result
    
    def analyze_recent_logs(self, hours: int = 1, context: str = "Recent activity analysis",
                          send_slack_alerts: bool = True) -> List[SecurityRecommendation]:
        """Analyze recent logs with optional Slack notifications"""
        
        # Use original analyzer
        results = self.analyzer.analyze_recent_logs(hours, context)
        
        # Send individual alerts
        if send_slack_alerts:
            for result in results:
                if self._should_send_slack_alert(result):
                    self._send_slack_alert(result, "recent_logs")
        
        return results
    
    def _should_send_slack_alert(self, recommendation: SecurityRecommendation) -> bool:
        """Determine if a recommendation should trigger a Slack alert"""
        if not self.slack_enabled or not self.slack_notifier or not self.slack_notifier.enabled:
            return False
        
        # Check minimum confidence threshold
        if recommendation.confidence < 0.5:
            return False
        
        # Always send for high severity issues
        if recommendation.severity in ["high", "critical"]:
            return True
        
        # Send medium severity security issues
        if recommendation.severity == "medium" and recommendation.category == "security":
            return True
        
        # Skip low severity and unknown categories
        return False
    
    def _send_slack_alert(self, recommendation: SecurityRecommendation, source_file: Optional[str] = None):
        """Send Slack alert for a security recommendation"""
        try:
            success = self.slack_notifier.send_security_alert(recommendation, source_file)
            if success:
                print(f"📱 Slack alert sent: {recommendation.issue}")
            else:
                print(f"📱 Slack alert failed: {recommendation.issue}")
        except Exception as e:
            print(f"📱 Slack alert error: {e}")
    
    def set_slack_enabled(self, enabled: bool):
        """Enable or disable Slack notifications"""
        self.slack_enabled = enabled
        if not enabled:
            print("🔇 Slack notifications disabled")
        elif self.slack_notifier and self.slack_notifier.enabled:
            print("📱 Slack notifications enabled")
        else:
            print("⚠️  Slack notifications requested but not configured")
    
    def get_slack_status(self) -> dict:
        """Get Slack integration status"""
        if self.slack_notifier:
            return self.slack_notifier.get_status()
        else:
            return {"enabled": False, "error": "Slack notifier not initialized"}
    
    # Delegate other methods to the original analyzer
    def get_analysis_stats(self):
        """Get analysis stats including Slack status"""
        stats = self.analyzer.get_analysis_stats()
        stats['slack_integration'] = self.get_slack_status()
        return stats
    
    @property
    def embeddings(self):
        """Access to embeddings for testing"""
        return self.analyzer.embeddings