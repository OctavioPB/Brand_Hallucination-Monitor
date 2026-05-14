"""Canonical BrandManifest schema — re-exported from apps.api.models.brand.

ml/ modules import from here to stay decoupled from the FastAPI app layer.
The single source of truth is apps/api/models/brand.py:BrandManifest.
"""
from apps.api.models.brand import BrandManifest

__all__ = ["BrandManifest"]
