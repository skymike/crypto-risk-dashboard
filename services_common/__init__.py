"""
services_common namespace package
This makes services/common importable as services_common
"""
import sys
from pathlib import Path
import importlib

# Ensure repo root is in path
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Import services.common modules and make them available as services_common.*
_common_modules = [
    'config', 'db', 'ingest', 'signals', 'schema'
]

for mod_name in _common_modules:
    try:
        mod = importlib.import_module(f'services.common.{mod_name}')
        sys.modules[f'services_common.{mod_name}'] = mod
    except ImportError:
        pass

# Handle adapters package
try:
    adapters = importlib.import_module('services.common.adapters')
    sys.modules['services_common.adapters'] = adapters
    for adapter in ['exchanges', 'open_interest', 'volatility', 'sentiment', 'headlines']:
        try:
            mod = importlib.import_module(f'services.common.adapters.{adapter}')
            sys.modules[f'services_common.adapters.{adapter}'] = mod
        except ImportError:
            pass
except ImportError:
    pass

