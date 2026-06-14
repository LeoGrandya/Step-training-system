"""Configure the SQLAlchemy database for the Flask app (MySQL or SQLite)."""

from __future__ import annotations

import os
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))


def default_database_uri() -> str:
    """Return the configured database URI.

    Priority: POSE3D_DATABASE_URL > DATABASE_URL > SQLALCHEMY_DATABASE_URI.
    Defaults to SQLite in the web_1/data directory for easy deployment.
    """
    return (
        os.environ.get("POSE3D_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or f"sqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'app.db'}"
    )


def _is_sqlite(uri: str) -> bool:
    return uri.startswith("sqlite")


def _migrate_add_column_if_missing(table: str, column: str, col_type: str) -> None:
    """Add a column to a SQLite table if it doesn't already exist (idempotent)."""
    try:
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _on_sqlite_connect(dbapi_connection, connection_record):
    """Enable foreign key constraints on every SQLite connection."""
    import sqlite3

    if isinstance(dbapi_connection, sqlite3.Connection):
        dbapi_connection.execute("PRAGMA journal_mode=WAL")
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


def init_database(app) -> None:
    """Attach SQLAlchemy to the Flask app."""
    uri = default_database_uri()
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", uri)
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    if _is_sqlite(uri):
        app.config.setdefault(
            "SQLALCHEMY_ENGINE_OPTIONS",
            {"connect_args": {"check_same_thread": False}},
        )
    else:
        app.config.setdefault(
            "SQLALCHEMY_ENGINE_OPTIONS",
            {
                "pool_pre_ping": True,
                "pool_recycle": 280,
            },
        )

    db.init_app(app)

    if _is_sqlite(uri):
        event.listen(Engine, "connect", _on_sqlite_connect)

        # Ensure data directory exists
        db_path = Path(uri.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # SQLite needs create_all since Alembic migrations are MySQL-specific
        from . import models  # noqa: F811 — ensure all models are imported
        with app.app_context():
            db.create_all()

            # Schema migrations for new columns (SQLite does not support ALTER TABLE ADD COLUMN IF NOT EXISTS)
            _migrate_add_column_if_missing("kinematics_datasets", "synced_left_path", "VARCHAR(512)")
            _migrate_add_column_if_missing("kinematics_datasets", "synced_right_path", "VARCHAR(512)")

        # One-time cleanup: deduplicate subjects (safe to run only on SQLite)
        cleanup_marker = db_path.parent / ".cleanup_subjects_done"
        if not cleanup_marker.exists():
            with app.app_context():
                from . import repositories as _repo
                deleted = _repo.cleanup_duplicate_subjects()
                if deleted:
                    import logging
                    logging.getLogger("pose3d").info("Cleaned up %d exact-duplicate subject(s)", deleted)
            try:
                cleanup_marker.touch()
            except OSError:
                pass
