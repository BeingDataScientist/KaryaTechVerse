"""
Script to run the web dashboard separately.
"""

from dashboard.app import app

if __name__ == '__main__':
    print("="*60)
    print("Starting Flask dashboard server...")
    print("="*60)
    print("Video Upload Page: http://localhost:5000/")
    print("Analysis Dashboard: http://localhost:5000/dashboard")
    print("="*60)
    print("Press CTRL+C to stop")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

