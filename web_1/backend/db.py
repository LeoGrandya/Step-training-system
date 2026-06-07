"""Configure the MySQL-backed SQLAlchemy database for the Flask app."""

from __future__ import annotations

import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))


def default_database_uri() -> str:
    """Return the configured MySQL URI without reading or writing .env files."""
    return (
        os.environ.get("POSE3D_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or "mysql+pymysql://root:root@127.0.0.1:3306/pose3d_project_3?charset=utf8mb4"
    )


def init_database(app) -> None:
    """Attach SQLAlchemy to the Flask app using the MySQL target database."""
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", default_database_uri())
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault(
        "SQLALCHEMY_ENGINE_OPTIONS",
        {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        },
    )
    db.init_app(app)
