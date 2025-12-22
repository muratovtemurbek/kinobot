#!/usr/bin/env python
"""
Start script for Railway deployment.
Runs both Django (gunicorn) and the Telegram bot concurrently.
"""
import os
import sys
import subprocess
import signal
import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

PORT = os.getenv('PORT', '8000')

# Global process references for cleanup
bot_process = None
gunicorn_process = None

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("Shutting down...")
    if bot_process:
        bot_process.terminate()
    if gunicorn_process:
        gunicorn_process.terminate()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 50)
    print("Starting KinoBot Services...")
    print("=" * 50)

    # Start gunicorn FIRST (for health check)
    print(f"Starting Django/Gunicorn on port {PORT}...")
    gunicorn_process = subprocess.Popen([
        sys.executable, '-m', 'gunicorn',
        'config.wsgi:application',
        '--bind', f'0.0.0.0:{PORT}',
        '--workers', '1',
        '--threads', '2',
        '--timeout', '120',
        '--access-logfile', '-',
        '--error-logfile', '-',
    ])

    # Wait for gunicorn to start
    time.sleep(3)

    # Check if gunicorn is running
    if gunicorn_process.poll() is not None:
        print("ERROR: Gunicorn failed to start!")
        sys.exit(1)

    print("Gunicorn started successfully!")

    # Start bot
    print("Starting Telegram bot...")
    bot_process = subprocess.Popen(
        [sys.executable, '-m', 'bot.main'],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    print("=" * 50)
    print("All services started!")
    print("=" * 50)

    # Wait for gunicorn (main process)
    # If gunicorn dies, exit
    gunicorn_process.wait()

    # Cleanup bot if gunicorn exits
    if bot_process:
        bot_process.terminate()
