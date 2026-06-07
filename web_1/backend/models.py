"""SQLAlchemy models for the MySQL migration schema."""

from __future__ import annotations

from datetime import datetime, timezone

from .db import db
from .json_text import JsonText


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    age = db.Column(db.Integer)
    height_cm = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    hand = db.Column(db.String(16), nullable=False, default="right")
    years = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.String(32), nullable=False, default="amateur")
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    deleted_at = db.Column(db.DateTime(timezone=True))


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.String(32), primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.String(32), primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.String(32), primary_key=True)
    code = db.Column(db.String(120), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class AccountRole(db.Model):
    __tablename__ = "account_roles"

    account_id = db.Column(db.String(32), db.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    role_id = db.Column(db.String(32), db.ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class RolePermission(db.Model):
    __tablename__ = "role_permissions"

    role_id = db.Column(db.String(32), db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = db.Column(db.String(32), db.ForeignKey("permissions.id", ondelete="RESTRICT"), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class FootworkType(db.Model):
    __tablename__ = "footwork_types"

    id = db.Column(db.String(32), primary_key=True)
    code = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(64))
    description = db.Column(db.Text)
    default_start_cell = db.Column(db.Integer)
    default_sequence = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    deleted_at = db.Column(db.DateTime(timezone=True))


class RouteDefinition(db.Model):
    __tablename__ = "route_definitions"
    __table_args__ = (
        db.UniqueConstraint("active_name_sequence_hash", name="uq_route_definitions_active_name_sequence_hash"),
    )

    id = db.Column(db.String(32), primary_key=True)
    footwork_type_id = db.Column(db.String(32), db.ForeignKey("footwork_types.id", ondelete="RESTRICT"))
    name = db.Column(db.String(120), nullable=False, index=True)
    name_norm = db.Column(db.String(120), nullable=False)
    sequence = db.Column(db.String(255), nullable=False)
    sequence_canon = db.Column(db.String(255), nullable=False)
    active_name_sequence_hash = db.Column(db.String(64), nullable=True)
    start_cell = db.Column(db.Integer, nullable=False)
    rhythm_json = db.Column(JsonText)
    action_requirements = db.Column(db.Text)
    created_by_account_id = db.Column(db.String(32), db.ForeignKey("accounts.id", ondelete="SET NULL"))
    is_custom = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    deleted_at = db.Column(db.DateTime(timezone=True))


class RouteStep(db.Model):
    __tablename__ = "route_steps"
    __table_args__ = (
        db.UniqueConstraint("route_definition_id", "step_order", name="uq_route_steps_route_order"),
    )

    id = db.Column(db.String(32), primary_key=True)
    route_definition_id = db.Column(
        db.String(32),
        db.ForeignKey("route_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order = db.Column(db.Integer, nullable=False)
    cell = db.Column(db.Integer, nullable=False)
    action_type = db.Column(db.String(64))
    dwell_ms = db.Column(db.Integer)
    rhythm_ms = db.Column(db.Integer)
    note = db.Column(db.String(255))


class TrainingConfig(db.Model):
    __tablename__ = "training_configs"

    id = db.Column(db.String(32), primary_key=True)
    subject_id = db.Column(db.String(32), db.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    footwork_type_id = db.Column(db.String(32), db.ForeignKey("footwork_types.id", ondelete="RESTRICT"))
    route_definition_id = db.Column(db.String(32), db.ForeignKey("route_definitions.id", ondelete="RESTRICT"))
    mode = db.Column(db.String(32), nullable=False, default="eval", index=True)
    analysis_profile = db.Column(db.String(32), nullable=False, default="fast")
    light_duration_ms = db.Column(db.Integer)
    step_interval_ms = db.Column(db.Integer)
    loop_count = db.Column(db.Integer)
    full_table_step_count = db.Column(db.Integer)
    hardware_feedback = db.Column(db.Boolean, nullable=False, default=False)
    config_snapshot = db.Column(JsonText)
    created_by_account_id = db.Column(db.String(32), db.ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)


class TrainingVideo(db.Model):
    __tablename__ = "training_videos"

    id = db.Column(db.String(32), primary_key=True)
    subject_id = db.Column(db.String(32), db.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    training_config_id = db.Column(db.String(32), db.ForeignKey("training_configs.id", ondelete="SET NULL"))
    left_video_path = db.Column(db.String(512), nullable=False)
    right_video_path = db.Column(db.String(512), nullable=False)
    left_original_name = db.Column(db.String(255))
    right_original_name = db.Column(db.String(255))
    left_size_bytes = db.Column(db.BigInteger)
    right_size_bytes = db.Column(db.BigInteger)
    stereo_params_path = db.Column(db.String(512))
    probe_json = db.Column(JsonText)
    status = db.Column(db.String(32), nullable=False, default="uploaded", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class AnalysisJob(db.Model):
    __tablename__ = "analysis_jobs"

    job_id = db.Column(db.String(64), primary_key=True)
    subject_id = db.Column(db.String(32), db.ForeignKey("subjects.id", ondelete="RESTRICT"), index=True)
    training_config_id = db.Column(db.String(32), db.ForeignKey("training_configs.id", ondelete="SET NULL"))
    training_video_id = db.Column(db.String(32), db.ForeignKey("training_videos.id", ondelete="SET NULL"))
    status = db.Column(db.String(32), nullable=False, default="queued", index=True)
    stage = db.Column(db.String(32), index=True)
    progress = db.Column(db.Float, nullable=False, default=0.0)
    message = db.Column(db.Text)
    error = db.Column(db.Text)
    error_code = db.Column(db.String(64), index=True)
    fps = db.Column(db.Float, nullable=False, default=60.0)
    analysis_profile = db.Column(db.String(32), nullable=False, default="fast")
    input_probe_json = db.Column(JsonText)
    estimated_duration_s = db.Column(db.Float)
    stereo_params_path = db.Column(db.String(512))
    step_display_name = db.Column(db.String(120))
    report_mode = db.Column(db.String(32), nullable=False, default="eval")
    result_id = db.Column(db.String(64), index=True)
    report_payload_path = db.Column(db.String(512))
    chart_bundle_path = db.Column(db.String(512))
    kinematics_dir = db.Column(db.String(512))
    meta_json = db.Column(JsonText)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, onupdate=now_utc)
    completed_at = db.Column(db.DateTime(timezone=True))


class KinematicsDataset(db.Model):
    __tablename__ = "kinematics_datasets"

    id = db.Column(db.String(32), primary_key=True)
    job_id = db.Column(
        db.String(64),
        db.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    subject_id = db.Column(db.String(32), db.ForeignKey("subjects.id", ondelete="RESTRICT"), index=True)
    training_video_id = db.Column(db.String(32), db.ForeignKey("training_videos.id", ondelete="SET NULL"))
    report_payload_path = db.Column(db.String(512))
    chart_bundle_path = db.Column(db.String(512))
    frame_csv_path = db.Column(db.String(512))
    session_csv_path = db.Column(db.String(512))
    step_csv_path = db.Column(db.String(512))
    unit_csv_path = db.Column(db.String(512))
    summary_json = db.Column(JsonText)
    derived_stats_json = db.Column(JsonText)
    quality_flags_json = db.Column(JsonText)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class KinematicsFrameMetric(db.Model):
    __tablename__ = "kinematics_frame_metrics"
    __table_args__ = (
        db.UniqueConstraint("dataset_id", "frame_index", name="uq_kinematics_frame_dataset_frame"),
    )

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    dataset_id = db.Column(
        db.String(32),
        db.ForeignKey("kinematics_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    frame_index = db.Column(db.Integer, nullable=False)
    time_s = db.Column(db.Float)
    com_speed_mps = db.Column(db.Float)
    com_acceleration_mps2 = db.Column(db.Float)
    turning_speed_deg_s = db.Column(db.Float)
    left_knee_angle_deg = db.Column(db.Float)
    right_knee_angle_deg = db.Column(db.Float)
    left_ankle_angle_deg = db.Column(db.Float)
    right_ankle_angle_deg = db.Column(db.Float)


class EvaluationRecord(db.Model):
    __tablename__ = "evaluation_records"

    id = db.Column(db.String(32), primary_key=True)
    subject_id = db.Column(db.String(32), db.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    analysis_job_id = db.Column(db.String(64), db.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), index=True)
    kinematics_dataset_id = db.Column(db.String(32), db.ForeignKey("kinematics_datasets.id", ondelete="SET NULL"))
    footwork_type_id = db.Column(db.String(32), db.ForeignKey("footwork_types.id", ondelete="RESTRICT"))
    route_definition_id = db.Column(db.String(32), db.ForeignKey("route_definitions.id", ondelete="RESTRICT"))
    score = db.Column(db.Integer, index=True)
    grade = db.Column(db.String(32), index=True)
    summary_json = db.Column(JsonText)
    suggestions_json = db.Column(JsonText)
    created_by_account_id = db.Column(db.String(32), db.ForeignKey("accounts.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)


class Report(db.Model):
    __tablename__ = "reports"
    __table_args__ = (
        db.UniqueConstraint("subject_id", "job_id", name="uq_reports_subject_job"),
    )

    id = db.Column(db.String(32), primary_key=True)
    subject_id = db.Column(db.String(32), db.ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True)
    job_id = db.Column(db.String(64), db.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    evaluation_record_id = db.Column(db.String(32), db.ForeignKey("evaluation_records.id", ondelete="SET NULL"))
    completed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, index=True)
    mode = db.Column(db.String(32), nullable=False, default="eval", index=True)
    step_name = db.Column(db.String(120), index=True)
    summary_json = db.Column(JsonText, nullable=False)


class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"

    result_id = db.Column(db.String(64), primary_key=True)
    job_id = db.Column(db.String(64), db.ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    saved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc, index=True)
    profile_json = db.Column(JsonText)
    summary_metrics_json = db.Column(JsonText)
    derived_stats_json = db.Column(JsonText)
    report_path = db.Column(db.String(512))
