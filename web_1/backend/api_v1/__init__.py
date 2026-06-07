"""Versioned REST API blueprint (/api/v1)."""

from __future__ import annotations

from flask import Blueprint

from .analysis import register as register_analysis
from .auth import register as register_auth
from .evaluations import register as register_evaluations
from .footwork_types import register as register_footwork_types
from .meta import register as register_meta
from .rbac import register as register_rbac
from .rbac_guard import register_rbac_guard
from .routes import register as register_routes
from .subjects import register as register_subjects
from .training import register as register_training


api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

register_rbac_guard(api_v1)
register_meta(api_v1)
register_auth(api_v1)
register_subjects(api_v1)
register_footwork_types(api_v1)
register_routes(api_v1)
register_training(api_v1)
register_rbac(api_v1)
register_analysis(api_v1)
register_evaluations(api_v1)
