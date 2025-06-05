"""
WatchDogAI Integrations Package

File location: src/watchdog/integrations/__init__.py

This package contains integrations with external services like Slack, email, and SIEM tools.
"""

from .slack import SlackNotifier, send_security_alert, test_slack_integration

__all__ = [
    "SlackNotifier", 
    "send_security_alert", 
    "test_slack_integration"
]