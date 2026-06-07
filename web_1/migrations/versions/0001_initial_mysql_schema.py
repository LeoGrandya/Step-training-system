"""Initial MySQL schema for pose3d business data.

Revision ID: 0001_initial_mysql_schema
Revises: 
Create Date: 2026-06-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from dialect_utils import json_column


revision = "0001_initial_mysql_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("hand", sa.String(length=16), nullable=False, server_default="right"),
        sa.Column("years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.String(length=32), nullable=False, server_default="amateur"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subjects_name", "subjects", ["name"])
    op.create_index("ix_subjects_is_active", "subjects", ["is_active"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_accounts_status", "accounts", ["status"])

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "account_roles",
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("role_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("account_id", "role_id"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=32), nullable=False),
        sa.Column("permission_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "footwork_types",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_start_cell", sa.Integer(), nullable=True),
        sa.Column("default_sequence", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_footwork_types_name", "footwork_types", ["name"])
    op.create_index("ix_footwork_types_is_active", "footwork_types", ["is_active"])

    op.create_table(
        "route_definitions",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("footwork_type_id", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_norm", sa.String(length=120), nullable=False),
        sa.Column("sequence", sa.String(length=255), nullable=False),
        sa.Column("sequence_canon", sa.String(length=255), nullable=False),
        sa.Column("active_name_sequence_hash", sa.String(length=64), nullable=True),
        sa.Column("start_cell", sa.Integer(), nullable=False),
        sa.Column("rhythm_json", json_column(), nullable=True),
        sa.Column("action_requirements", sa.Text(), nullable=True),
        sa.Column("created_by_account_id", sa.String(length=32), nullable=True),
        sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["footwork_type_id"], ["footwork_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("active_name_sequence_hash", name="uq_route_definitions_active_name_sequence_hash"),
    )
    op.create_index("ix_route_definitions_name", "route_definitions", ["name"])
    op.create_index("ix_route_definitions_is_custom", "route_definitions", ["is_custom"])
    op.create_index("ix_route_definitions_is_active", "route_definitions", ["is_active"])

    op.create_table(
        "route_steps",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("route_definition_id", sa.String(length=32), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("cell", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=True),
        sa.Column("dwell_ms", sa.Integer(), nullable=True),
        sa.Column("rhythm_ms", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["route_definition_id"], ["route_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_definition_id", "step_order", name="uq_route_steps_route_order"),
    )
    op.create_index("ix_route_steps_route_definition_id", "route_steps", ["route_definition_id"])

    op.create_table(
        "training_configs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=32), nullable=False),
        sa.Column("footwork_type_id", sa.String(length=32), nullable=True),
        sa.Column("route_definition_id", sa.String(length=32), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="eval"),
        sa.Column("analysis_profile", sa.String(length=32), nullable=False, server_default="fast"),
        sa.Column("light_duration_ms", sa.Integer(), nullable=True),
        sa.Column("step_interval_ms", sa.Integer(), nullable=True),
        sa.Column("loop_count", sa.Integer(), nullable=True),
        sa.Column("full_table_step_count", sa.Integer(), nullable=True),
        sa.Column("hardware_feedback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("config_snapshot", json_column(), nullable=True),
        sa.Column("created_by_account_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["footwork_type_id"], ["footwork_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["route_definition_id"], ["route_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_configs_subject_id", "training_configs", ["subject_id"])
    op.create_index("ix_training_configs_mode", "training_configs", ["mode"])

    op.create_table(
        "training_videos",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=32), nullable=False),
        sa.Column("training_config_id", sa.String(length=32), nullable=True),
        sa.Column("left_video_path", sa.String(length=512), nullable=False),
        sa.Column("right_video_path", sa.String(length=512), nullable=False),
        sa.Column("left_original_name", sa.String(length=255), nullable=True),
        sa.Column("right_original_name", sa.String(length=255), nullable=True),
        sa.Column("left_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("right_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("stereo_params_path", sa.String(length=512), nullable=True),
        sa.Column("probe_json", json_column(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["training_config_id"], ["training_configs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_videos_subject_id", "training_videos", ["subject_id"])
    op.create_index("ix_training_videos_status", "training_videos", ["status"])

    op.create_table(
        "analysis_jobs",
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=32), nullable=True),
        sa.Column("training_config_id", sa.String(length=32), nullable=True),
        sa.Column("training_video_id", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("fps", sa.Float(), nullable=False, server_default="60"),
        sa.Column("analysis_profile", sa.String(length=32), nullable=False, server_default="fast"),
        sa.Column("input_probe_json", json_column(), nullable=True),
        sa.Column("estimated_duration_s", sa.Float(), nullable=True),
        sa.Column("stereo_params_path", sa.String(length=512), nullable=True),
        sa.Column("step_display_name", sa.String(length=120), nullable=True),
        sa.Column("report_mode", sa.String(length=32), nullable=False, server_default="eval"),
        sa.Column("result_id", sa.String(length=64), nullable=True),
        sa.Column("report_payload_path", sa.String(length=512), nullable=True),
        sa.Column("chart_bundle_path", sa.String(length=512), nullable=True),
        sa.Column("kinematics_dir", sa.String(length=512), nullable=True),
        sa.Column("meta_json", json_column(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["training_config_id"], ["training_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["training_video_id"], ["training_videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_analysis_jobs_subject_id", "analysis_jobs", ["subject_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])
    op.create_index("ix_analysis_jobs_stage", "analysis_jobs", ["stage"])
    op.create_index("ix_analysis_jobs_error_code", "analysis_jobs", ["error_code"])
    op.create_index("ix_analysis_jobs_result_id", "analysis_jobs", ["result_id"])

    op.create_table(
        "kinematics_datasets",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=32), nullable=True),
        sa.Column("training_video_id", sa.String(length=32), nullable=True),
        sa.Column("report_payload_path", sa.String(length=512), nullable=True),
        sa.Column("chart_bundle_path", sa.String(length=512), nullable=True),
        sa.Column("frame_csv_path", sa.String(length=512), nullable=True),
        sa.Column("session_csv_path", sa.String(length=512), nullable=True),
        sa.Column("step_csv_path", sa.String(length=512), nullable=True),
        sa.Column("unit_csv_path", sa.String(length=512), nullable=True),
        sa.Column("summary_json", json_column(), nullable=True),
        sa.Column("derived_stats_json", json_column(), nullable=True),
        sa.Column("quality_flags_json", json_column(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["training_video_id"], ["training_videos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_kinematics_datasets_subject_id", "kinematics_datasets", ["subject_id"])

    op.create_table(
        "kinematics_frame_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.String(length=32), nullable=False),
        sa.Column("frame_index", sa.Integer(), nullable=False),
        sa.Column("time_s", sa.Float(), nullable=True),
        sa.Column("com_speed_mps", sa.Float(), nullable=True),
        sa.Column("com_acceleration_mps2", sa.Float(), nullable=True),
        sa.Column("turning_speed_deg_s", sa.Float(), nullable=True),
        sa.Column("left_knee_angle_deg", sa.Float(), nullable=True),
        sa.Column("right_knee_angle_deg", sa.Float(), nullable=True),
        sa.Column("left_ankle_angle_deg", sa.Float(), nullable=True),
        sa.Column("right_ankle_angle_deg", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["kinematics_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "frame_index", name="uq_kinematics_frame_dataset_frame"),
    )
    op.create_index("ix_kinematics_frame_metrics_dataset_id", "kinematics_frame_metrics", ["dataset_id"])

    op.create_table(
        "evaluation_records",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=32), nullable=False),
        sa.Column("analysis_job_id", sa.String(length=64), nullable=True),
        sa.Column("kinematics_dataset_id", sa.String(length=32), nullable=True),
        sa.Column("footwork_type_id", sa.String(length=32), nullable=True),
        sa.Column("route_definition_id", sa.String(length=32), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=32), nullable=True),
        sa.Column("summary_json", json_column(), nullable=True),
        sa.Column("suggestions_json", json_column(), nullable=True),
        sa.Column("created_by_account_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_job_id"], ["analysis_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["footwork_type_id"], ["footwork_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["kinematics_dataset_id"], ["kinematics_datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_definition_id"], ["route_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evaluation_records_subject_id", "evaluation_records", ["subject_id"])
    op.create_index("ix_evaluation_records_analysis_job_id", "evaluation_records", ["analysis_job_id"])
    op.create_index("ix_evaluation_records_score", "evaluation_records", ["score"])
    op.create_index("ix_evaluation_records_grade", "evaluation_records", ["grade"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=32), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("evaluation_record_id", sa.String(length=32), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="eval"),
        sa.Column("step_name", sa.String(length=120), nullable=True),
        sa.Column("summary_json", json_column(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_record_id"], ["evaluation_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "job_id", name="uq_reports_subject_job"),
    )
    op.create_index("ix_reports_subject_id", "reports", ["subject_id"])
    op.create_index("ix_reports_job_id", "reports", ["job_id"])
    op.create_index("ix_reports_completed_at", "reports", ["completed_at"])
    op.create_index("ix_reports_mode", "reports", ["mode"])
    op.create_index("ix_reports_step_name", "reports", ["step_name"])

    op.create_table(
        "analysis_results",
        sa.Column("result_id", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_json", json_column(), nullable=True),
        sa.Column("summary_metrics_json", json_column(), nullable=True),
        sa.Column("derived_stats_json", json_column(), nullable=True),
        sa.Column("report_path", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.job_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("result_id"),
    )
    op.create_index("ix_analysis_results_job_id", "analysis_results", ["job_id"])
    op.create_index("ix_analysis_results_saved_at", "analysis_results", ["saved_at"])


def downgrade() -> None:
    op.drop_table("analysis_results")
    op.drop_table("reports")
    op.drop_table("evaluation_records")
    op.drop_table("kinematics_frame_metrics")
    op.drop_table("kinematics_datasets")
    op.drop_table("analysis_jobs")
    op.drop_table("training_videos")
    op.drop_table("training_configs")
    op.drop_table("route_steps")
    op.drop_table("route_definitions")
    op.drop_table("footwork_types")
    op.drop_table("role_permissions")
    op.drop_table("account_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("accounts")
    op.drop_table("subjects")
