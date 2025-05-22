#!/usr/bin/env python3
"""
Flask API backend for WatchDogAI Web Dashboard
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import tempfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import traceback

from .config import get_config
from .analyzer import LogAnalyzer
from .embeddings import LogEmbeddings, LogEntry


class WatchDogAPI:
    """Flask API for WatchDogAI web interface"""
    
    def __init__(self):
        # Set static folder path relative to project root
        static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static')
        self.app = Flask(__name__, static_folder=static_folder)
        CORS(self.app)  # Enable CORS for React frontend
        
        # Configuration
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
        self.upload_folder = tempfile.mkdtemp()
        
        # Initialize WatchDogAI components
        self.analyzer = None
        self.embeddings = None
        self._init_watchdog()
        
        # Register routes
        self._register_routes()
    
    def _init_watchdog(self):
        """Initialize WatchDogAI components with error handling"""
        try:
            print("🔄 Initializing WatchDogAI components...")
            self.config = get_config()
            self.analyzer = LogAnalyzer()
            self.embeddings = LogEmbeddings()
            print("✅ WatchDogAI API ready!")
        except Exception as e:
            print(f"❌ Failed to initialize WatchDogAI: {e}")
            # Don't crash the server, but log the error
            self.analyzer = None
            self.embeddings = None
    
    def _register_routes(self):
        """Register all API routes"""
        
        @self.app.route('/', methods=['GET'])
        def serve_dashboard():
            """Serve the main dashboard"""
            return send_from_directory(self.app.static_folder, 'dashboard.html')
        
        @self.app.route('/static/<path:filename>')
        def serve_static(filename):
            """Serve static files"""
            return send_from_directory(self.app.static_folder, filename)
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'watchdog_available': self.analyzer is not None,
                'version': '1.0.0'
            })
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Get system status and statistics"""
            try:
                if not self.embeddings:
                    return jsonify({'error': 'WatchDogAI not initialized'}), 500
                
                stats = self.embeddings.get_collection_stats()
                config = self.config
                
                return jsonify({
                    'llm_provider': config.llm.provider,
                    'llm_model': config.llm.model,
                    'vector_db': config.vector_db.provider,
                    'total_logs': stats.get('total_logs', 0),
                    'collection_name': stats.get('collection_name', ''),
                    'status': 'ready'
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/upload', methods=['POST'])
        def upload_file():
            """Upload and analyze a log file"""
            try:
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400
                
                if not self._allowed_file(file.filename):
                    return jsonify({'error': 'File type not allowed'}), 400
                
                # Save uploaded file
                filename = secure_filename(file.filename)
                filepath = os.path.join(self.upload_folder, filename)
                file.save(filepath)
                
                # Get file info
                file_size = os.path.getsize(filepath)
                
                return jsonify({
                    'filename': filename,
                    'filepath': filepath,
                    'size': file_size,
                    'status': 'uploaded'
                })
            
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analyze', methods=['POST'])
        def analyze_logs():
            """Analyze uploaded logs"""
            try:
                data = request.get_json()
                filepath = data.get('filepath')
                
                if not filepath or not os.path.exists(filepath):
                    return jsonify({'error': 'File not found'}), 400
                
                if not self.analyzer or not self.embeddings:
                    return jsonify({'error': 'WatchDogAI not initialized'}), 500
                
                # Read and parse log file
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                
                log_entries = self.embeddings.parse_logs(log_content, source=os.path.basename(filepath))
                
                # Embed logs
                self.embeddings.embed_logs(log_entries)
                
                # Run analysis queries
                analyses = []
                
                security_queries = [
                    ("failed login authentication unauthorized access", "Security"),
                    ("error denied forbidden blocked suspicious", "Security"), 
                    ("attack malicious intrusion exploit", "Security"),
                ]
                
                performance_queries = [
                    ("timeout slow performance high memory CPU", "Performance"),
                    ("database connection error timeout", "Performance"),
                    ("server error 500 503 504", "Performance"),
                ]
                
                all_queries = security_queries + performance_queries
                
                for query, category in all_queries:
                    result = self.analyzer.analyze_logs(query, f"{category} analysis")
                    if result and result.confidence > 0.3:
                        analyses.append({
                            'category': category,
                            'issue': result.issue,
                            'severity': result.severity,
                            'confidence': result.confidence,
                            'recommendation': result.recommendation,
                            'affected_systems': result.affected_systems,
                            'timeline': result.timeline
                        })
                
                return jsonify({
                    'filename': os.path.basename(filepath),
                    'total_logs': len(log_entries),
                    'analyses': analyses,
                    'timestamp': datetime.now().isoformat()
                })
            
            except Exception as e:
                print(f"Analysis error: {e}")
                traceback.print_exc()
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/search', methods=['POST'])
        def search_logs():
            """Search existing logs"""
            try:
                data = request.get_json()
                query = data.get('query', '')
                limit = data.get('limit', 10)
                
                if not query:
                    return jsonify({'error': 'Query is required'}), 400
                
                if not self.embeddings:
                    return jsonify({'error': 'WatchDogAI not initialized'}), 500
                
                results = self.embeddings.search_similar_logs(query, limit)
                
                # Format results for frontend
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        'document': result['document'],
                        'similarity': result['similarity_score'],
                        'metadata': result.get('metadata', {}),
                        'timestamp': result.get('metadata', {}).get('timestamp', 'Unknown')
                    })
                
                return jsonify({
                    'query': query,
                    'results': formatted_results,
                    'total': len(formatted_results)
                })
            
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analyze-query', methods=['POST'])
        def analyze_query():
            """Analyze logs based on a specific query"""
            try:
                data = request.get_json()
                query = data.get('query', '')
                context = data.get('context', 'User query')
                
                if not query:
                    return jsonify({'error': 'Query is required'}), 400
                
                if not self.analyzer:
                    return jsonify({'error': 'WatchDogAI not initialized'}), 500
                
                result = self.analyzer.analyze_logs(query, context)
                
                if result:
                    return jsonify({
                        'issue': result.issue,
                        'severity': result.severity,
                        'confidence': result.confidence,
                        'category': result.category,
                        'recommendation': result.recommendation,
                        'affected_systems': result.affected_systems,
                        'timeline': result.timeline,
                        'log_evidence': result.log_evidence
                    })
                else:
                    return jsonify({
                        'issue': 'No significant findings',
                        'severity': 'low',
                        'confidence': 0.1,
                        'category': 'unknown',
                        'recommendation': 'No specific recommendations based on current query.',
                        'affected_systems': [],
                        'timeline': 'none',
                        'log_evidence': []
                    })
            
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/report', methods=['GET'])
        def generate_report():
            """Generate comprehensive analysis report"""
            try:
                if not self.analyzer or not self.embeddings:
                    return jsonify({'error': 'WatchDogAI not initialized'}), 500
                
                # Get system stats
                stats = self.embeddings.get_collection_stats()
                
                if stats.get('total_logs', 0) == 0:
                    return jsonify({'error': 'No logs available for analysis'}), 400
                
                # Run comprehensive analysis
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
                
                report_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_logs': stats.get('total_logs', 0),
                    'categories': []
                }
                
                for category, queries in comprehensive_queries:
                    category_results = []
                    
                    for query in queries:
                        result = self.analyzer.analyze_logs(query, f"{category} analysis")
                        if result and result.confidence > 0.3:
                            category_results.append({
                                'issue': result.issue,
                                'severity': result.severity,
                                'confidence': result.confidence,
                                'recommendation': result.recommendation,
                                'affected_systems': result.affected_systems,
                                'timeline': result.timeline
                            })
                    
                    if category_results:
                        report_data['categories'].append({
                            'name': category,
                            'results': category_results
                        })
                
                return jsonify(report_data)
            
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def _allowed_file(self, filename):
        """Check if file type is allowed"""
        allowed_extensions = {'txt', 'log', 'json', 'csv'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    def run(self, host='localhost', port=5000, debug=True):
        """Run the Flask app"""
        print(f"🚀 Starting WatchDogAI Web API on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)


# Create app instance for external use
def create_app():
    """Factory function to create Flask app"""
    api = WatchDogAPI()
    return api.app


if __name__ == "__main__":
    api = WatchDogAPI()
    api.run()