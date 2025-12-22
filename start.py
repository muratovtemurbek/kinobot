#!/usr/bin/env python
"""
Start script for Railway deployment.
Runs both Django (gunicorn) and the Telegram bot concurrently.
"""
import os
import sys
import subprocess
import threading
import signal
import time

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

PORT = os.getenv('PORT', '8000')

# Global process reference for cleanup
bot_process = None

def run_bot():
    """Run Telegram bot as subprocess"""
    global bot_process
    try:
        print("Starting Telegram bot...")
        bot_process = subprocess.Popen(
            [sys.executable, '-m', 'bot.main'],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        bot_process.wait()
    except Exception as e:
        print(f"Bot error: {e}")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("Shutting down...")
    if bot_process:
        bot_process.terminate()
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Starting services...")

    # Run bot in a separate thread (daemon=True so it doesn't block shutdown)
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Give bot a moment to start
    time.sleep(2)

    print(f"Starting Django on port {PORT}...")

    # Run gunicorn in main process (for health check to work)
    os.execvp('gunicorn', [
        'gunicorn',
        'config.wsgi:application',
        '--bind', f'0.0.0.0:{PORT}',
        '--workers', '2',
        '--threads', '4',
        '--timeout', '120',
        '--access-logfile', '-',
        '--error-logfile', '-',
    ])
