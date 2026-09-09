"""Veyra Server Launcher.

Unified entry point for running the Veyra Warehouse Execution System as
a standalone executable or from source.
"""

import argparse
import os
import shutil
import sys
import threading
import time
import webbrowser
from pathlib import Path


def setup_environment():
    """Configure environment, paths, and persistent data directories."""
    is_frozen = getattr(sys, 'frozen', False)

    if is_frozen:
        # Running inside PyInstaller bundle
        bundle_dir = Path(sys._MEIPASS).resolve()
        exe_dir = Path(sys.executable).parent.resolve()
        # Add bundled backend package to python search path
        sys.path.insert(0, str(bundle_dir / 'src' / 'backend' / 'InvenTree'))
        sys.path.insert(0, str(bundle_dir))
    else:
        # Running from source
        bundle_dir = Path(__file__).parent.parent.parent.parent.resolve()
        exe_dir = bundle_dir
        backend_dir = bundle_dir / 'src' / 'backend' / 'InvenTree'
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))

    # Set up persistent directories next to executable or project root
    data_dir = exe_dir / 'data'
    media_dir = data_dir / 'media'
    static_dir = data_dir / 'static'
    backup_dir = data_dir / 'backup'
    config_dir = exe_dir / 'config'

    for d in (data_dir, media_dir, static_dir, backup_dir, config_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Database file setup
    db_file = data_dir / 'inventree.sqlite3'
    if not db_file.exists():
        # Look for seed database inside bundle or source data
        seed_db = bundle_dir / 'data' / 'inventree.sqlite3'
        if not seed_db.exists() and is_frozen:
            seed_db = bundle_dir / 'inventree.sqlite3'
        if seed_db.exists():
            print(f'[*] Initializing database from bundled template: {db_file.name}')
            shutil.copyfile(seed_db, db_file)

    # Config file setup
    cfg_file = config_dir / 'config.yaml'
    if not cfg_file.exists():
        seed_cfg = bundle_dir / 'config' / 'config.yaml'
        if not seed_cfg.exists() and is_frozen:
            seed_cfg = bundle_dir / 'config.yaml'
        if seed_cfg.exists():
            print(f'[*] Initializing configuration file: {cfg_file.name}')
            shutil.copyfile(seed_cfg, cfg_file)

    # Core environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
    os.environ['INVENTREE_DB_ENGINE'] = 'sqlite3'
    os.environ['INVENTREE_DB_NAME'] = str(db_file.resolve())
    os.environ['INVENTREE_MEDIA_ROOT'] = str(media_dir.resolve())
    os.environ['INVENTREE_STATIC_ROOT'] = str(static_dir.resolve())
    os.environ['INVENTREE_BACKUP_DIR'] = str(backup_dir.resolve())
    os.environ['INVENTREE_CONFIG_FILE'] = str(cfg_file.resolve())
    os.environ.setdefault('INVENTREE_SITE_URL', 'http://localhost:8000')

    return exe_dir, data_dir


def open_browser_delayed(url: str, delay_seconds: float = 2.5):
    """Open web browser after a short delay to allow server startup."""
    def _worker():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def print_banner(host: str = 'localhost', port: int = 8000):
    """Print the Veyra server banner with access URLs and credentials."""
    banner = f"""
======================================================================
          VEYRA - Open Warehouse Execution System (v1.0)
======================================================================
  - Dashboard:    http://{host}:{port}/
  - Login Page:   http://{host}:{port}/login
  - Operator HUD: http://{host}:{port}/openwes/operator
  - Supervisor:   http://{host}:{port}/openwes/supervisor
  - Backend API:  http://{host}:{port}/api/openwes/
----------------------------------------------------------------------
  Demo Credentials:
  - Admin (Superuser):  admin / admin123
  - Operations Lead:    manager / demo123
  - Supervisor:         supervisor / demo123
  - Scanner Operator:   operator / demo123
  - Demo Evaluation:    demo / demo123
======================================================================
[*] Server is running on port {port}. Press Ctrl+C to exit.
"""
    print(banner)


def main():
    """Main launcher execution."""
    exe_dir, data_dir = setup_environment()

    # Supported Django management commands
    django_subcommands = {
        'check', 'migrate', 'makemigrations', 'showmigrations',
        'createsuperuser', 'shell', 'collectstatic', 'dumpdata', 'loaddata', 'test'
    }

    # If first argument is an explicit django management command
    if len(sys.argv) > 1 and sys.argv[1] in django_subcommands:
        import django
        from django.core.management import execute_from_command_line

        django.setup()
        execute_from_command_line(sys.argv)
        return

    # Parse server launcher arguments
    parser = argparse.ArgumentParser(description="Veyra Standalone Server")
    parser.add_argument('action', nargs='?', default='run', help='Action to perform (run, serve, start)')
    parser.add_argument('--port', type=int, default=8000, help='Port to run server on (default: 8000)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    args, unknown = parser.parse_known_args()

    print('[*] Initializing Veyra components...')
    import django
    from django.core.management import call_command

    django.setup()

    # Run database migrations
    print('[*] Checking database migrations...')
    try:
        call_command('migrate', interactive=False, verbosity=0)
        print('[*] Database migrations up to date.')
    except Exception as e:
        print(f'[!] Migration warning: {e}')

    try:
        call_command('seed_demo_users')
    except Exception:
        pass

    port = args.port
    host = args.host

    # Schedule browser opening
    if not args.no_browser:
        open_browser_delayed(f'http://localhost:{port}/', delay_seconds=2.0)

    # Print server banner
    print_banner(host='localhost', port=port)

    # Run Django server (serves both SPA frontend and OpenWES backend)
    try:
        call_command('runserver', f'{host}:{port}', use_reloader=False)
    except KeyboardInterrupt:
        print('\n[*] Veyra server stopped. Goodbye!')
    except Exception as e:
        print(f'[!] Error running server: {e}')
        if not getattr(sys, 'frozen', False):
            raise
        input('Press Enter to exit...')



if __name__ == '__main__':
    main()
