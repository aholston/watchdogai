#!/usr/bin/env python3
"""
WatchDogAI Command Line Interface

Usage:
    python -m watchdog.cli analyze /var/log/auth.log
    python -m watchdog.cli search "failed login"
    python -m watchdog.cli report --output security_report.md
    python -m watchdog.cli interactive
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List
import json

from .config import get_config, init_config
from .analyzer import LogAnalyzer
from .embeddings import LogEmbeddings


class WatchDogCLI:
    """Command-line interface for WatchDogAI"""
    
    def __init__(self):
        self.config = get_config()
        self.analyzer = None
        self._init_analyzer()
    
    def _init_analyzer(self):
        """Initialize the analyzer with error handling"""
        try:
            print("🔄 Initializing WatchDogAI...")
            self.analyzer = LogAnalyzer()
            print("✅ WatchDogAI ready!")
        except Exception as e:
            print(f"❌ Failed to initialize WatchDogAI: {e}")
            print("💡 Check your .env file has ANTHROPIC_API_KEY set")
            sys.exit(1)
    
    def analyze_file(self, file_path: str, output_format: str = "text", 
                    save_to: Optional[str] = None) -> bool:
        """Analyze a log file"""
        log_file = Path(file_path)
        
        if not log_file.exists():
            print(f"❌ File not found: {file_path}")
            return False
        
        print(f"📂 Analyzing log file: {log_file.name}")
        print(f"   Size: {log_file.stat().st_size:,} bytes")
        
        try:
            # Read log file
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
            
            # Parse logs into entries
            embeddings = LogEmbeddings()
            log_entries = embeddings.parse_logs(log_content, source=str(log_file))
            
            print(f"📊 Parsed {len(log_entries)} log entries")
            
            # Embed logs if not already done
            print("🔄 Embedding logs for analysis...")
            embeddings.embed_logs(log_entries)
            
            # Analyze different categories
            analyses = []
            
            security_queries = [
                "failed login authentication unauthorized access",
                "error denied forbidden blocked",
                "suspicious malicious attack intrusion",
            ]
            
            performance_queries = [
                "timeout slow performance high memory CPU",
                "database connection error timeout",
                "server error 500 503 504",
            ]
            
            print("\n🔍 Running security analysis...")
            for query in security_queries:
                result = self.analyzer.analyze_logs(query, "Security analysis")
                if result and result.severity != "low":
                    analyses.append(("Security", result))
            
            print("🔍 Running performance analysis...")
            for query in performance_queries:
                result = self.analyzer.analyze_logs(query, "Performance analysis") 
                if result and result.severity != "low":
                    analyses.append(("Performance", result))
            
            # Output results
            self._output_results(analyses, output_format, save_to, log_file.name)
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing file: {e}")
            return False
    
    def search_logs(self, query: str, limit: int = 10) -> bool:
        """Search existing logs"""
        try:
            embeddings = LogEmbeddings()
            results = embeddings.search_similar_logs(query, limit)
            
            if not results:
                print(f"🔍 No logs found matching: '{query}'")
                return False
            
            print(f"🔍 Found {len(results)} logs matching: '{query}'\n")
            
            for i, result in enumerate(results, 1):
                similarity = result['similarity_score']
                doc = result['document'][:100] + "..." if len(result['document']) > 100 else result['document']
                
                print(f"{i}. Similarity: {similarity:.2f}")
                print(f"   {doc}")
                print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error searching logs: {e}")
            return False
    
    def generate_report(self, output_file: str = "watchdog_report.md") -> bool:
        """Generate a comprehensive analysis report"""
        try:
            print("📊 Generating comprehensive security report...")
            
            # Get collection stats
            embeddings = LogEmbeddings()
            stats = embeddings.get_collection_stats()
            
            if stats.get('total_logs', 0) == 0:
                print("❌ No logs in database. Analyze some files first.")
                return False
            
            # Run comprehensive analysis
            analyses = []
            
            comprehensive_queries = [
                ("Security Incidents", [
                    "failed login authentication brute force",
                    "unauthorized access denied forbidden",
                    "suspicious malicious attack exploit",
                    "privilege escalation sudo admin root",
                ]),
                ("System Performance", [
                    "high CPU memory usage performance",
                    "database connection timeout error",
                    "disk space full storage warning",
                    "network timeout connection refused",
                ]),
                ("Application Errors", [
                    "exception error stack trace crash",
                    "HTTP 500 502 503 504 error",
                    "database query slow timeout",
                    "API rate limit exceeded",
                ]),
            ]
            
            for category, queries in comprehensive_queries:
                print(f"🔍 Analyzing {category.lower()}...")
                category_results = []
                
                for query in queries:
                    result = self.analyzer.analyze_logs(query, f"{category} analysis")
                    if result and result.confidence > 0.3:
                        category_results.append(result)
                
                if category_results:
                    analyses.append((category, category_results))
            
            # Generate markdown report
            self._generate_markdown_report(analyses, stats, output_file)
            
            print(f"✅ Report saved to: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            return False
    
    def interactive_mode(self):
        """Interactive mode for querying logs"""
        print("🤖 WatchDogAI Interactive Mode")
        print("Ask questions about your logs. Type 'quit' to exit.\n")
        
        while True:
            try:
                query = input("🔍 Query: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not query:
                    continue
                
                # Determine if it's a search or analysis query
                if query.startswith("search "):
                    search_query = query[7:]
                    self.search_logs(search_query)
                else:
                    print(f"🤖 Analyzing: {query}")
                    result = self.analyzer.analyze_logs(query, "Interactive query")
                    
                    if result:
                        print(f"\n📋 Analysis Result:")
                        print(f"   Issue: {result.issue}")
                        print(f"   Severity: {result.severity.upper()}")
                        print(f"   Confidence: {result.confidence:.1%}")
                        print(f"   Category: {result.category}")
                        print(f"   Recommendation: {result.recommendation}")
                        if result.affected_systems:
                            print(f"   Affected Systems: {', '.join(result.affected_systems)}")
                    else:
                        print("🤷 No significant findings for that query.")
                
                print()  # Add spacing
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _output_results(self, analyses: List, format_type: str, save_to: Optional[str], filename: str):
        """Output analysis results in specified format"""
        if not analyses:
            print("✅ No significant issues found in the logs.")
            return
        
        if format_type == "json":
            output = {
                "file": filename,
                "analyses": []
            }
            
            for category, result in analyses:
                output["analyses"].append({
                    "category": category,
                    "issue": result.issue,
                    "severity": result.severity,
                    "confidence": result.confidence,
                    "recommendation": result.recommendation,
                    "affected_systems": result.affected_systems,
                    "timeline": result.timeline
                })
            
            json_output = json.dumps(output, indent=2)
            
            if save_to:
                with open(save_to, 'w') as f:
                    f.write(json_output)
                print(f"✅ Results saved to: {save_to}")
            else:
                print(json_output)
        
        else:  # text format
            print(f"\n📊 Analysis Results for {filename}:")
            print("=" * 50)
            
            for category, result in analyses:
                print(f"\n🔍 {category} Analysis:")
                print(f"   Issue: {result.issue}")
                print(f"   Severity: {result.severity.upper()}")
                print(f"   Confidence: {result.confidence:.1%}")
                print(f"   Timeline: {result.timeline}")
                print(f"   Recommendation: {result.recommendation}")
                
                if result.affected_systems:
                    print(f"   Affected Systems: {', '.join(result.affected_systems)}")
            
            if save_to:
                # Save text format
                with open(save_to, 'w') as f:
                    f.write(f"WatchDogAI Analysis Results for {filename}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for category, result in analyses:
                        f.write(f"{category} Analysis:\n")
                        f.write(f"Issue: {result.issue}\n")
                        f.write(f"Severity: {result.severity.upper()}\n")
                        f.write(f"Confidence: {result.confidence:.1%}\n")
                        f.write(f"Recommendation: {result.recommendation}\n")
                        if result.affected_systems:
                            f.write(f"Affected Systems: {', '.join(result.affected_systems)}\n")
                        f.write("\n")
                
                print(f"✅ Results saved to: {save_to}")
    
    def _generate_markdown_report(self, analyses: List, stats: dict, output_file: str):
        """Generate markdown report"""
        with open(output_file, 'w') as f:
            f.write("# WatchDogAI Security & Performance Report\n\n")
            f.write(f"**Generated:** {self._get_timestamp()}\n")
            f.write(f"**Total Logs Analyzed:** {stats.get('total_logs', 0):,}\n\n")
            
            # Executive Summary
            high_severity = sum(1 for _, results in analyses for result in results if result.severity == 'high')
            medium_severity = sum(1 for _, results in analyses for result in results if result.severity == 'medium')
            
            f.write("## Executive Summary\n\n")
            if high_severity > 0:
                f.write(f"🚨 **{high_severity} HIGH severity issues** requiring immediate attention\n")
            if medium_severity > 0:
                f.write(f"⚠️ **{medium_severity} MEDIUM severity issues** requiring review\n")
            f.write("\n")
            
            # Detailed findings
            for category, results in analyses:
                f.write(f"## {category}\n\n")
                
                for i, result in enumerate(results, 1):
                    severity_emoji = "🚨" if result.severity == "high" else "⚠️" if result.severity == "medium" else "ℹ️"
                    
                    f.write(f"### {i}. {result.issue}\n\n")
                    f.write(f"{severity_emoji} **Severity:** {result.severity.upper()}\n")
                    f.write(f"🎯 **Confidence:** {result.confidence:.1%}\n")
                    f.write(f"⏱️ **Timeline:** {result.timeline}\n\n")
                    f.write(f"**Recommendation:**\n{result.recommendation}\n\n")
                    
                    if result.affected_systems:
                        f.write(f"**Affected Systems:** {', '.join(result.affected_systems)}\n\n")
                    
                    f.write("---\n\n")
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="WatchDogAI - Intelligent Log Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m watchdog.cli analyze /var/log/auth.log
  python -m watchdog.cli analyze app.log --format json --output results.json
  python -m watchdog.cli search "failed login"
  python -m watchdog.cli report --output security_report.md
  python -m watchdog.cli interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a log file')
    analyze_parser.add_argument('file', help='Path to log file')
    analyze_parser.add_argument('--format', choices=['text', 'json'], default='text',
                               help='Output format (default: text)')
    analyze_parser.add_argument('--output', '-o', help='Save results to file')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search existing logs')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', '-l', type=int, default=10,
                              help='Maximum results (default: 10)')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate comprehensive report')
    report_parser.add_argument('--output', '-o', default='watchdog_report.md',
                              help='Output file (default: watchdog_report.md)')
    
    # Interactive command
    subparsers.add_parser('interactive', help='Interactive mode')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = WatchDogCLI()
    
    # Execute command
    if args.command == 'analyze':
        success = cli.analyze_file(args.file, args.format, args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == 'search':
        success = cli.search_logs(args.query, args.limit)
        sys.exit(0 if success else 1)
    
    elif args.command == 'report':
        success = cli.generate_report(args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == 'interactive':
        cli.interactive_mode()
    
    elif args.command == 'status':
        embeddings = LogEmbeddings()
        stats = embeddings.get_collection_stats()
        config = get_config()
        
        print("📊 WatchDogAI Status:")
        print(f"   LLM Provider: {config.llm.provider}")
        print(f"   LLM Model: {config.llm.model}")
        print(f"   Vector Database: {config.vector_db.provider}")
        print(f"   Total Logs: {stats.get('total_logs', 0):,}")
        print(f"   Collection: {stats.get('collection_name', 'N/A')}")


if __name__ == "__main__":
    main()