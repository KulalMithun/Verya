"""Veyra - Standalone Executable Builder.

Builds a single, fully self-contained Windows executable (Veyra.exe) that
bundles the Django backend, OpenWES engines, built React SPA frontend,
static assets, migrations, and template database.

Usage:
    python build_exe.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.resolve()
VENV_PYTHON = ROOT_DIR / '.venv' / 'Scripts' / 'python.exe'


def ensure_python_environment():
    """Ensure we are running with the project virtual environment if present."""
    if VENV_PYTHON.exists():
        current_python = Path(sys.executable).resolve()
        target_python = VENV_PYTHON.resolve()
        if current_python != target_python:
            print(f'[*] Detected virtual environment at: {VENV_PYTHON}')
            print('[*] Re-launching builder using virtual environment Python...')
            result = subprocess.run([str(target_python), str(__file__)] + sys.argv[1:])
            sys.exit(result.returncode)


def ensure_pyinstaller():
    """Ensure PyInstaller is installed in the active environment."""
    try:
        import PyInstaller
        print(f'[*] PyInstaller version {PyInstaller.__version__} is available.')
    except ImportError:
        print('[*] PyInstaller not found. Installing PyInstaller...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])


def verify_frontend_bundle():
    """Verify that frontend static assets have been built."""
    static_web_dir = ROOT_DIR / 'src' / 'backend' / 'InvenTree' / 'web' / 'static' / 'web'
    manifest_file = static_web_dir / '.vite' / 'manifest.json'

    if not manifest_file.exists():
        print('[*] Frontend static bundle missing. Attempting to build frontend...')
        frontend_dir = ROOT_DIR / 'src' / 'frontend'
        if frontend_dir.exists():
            yarn_cmd = shutil.which('yarn') or shutil.which('yarn.cmd')
            npm_cmd = shutil.which('npm') or shutil.which('npm.cmd')
            if yarn_cmd:
                subprocess.check_call([yarn_cmd, 'build'], cwd=str(frontend_dir))
            elif npm_cmd:
                subprocess.check_call([npm_cmd, 'run', 'build'], cwd=str(frontend_dir))
            else:
                print('[!] Warning: Neither yarn nor npm found to build frontend.')
        else:
            print('[!] Warning: Frontend source directory not found.')
    else:
        print('[*] Frontend static bundle verified.')


def create_spec_file():
    """Generate the PyInstaller spec file for Veyra."""
    spec_path = ROOT_DIR / 'Veyra.spec'

    root_posix = ROOT_DIR.as_posix()
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

ROOT_DIR = Path('__ROOT_DIR__').resolve()
BACKEND_DIR = ROOT_DIR / 'src' / 'backend' / 'InvenTree'

# Ensure backend directory is in python path during analysis
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
try:
    import django
    django.setup()
except Exception:
    pass

# Internal Django apps to collect
internal_apps = [
    'InvenTree',
    'openwes',
    'part',
    'stock',
    'build',
    'order',
    'company',
    'common',
    'users',
    'plugin',
    'report',
    'importer',
    'machine',
    'web',
    'generic',
    'data_exporter',
    'scim',
]

# Third party packages to collect
third_party = [
    'rest_framework',
    'corsheaders',
    'django_filters',
    'django_cleanup',
    'mptt',
    'markdownify',
    'djmoney',
    'error_report',
    'django_q',
    'taggit',
    'flags',
    'django_structlog',
    'allauth',
    'django_otp',
    'oauth2_provider',
    'drf_spectacular',
    'maintenance_mode',
    'whitenoise',
    'sesame',
    'anymail',
    'django_mailbox',
    'django_ical',
    'storages',
    'dbbackup',
    'x_forwarded_for',
    'opentelemetry',
]

hidden_imports = [
    'django',
    'django.core.management',
    'django.core.management.commands.runserver',
    'django.core.management.commands.migrate',
    'django.core.management.commands.showmigrations',
    'django.core.management.commands.createsuperuser',
    'django.core.management.commands.collectstatic',
    'django.core.management.commands.check',
    'django.core.servers.basehttp',
    'django.core.handlers.wsgi',
    'wsgiref.simple_server',
    'django.db.backends.sqlite3',
    'django.db.backends.sqlite3.base',
    'django.db.backends.sqlite3.operations',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.admindocs',
    'InvenTree.settings',
    'InvenTree.urls',
    'InvenTree.wsgi',
    'InvenTree.apps',
    'openwes.apps',
    'openwes.urls',
    'openwes.api',
    'openwes.models',
    'openwes.serializers',
    'openwes.engines',
    'openwes.engines.assignment',
    'openwes.engines.routing',
    'openwes.engines.sync',
    'openwes.engines.voice',
    'openwes.status_codes',
    'whitenoise.middleware',
    'whitenoise.storage',
    'x_forwarded_for',
    'x_forwarded_for.middleware',
    'django_structlog',
    'django_structlog.middlewares',
    'opentelemetry',
    'opentelemetry.instrumentation.wsgi',
    'structlog',
    'pytz',
    'zoneinfo',
    'jinja2',
    'weasyprint',
    'yaml',
]

# Collect submodules
for app in internal_apps + third_party:
    try:
        subs = collect_submodules(app)
        hidden_imports.extend(subs)
    except Exception as e:
        pass

# Deduplicate hidden imports
hidden_imports = sorted(list(set(hidden_imports)))

# Data files
datas = [
    # Database and configuration templates
    (str(ROOT_DIR / 'data' / 'inventree.sqlite3'), 'data'),
    (str(ROOT_DIR / 'config' / 'config.yaml'), 'config'),
]

# Collect all backend templates, fixtures, static assets, locales, and migrations
for root, dirs, files in os.walk(str(BACKEND_DIR)):
    folder_name = os.path.basename(root)
    if folder_name in ('templates', 'fixtures', 'static', 'locale', 'migrations'):
        rel = os.path.relpath(root, str(BACKEND_DIR)).replace(os.sep, '/')
        datas.append((root, rel))
        datas.append((root, f'src/backend/InvenTree/{rel}'))


# Collect package data files and metadata
data_packages = [
    'rest_framework',
    'drf_spectacular',
    'allauth',
    'django',
    'fido2',
    'moneyed',
    'djmoney',
    'whitenoise',
    'tablib',
    'qrcode',
    'barcode',
    'weasyprint',
    'tinycss2',
    'pyphen',
    'structlog',
]
for pkg in data_packages:
    try:
        datas.extend(collect_data_files(pkg))
        datas.extend(copy_metadata(pkg))
    except Exception:
        pass

# Deduplicate datas
seen_datas = set()
unique_datas = []
for src, dst in datas:
    if os.path.exists(src) and (src, dst) not in seen_datas:
        seen_datas.add((src, dst))
        unique_datas.append((src, dst))

a = Analysis(
    [str(BACKEND_DIR / 'veyra_launcher.py')],
    pathex=[str(BACKEND_DIR), str(ROOT_DIR)],
    binaries=[],
    datas=unique_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PySide2', 'matplotlib'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Veyra',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    spec_content = spec_content.replace('__ROOT_DIR__', root_posix)

    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print(f'[*] Created PyInstaller specification: {spec_path.name}')
    return spec_path


def build_executable(spec_path: Path):
    """Run PyInstaller with the generated spec file."""
    print('=' * 70)
    print('          Building Veyra Standalone Executable (v1.0)')
    print('=' * 70)
    print('[*] Compiling backend, frontend, engines, and assets...')

    cmd = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--noconfirm',
        '--clean',
        str(spec_path),
    ]

    subprocess.check_call(cmd, cwd=str(ROOT_DIR))

    dist_exe = ROOT_DIR / 'dist' / 'Veyra.exe'
    if dist_exe.exists():
        size_mb = dist_exe.stat().st_size / (1024 * 1024)
        print('\n' + '=' * 70)
        print('  BUILD SUCCESSFUL!')
        print('=' * 70)
        print(f'  Executable: {dist_exe}')
        print(f'  Size:       {size_mb:.2f} MB')
        print('----------------------------------------------------------------------')
        print('  To run Veyra, simply launch:')
        print(f'    dist\\Veyra.exe')
        print('======================================================================\n')
    else:
        print('[!] Error: Expected output executable not found in dist/')
        sys.exit(1)


def main():
    """Main build entry point."""
    ensure_python_environment()
    ensure_pyinstaller()
    verify_frontend_bundle()
    spec_path = create_spec_file()
    build_executable(spec_path)


if __name__ == '__main__':
    main()
