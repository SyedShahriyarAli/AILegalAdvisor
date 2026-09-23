"""
Main entry point for AI Legal Advisor Backend
Run with: python run.py
"""

from app.api import app

if __name__ == '__main__':
    print("Starting AI Legal Advisor API...")
    print("Server: http://localhost:5000")
    print("Health check: http://localhost:5000/health")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
