"""LLM-powered log analysis for WatchDogAI with Slack integration"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser

from .config import get_config
from .embeddings import LogEmbeddings


@dataclass
class SecurityRecommendation:
    """Structured security/ops recommendation"""
    issue: str
    recommendation: str
    severity: str  # "low", "medium", "high", "critical"
    confidence: float  # 0.0 to 1.0
    category: str  # "security", "performance", "availability", "compliance"
    affected_systems: List[str]
    timeline: str  # "immediate", "short-term", "medium-term"
    log_evidence: List[str]  # Supporting log entries


class RecommendationParser(BaseOutputParser):
    """Parse LLM response into structured recommendation"""
    
    def parse(self, text: str) -> SecurityRecommendation:
        """Parse LLM JSON response into SecurityRecommendation object"""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = text.strip()
            if json_text.startswith("```json"):
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif json_text.startswith("```"):
                json_text = json_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_text)
            
            return SecurityRecommendation(
                issue=data.get("issue", "Unknown issue"),
                recommendation=data.get("recommendation", "No recommendation provided"),
                severity=str(data.get("severity", "medium")).lower(),
                confidence=float(data.get("confidence", 0.5)),
                category=str(data.get("category", "unknown")).lower(),
                affected_systems=data.get("affected_systems", []) if isinstance(data.get("affected_systems"), list) else [],
                timeline=str(data.get("timeline", "medium-term")).lower(),
                log_evidence=data.get("log_evidence", []) if isinstance(data.get("log_evidence"), list) else []
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback for unparseable responses
            return SecurityRecommendation(
                issue="Failed to parse LLM response",
                recommendation="Review logs manually for potential issues",
                severity="low",
                confidence=0.1,
                category="unknown",
                affected_systems=[],
                timeline="medium-term",
                log_evidence=[text[:200] + "..." if len(text) > 200 else text]
            )


class LogAnalyzer:
    """Main log analysis engine using LLM with Slack integration"""
    
    def __init__(self, enable_slack: bool = True):
        self.config = get_config()
        self.llm = None
        self.embeddings = LogEmbeddings()
        self.slack_notifier = None
        self.slack_enabled = enable_slack
        
        self._initialize_llm()
        self._initialize_slack()
        
        # Analysis prompt template
        self.analysis_prompt = PromptTemplate(
            input_variables=["log_entries", "context"],
            template="""You are WatchDogAI, an expert DevOps and Security analyst. Analyze the following log entries and provide a structured security/operations recommendation.

CONTEXT: {context}

LOG ENTRIES TO ANALYZE:
{log_entries}

Your task:
1. Identify patterns, anomalies, or security/operational issues
2. Assess the severity and potential impact
3. Provide specific, actionable recommendations
4. Consider the broader system context

Respond with ONLY a JSON object in this exact format:
{{
    "issue": "Brief description of the identified issue",
    "recommendation": "Specific, actionable steps to address the issue",
    "severity": "low|medium|high|critical",
    "confidence": 0.0-1.0,
    "category": "security|performance|availability|compliance|configuration",
    "affected_systems": ["list", "of", "affected", "systems"],
    "timeline": "immediate|short-term|medium-term|long-term",
    "log_evidence": ["specific log entries that support this analysis"]
}}

Focus on:
- Security threats (failed logins, unauthorized access, suspicious patterns)
- System performance issues (high CPU, memory, disk usage)
- Service availability problems (connection failures, timeouts)
- Configuration issues (misconfigurations, deprecated settings)
- Compliance violations (access without proper authentication)

