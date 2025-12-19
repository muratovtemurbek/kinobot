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

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

PORT = os.getenv('PORT', '8000')

def run_gunicorn():
    """Run Django with gunicorn"""
    subprocess.run([
        'gunicorn',
        'config.wsgi:application',
        '--bind', f'0.0.0.0:{PORT}',
        '--workers', '2',
        '--threads', '4',
        '--timeout', '120',
    ])

def run_bot():
    """Run Telegram bot"""
    # Add bot directory to path
    bot_dir = os.path.join(os.path.dirname(__file__), 'bot')
    sys.path.insert(0, bot_dir)

    # Import and run
    import django
    django.setup()

    import asyncio
    from bot.main import main
    asyncio.run(main())

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("Shutting down...")
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run gunicorn in a separate thread (daemon=False so it keeps running)
    gunicorn_thread = threading.Thread(target=run_gunicorn, daemon=False)
    gunicorn_thread.start()

    print("Starting services...")
    print(f"Django running on port {PORT}")
    print("Telegram bot starting...")

    # Run bot in main thread with error handling
    try:
        run_bot()
    except Exception as e:
        print(f"Bot error: {e}")
        print("Bot failed but Django will continue running...")
        # Keep the process alive for Django
        gunicorn_thread.join()
