"""Import the ``validators`` engine from a pinned checkout under a unique package name.

The web process never mutates the engine's global loader paths. Each checkout
gets its own module namespace so two revisions of the engine can coexist and
nothing leaks between submissions.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import sys
from pathlib import Path

ENGINE_MODULES = ("loader", "checks", "gates", "receipts", "admit", "allocation", "execution",
                  "profiles", "bridges", "search", "sitegen")


def import_engine(checkout: Path) -> dict:
    checkout = Path(checkout).resolve()
    package_dir = checkout / "validators"
    if not (package_dir / "__init__.py").exists():
        raise FileNotFoundError(f"{package_dir} does not contain the validators package")
    name = "sr_engine_" + hashlib.sha1(str(checkout).encode("utf-8")).hexdigest()[:12]
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, package_dir / "__init__.py", submodule_search_locations=[str(package_dir)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
    modules = {}
    for sub in ENGINE_MODULES:
        try:
            modules[sub] = importlib.import_module(f"{name}.{sub}")
        except ModuleNotFoundError:
            modules[sub] = None  # older engine revisions may lack newer modules
    return modules
