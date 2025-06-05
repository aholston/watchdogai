"""
Slack integration for WatchDogAI security alerts

File location: src/watchdog/integrations/slack.py

This module provides Slack notification capabilities for security incidents
detected by WatchDogAI. It sends formatted alerts using Slack's Block Kit API.
"""

import json
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import from parent modules
from ..config import get_config
from ..analyzer import SecurityRecommendation


class AlertSeverity(Enum):
    """Alert severity levels for Slack notifications"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SlackAlert:
    """Structured Slack alert data"""
    title: str
    severity: AlertSeverity
    issue: str
    recommendation: str
    affected_systems: List[str]
    confidence: float
    category: str
    timeline: str
    log_evidence: List[str]
    timestamp: datetime
    source_file: Optional[str] = None
    
    def to_slack_blocks(self) -> List[Dict[str, Any]]:
        """Convert alert to Slack Block Kit format"""
        # Severity emoji and color mapping
        severity_config = {
            AlertSeverity.CRITICAL: {"emoji": "🚨", "color": "#FF0000"},
            AlertSeverity.HIGH: {"emoji": "⚠️", "color": "#FF6B35"},
            AlertSeverity.MEDIUM: {"emoji": "⚡", "color": "#F7931E"},
            AlertSeverity.LOW: {"emoji": "ℹ️", "color": "#36C5F0"},
            AlertSeverity.INFO: {"emoji": "📋", "color": "#2EB67D"}
        }
        
        config = severity_config.get(self.severity, severity_config[AlertSeverity.INFO])
        
        blocks = [
            # Header with severity and title
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{config['emoji']} {self.title}"
                }
            },
            
            # Main alert information
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:* {self.severity.value.upper()}"
                    },
                    {
                        "type": "mrkdwn", 
                        "text": f"*Category:* {self.category.title()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Confidence:* {self.confidence:.0%}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timeline:* {self.timeline}"
                    }
                ]
            },
            
            # Issue description
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Issue:*\n{self.issue}"
                }
            },
            
            # Recommendation
            {
                "type": "section", 
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Recommendation:*\n{self.recommendation}"
                }
            }
        ]
        
        # Add affected systems if any
        if self.affected_systems:
            systems_text = ", ".join(self.affected_systems)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn", 
                    "text": f"*Affected Systems:* {systems_text}"
                }
            })
        
        # Add log evidence (truncated for readability)
        if self.log_evidence:
            evidence_preview = self.log_evidence[:2]  # Show first 2 entries
            evidence_text = "\n".join([f"• {log[:100]}..." if len(log) > 100 else f"• {log}" 
                                     for log in evidence_preview])
            
            if len(self.log_evidence) > 2:
                evidence_text += f"\n_...and {len(self.log_evidence) - 2} more entries_"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Log Evidence:*\n```{evidence_text}```"
                }
            })
        
        # Footer with timestamp and source
        footer_text = f"WatchDogAI • {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        if self.source_file:
            footer_text += f" • Source: {self.source_file}"
            
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": footer_text
                }
            ]
        })
        
        return blocks


class SlackNotifier:
    """Handles Slack webhook notifications for WatchDogAI alerts"""
    
    def __init__(self):
        self.config = get_config()
        # For now, we'll use environment variables directly
        # Later we'll integrate with the enhanced config system
        import os
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.channel = os.getenv("SLACK_CHANNEL", "#security-alerts")
        self.username = os.getenv("SLACK_USERNAME", "WatchDogAI")
        self.min_severity = os.getenv("SLACK_MIN_SEVERITY", "medium")
        self.enabled = bool(self.webhook_url)
        
        if not self.enabled:
            print("⚠️  Slack integration disabled - no SLACK_WEBHOOK_URL configured")
    
    def send_security_alert(self, recommendation: SecurityRecommendation, 
                          source_file: Optional[str] = None) -> bool:
        """Send a security alert to Slack"""
        if not self.enabled:
            return False
        
        # Convert SecurityRecommendation to SlackAlert
        alert = SlackAlert(
            title=f"Security Alert: {recommendation.issue}",
            severity=AlertSeverity(recommendation.severity.lower()),
            issue=recommendation.issue,
            recommendation=recommendation.recommendation,
            affected_systems=recommendation.affected_systems,
            confidence=recommendation.confidence,
            category=recommendation.category,
            timeline=recommendation.timeline,
            log_evidence=recommendation.log_evidence,
            timestamp=datetime.utcnow(),
            source_file=source_file
        )
        
        return self._send_alert(alert)
    
    def _send_alert(self, alert: SlackAlert) -> bool:
        """Send a formatted alert to Slack"""
        if not self.enabled:
            return False
        
        # Check if alert meets minimum severity threshold
        if not self._meets_severity_threshold(alert.severity):
            print(f"🔇 Alert below minimum severity threshold ({self.min_severity})")
            return False
        
        try:
            # Prepare Slack message payload
            payload = {
                "channel": self.channel,
                "username": self.username,
                "icon_emoji": ":shield:",
                "blocks": alert.to_slack_blocks()
            }
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Slack alert sent successfully: {alert.title}")
                return True
            else:
                print(f"❌ Slack alert failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending Slack alert: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """Send a test message to verify Slack integration"""
        if not self.enabled:
            print("❌ Slack integration not configured")
            return False
        
        test_alert = SlackAlert(
            title="WatchDogAI Test Alert",
            severity=AlertSeverity.INFO,
            issue="This is a test message to verify Slack integration is working correctly.",
            recommendation="No action required - this is just a connectivity test.",
            affected_systems=["test-system"],
            confidence=1.0,
            category="test",
            timeline="immediate",
            log_evidence=["2024-01-01 12:00:00 INFO WatchDogAI integration test"],
            timestamp=datetime.utcnow()
        )
        
        return self._send_alert(test_alert)
    
    def _meets_severity_threshold(self, severity: AlertSeverity) -> bool:
        """Check if alert severity meets configured minimum threshold"""
        severity_levels = {
            "critical": 4,
            "high": 3, 
            "medium": 2,
            "low": 1,
            "info": 0
        }
        
        alert_level = severity_levels.get(severity.value, 0)
        min_level = severity_levels.get(self.min_severity, 2)
        
        return alert_level >= min_level
    
    def get_status(self) -> Dict[str, Any]:
        """Get Slack integration status"""
        return {
            "enabled": self.enabled,
            "webhook_configured": bool(self.webhook_url),
            "channel": self.channel,
            "username": self.username,
            "min_severity": self.min_severity
        }


# Convenience functions for easy integration
def send_security_alert(recommendation: SecurityRecommendation, 
                       source_file: Optional[str] = None) -> bool:
    """Convenience function to send a security alert to Slack"""
    notifier = SlackNotifier()
    return notifier.send_security_alert(recommendation, source_file)


def test_slack_integration() -> bool:
    """Test Slack integration with a sample message"""
    notifier = SlackNotifier()
    return notifier.send_test_message()