Be concise but specific. If no significant issues are found, indicate low severity."""
        )
    
    def _initialize_llm(self):
        """Initialize the LLM based on configuration"""
        if self.config.llm.provider == "anthropic":
            if not self.config.anthropic_api_key:
                raise ValueError("Anthropic API key not found. Check your .env file.")
            
            self.llm = ChatAnthropic(
                anthropic_api_key=self.config.anthropic_api_key,
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens
            )
            print(f"✅ Claude LLM initialized ({self.config.llm.model})")
            
        elif self.config.llm.provider == "openai":
            # Future: OpenAI implementation
            raise NotImplementedError("OpenAI provider not yet implemented")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.llm.provider}")
    
    def _initialize_slack(self):
        """Initialize Slack integration"""
        if not self.slack_enabled:
            print("🔇 Slack notifications disabled for this analyzer instance")
            return
        
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
        """Analyze logs based on a query and return structured recommendation with optional Slack alert"""
        try:
            # 1. Find similar logs using vector search
            print(f"🔍 Searching for logs related to: '{query}'")
            similar_logs = self.embeddings.search_similar_logs(
                query, 
                n_results=self.config.analysis_chunk_size
            )
            
            if not similar_logs:
                print("❌ No relevant logs found")
                return None
            
            # 2. Format logs for LLM analysis
            log_entries_text = self._format_logs_for_analysis(similar_logs)
            
            # 3. Generate analysis prompt
            prompt_text = self.analysis_prompt.format(
                log_entries=log_entries_text,
                context=context
            )
            
            # 4. Get LLM analysis
            print(f"🤖 Analyzing {len(similar_logs)} relevant log entries with Claude...")
            response = self.llm.invoke(prompt_text)
            
            # 5. Parse response into structured recommendation
            parser = RecommendationParser()
            recommendation = parser.parse(response.content)
            
            # 6. Send Slack alert if enabled and conditions are met
            if send_slack_alert and self._should_send_slack_alert(recommendation):
                self._send_slack_alert(recommendation, source_file)
            
            return recommendation
            
        except Exception as e:
            print(f"❌ Error during log analysis: {e}")
            return None
    
    def analyze_recent_logs(self, hours: int = 1, context: str = "Recent activity analysis", 
                          send_slack_alerts: bool = True) -> List[SecurityRecommendation]:
        """Analyze recent logs for general issues with optional Slack alerts"""
        # For now, we'll simulate this by analyzing common security patterns
        common_queries = [
            "failed login authentication error",
            "database connection timeout error",
            "high memory CPU usage performance",
            "access denied forbidden unauthorized",
            "SSL certificate TLS connection error"
        ]
        
        recommendations = []
        
        for query in common_queries:
            recommendation = self.analyze_logs(
                query, 
                context, 
                source_file="recent_logs",
                send_slack_alert=send_slack_alerts
            )
            if recommendation and recommendation.confidence > 0.3:
                recommendations.append(recommendation)
        
        # Send summary to Slack if multiple issues found
        if send_slack_alerts and recommendations and self.slack_notifier and self.slack_notifier.enabled:
            self._send_slack_summary(recommendations, "recent_logs")
        
        return recommendations
    
    def _should_send_slack_alert(self, recommendation: SecurityRecommendation) -> bool:
        """Determine if a recommendation should trigger a Slack alert"""
        if not self.slack_notifier or not self.slack_notifier.enabled:
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
    
    def _send_slack_summary(self, recommendations: List[SecurityRecommendation], filename: str):
        """Send Slack summary for multiple recommendations"""
        try:
            if hasattr(self.slack_notifier, 'send_summary_report'):
                success = self.slack_notifier.send_summary_report(recommendations, len(recommendations), filename)
                if success:
                    print(f"📱 Slack summary sent: {len(recommendations)} issues")
        except Exception as e:
            print(f"📱 Slack summary error: {e}")
    
    def _format_logs_for_analysis(self, similar_logs: List[Dict]) -> str:
        """Format similar logs for LLM consumption"""
        formatted_logs = []
        
        for i, log in enumerate(similar_logs, 1):
            metadata = log['metadata']
            document = log['document']
            similarity = log['similarity_score']
            
            # Extract useful metadata
            timestamp = metadata.get('timestamp', 'unknown')
            source = metadata.get('source', 'unknown')
            
            formatted_logs.append(
                f"[{i}] Timestamp: {timestamp} | Source: {source} | Similarity: {similarity:.3f}\n"
                f"    Log: {document}\n"
            )
        
        return "\n".join(formatted_logs)
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get statistics about the analysis system"""
        vector_stats = self.embeddings.get_collection_stats()
        slack_status = self.slack_notifier.get_status() if self.slack_notifier else {"enabled": False}
        
        return {
            'llm_provider': self.config.llm.provider,
            'llm_model': self.config.llm.model,
            'vector_database': vector_stats,
            'analysis_chunk_size': self.config.analysis_chunk_size,
            'slack_integration': slack_status
        }
    
    def set_slack_enabled(self, enabled: bool):
        """Enable or disable Slack notifications for this analyzer instance"""
        self.slack_enabled = enabled
        if not enabled:
            print("🔇 Slack notifications disabled")
        elif self.slack_notifier and self.slack_notifier.enabled:
            print("📱 Slack notifications enabled")
        else:
            print("⚠️  Slack notifications requested but not configured")