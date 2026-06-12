"""Backend package initializer.

This module provides a small, safe public surface for the `backend` package:

- `app`: re-export of the FastAPI application defined in ``backend.main``
- ``__version__``: best-effort package version (falls back to "0.0.0" when
  distribution metadata is not available)

Keep this file minimal so other scripts can import the package via
``import backend`` and access ``backend.app`` without having to import
``backend.main`` directly.
"""

from importlib import metadata

try:
    # Try to get distribution version for the package name `backend` — this
    # will work when the project is installed in the environment. If the
    # package isn't installed, fall back to a sensible default.
    __version__ = metadata.version("backend")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"

# Re-export the FastAPI application to make `from backend import app` possible.
from .main import app  # noqa: F401

__all__ = ["app", "__version__"]
