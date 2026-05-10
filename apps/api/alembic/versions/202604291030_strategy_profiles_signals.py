"""create strategy profiles and signals

Revision ID: 202604291030
Revises: 202604291000
Create Date: 2026-04-29 10:30:00.000000
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291030"
down_revision: str | None = "202604291000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_PROFILES: tuple[dict[str, object], ...] = (
    {
        "key": "breakout_continuation",
        "name": "Breakout Continuation",
        "description": (
            "Classifies clean breakout and continuation setups when structure, "
            "volatility, and candidate strength are aligned."
        ),
        "version": "v1",
        "allowed_patterns": [
            "bullish_breakout",
            "bearish_breakdown",
            "bullish_continuation",
            "bearish_continuation",
        ],
        "excluded_patterns": [
            "fakeout",
            "sideways_range",
            "low_volatility_chop",
            "unclear_structure",
        ],
        "minimum_candidate_strength": "0.6500",
        "minimum_confidence": "0.6500",
        "component_weights": {
            "pattern_strength": "0.35",
            "trend_alignment": "0.20",
            "volatility_confirmation": "0.20",
            "indicator_support": "0.15",
            "data_quality": "0.10",
        },
        "risk_filters": {
            "minimum_data_quality": "0.9000",
            "fakeout_override_margin": "0.1200",
            "chop_override_margin": "0.1000",
            "opposing_bias_conflict_margin": "0.0800",
            "compressed_volatility_blocks_directional": True,
            "contradicting_trend_blocks_directional": True,
        },
        "no_signal_rules": {
            "low_data_quality": True,
            "fakeout_risk": True,
            "compressed_volatility": True,
            "contradicting_trend": True,
        },
    },
    {
        "key": "reversal_rejection",
        "name": "Reversal Rejection",
        "description": (
            "Classifies reversal and rejection behavior when price rejects a boundary "
            "or prior movement weakens."
        ),
        "version": "v1",
        "allowed_patterns": ["bullish_reversal", "bearish_reversal"],
        "excluded_patterns": [],
        "minimum_candidate_strength": "0.6200",
        "minimum_confidence": "0.6000",
        "component_weights": {
            "pattern_strength": "0.40",
            "trend_alignment": "0.15",
            "volatility_confirmation": "0.15",
            "indicator_support": "0.15",
            "data_quality": "0.15",
        },
        "risk_filters": {
            "minimum_data_quality": "0.8500",
            "reversal_required_margin": "0.0800",
            "chop_override_margin": "0.1000",
            "opposing_bias_conflict_margin": "0.0800",
        },
        "no_signal_rules": {
            "weak_reversal_evidence": True,
            "missing_follow_through": True,
            "low_data_quality": True,
            "chop_override": True,
            "stronger_opposing_continuation": True,
        },
    },
    {
        "key": "range_chop_avoidance",
        "name": "Range Chop Avoidance",
        "description": (
            "Protects classification from forcing directional signals in unclear, "
            "sideways, low-volatility, or choppy markets."
        ),
        "version": "v1",
        "allowed_patterns": ["sideways_range", "low_volatility_chop", "unclear_structure"],
        "excluded_patterns": [],
        "minimum_candidate_strength": "0.5000",
        "minimum_confidence": "0.5000",
        "component_weights": {
            "pattern_strength": "0.45",
            "trend_alignment": "0.10",
            "volatility_confirmation": "0.20",
            "indicator_support": "0.05",
            "data_quality": "0.20",
        },
        "risk_filters": {
            "minimum_data_quality": "0.7500",
            "chop_override_margin": "0.1000",
            "opposing_bias_conflict_margin": "0.0800",
        },
        "no_signal_rules": {
            "low_movement_efficiency": True,
            "frequent_direction_changes": True,
            "sideways_or_unclear_trend": True,
            "compressed_volatility": True,
            "directional_candidates_below_threshold": True,
        },
    },
    {
        "key": "fakeout_protection",
        "name": "Fakeout Protection",
        "description": (
            "Prevents false breakout classification when fakeout evidence is stronger "
            "than breakout or continuation evidence."
        ),
        "version": "v1",
        "allowed_patterns": ["fakeout"],
        "excluded_patterns": [],
        "minimum_candidate_strength": "0.5800",
        "minimum_confidence": "0.5800",
        "component_weights": {
            "pattern_strength": "0.45",
            "trend_alignment": "0.10",
            "volatility_confirmation": "0.15",
            "indicator_support": "0.05",
            "data_quality": "0.25",
        },
        "risk_filters": {
            "minimum_data_quality": "0.7500",
            "fakeout_override_margin": "0.1200",
            "opposing_bias_conflict_margin": "0.0800",
        },
        "no_signal_rules": {
            "fakeout_within_conflict_margin": True,
            "failed_to_hold_outside_range": True,
            "wick_rejection": True,
            "contradicting_follow_through": True,
        },
    },
)


def upgrade() -> None:
    op.create_table(
        "strategy_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "allowed_patterns_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "excluded_patterns_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("minimum_candidate_strength", sa.Numeric(5, 4), nullable=False),
        sa.Column("minimum_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "component_weights_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "risk_filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "no_signal_rules_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "minimum_candidate_strength >= 0 and minimum_candidate_strength <= 1",
            name=op.f("ck_strategy_profiles_strategy_profile_minimum_candidate_strength_range"),
        ),
        sa.CheckConstraint(
            "minimum_confidence >= 0 and minimum_confidence <= 1",
            name=op.f("ck_strategy_profiles_strategy_profile_minimum_confidence_range"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_profiles")),
        sa.UniqueConstraint("key", "version", name="uq_strategy_profiles_key_version"),
    )
    op.create_index(
        "ix_strategy_profiles_key_version",
        "strategy_profiles",
        ["key", "version"],
        unique=False,
    )
    op.create_index(
        "ix_strategy_profiles_is_active",
        "strategy_profiles",
        ["is_active"],
        unique=False,
    )
    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("strategy_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=True),
        sa.Column("strategy_profile_version", sa.String(length=32), nullable=True),
        sa.Column(
            "strategy_profile_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("bias", sa.String(length=16), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=True),
        sa.Column("classification_status", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_label", sa.String(length=16), nullable=False),
        sa.Column("candidate_strength", sa.Numeric(5, 4), nullable=True),
        sa.Column("selected_pattern_candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pips_moved", sa.Numeric(24, 10), nullable=True),
        sa.Column("tick_moved", sa.Numeric(24, 10), nullable=True),
        sa.Column("movement_direction", sa.String(length=32), nullable=True),
        sa.Column("movement_quality", sa.String(length=64), nullable=True),
        sa.Column("volatility_state", sa.String(length=64), nullable=True),
        sa.Column("trend_state", sa.String(length=64), nullable=True),
        sa.Column("range_state", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("no_signal_reason", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "classification_status in ('signal', 'no_signal', 'unclear', 'insufficient_evidence')",
            name=op.f("ck_signals_signal_classification_status_allowed"),
        ),
        sa.CheckConstraint(
            "bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name=op.f("ck_signals_signal_bias_allowed"),
        ),
        sa.CheckConstraint(
            "confidence_label in ('low', 'medium', 'high', 'very_high')",
            name=op.f("ck_signals_signal_confidence_label_allowed"),
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 and confidence_score <= 1",
            name=op.f("ck_signals_signal_confidence_score_range"),
        ),
        sa.CheckConstraint(
            "candidate_strength is null or (candidate_strength >= 0 and candidate_strength <= 1)",
            name=op.f("ck_signals_signal_candidate_strength_range"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_signals_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_signals_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_signals_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_profile_id"],
            ["strategy_profiles.id"],
            name=op.f("fk_signals_strategy_profile_id_strategy_profiles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["selected_pattern_candidate_id"],
            ["pattern_candidates.id"],
            name=op.f("fk_signals_selected_pattern_candidate_id_pattern_candidates"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signals")),
        sa.UniqueConstraint("analysis_run_id", name="uq_signals_analysis_run_id"),
    )
    op.create_index("ix_signals_analysis_run_id", "signals", ["analysis_run_id"], unique=False)
    op.create_index(
        "ix_signals_workspace_symbol_timeframe_created",
        "signals",
        ["workspace_id", "symbol_id", "timeframe", "created_at"],
        unique=False,
    )
    op.create_table(
        "signal_confidence_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_name", sa.String(length=80), nullable=False),
        sa.Column("component_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("component_weight", sa.Numeric(5, 4), nullable=False),
        sa.Column("weighted_score", sa.Numeric(6, 5), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "component_score >= 0 and component_score <= 1",
            name=op.f("ck_signal_confidence_components_signal_confidence_component_score_range"),
        ),
        sa.CheckConstraint(
            "component_weight >= 0 and component_weight <= 1",
            name=op.f("ck_signal_confidence_components_signal_confidence_component_weight_range"),
        ),
        sa.CheckConstraint(
            "weighted_score >= 0 and weighted_score <= 1",
            name=op.f(
                "ck_signal_confidence_components_signal_confidence_component_weighted_score_range"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_signal_confidence_components_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_confidence_components")),
    )
    op.create_index(
        "ix_signal_confidence_components_signal_id",
        "signal_confidence_components",
        ["signal_id"],
        unique=False,
    )
    op.create_table(
        "signal_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("direction", sa.String(length=80), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("numeric_value", sa.Numeric(24, 10), nullable=True),
        sa.Column("weight", sa.Numeric(6, 5), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_signal_evidence_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_evidence")),
    )
    op.create_index(
        "ix_signal_evidence_signal_id",
        "signal_evidence",
        ["signal_id"],
        unique=False,
    )
    op.create_table(
        "signal_risk_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name=op.f("ck_signal_risk_notes_signal_risk_note_severity_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_signal_risk_notes_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_risk_notes")),
    )
    op.create_index(
        "ix_signal_risk_notes_signal_id",
        "signal_risk_notes",
        ["signal_id"],
        unique=False,
    )
    seed_strategy_profiles()


def downgrade() -> None:
    op.drop_index("ix_signal_risk_notes_signal_id", table_name="signal_risk_notes")
    op.drop_table("signal_risk_notes")
    op.drop_index("ix_signal_evidence_signal_id", table_name="signal_evidence")
    op.drop_table("signal_evidence")
    op.drop_index(
        "ix_signal_confidence_components_signal_id",
        table_name="signal_confidence_components",
    )
    op.drop_table("signal_confidence_components")
    op.drop_index("ix_signals_workspace_symbol_timeframe_created", table_name="signals")
    op.drop_index("ix_signals_analysis_run_id", table_name="signals")
    op.drop_table("signals")
    op.drop_index("ix_strategy_profiles_is_active", table_name="strategy_profiles")
    op.drop_index("ix_strategy_profiles_key_version", table_name="strategy_profiles")
    op.drop_table("strategy_profiles")


def seed_strategy_profiles() -> None:
    connection = op.get_bind()
    statement = sa.text(
        """
        insert into strategy_profiles (
            id,
            key,
            name,
            description,
            version,
            is_active,
            allowed_patterns_json,
            excluded_patterns_json,
            minimum_candidate_strength,
            minimum_confidence,
            component_weights_json,
            risk_filters_json,
            no_signal_rules_json
        )
        values (
            :id,
            :key,
            :name,
            :description,
            :version,
            true,
            cast(:allowed_patterns_json as jsonb),
            cast(:excluded_patterns_json as jsonb),
            :minimum_candidate_strength,
            :minimum_confidence,
            cast(:component_weights_json as jsonb),
            cast(:risk_filters_json as jsonb),
            cast(:no_signal_rules_json as jsonb)
        )
        on conflict (key, version) do nothing
        """
    )
    for profile in DEFAULT_PROFILES:
        connection.execute(
            statement,
            {
                "id": str(uuid4()),
                "key": profile["key"],
                "name": profile["name"],
                "description": profile["description"],
                "version": profile["version"],
                "allowed_patterns_json": json.dumps(profile["allowed_patterns"]),
                "excluded_patterns_json": json.dumps(profile["excluded_patterns"]),
                "minimum_candidate_strength": profile["minimum_candidate_strength"],
                "minimum_confidence": profile["minimum_confidence"],
                "component_weights_json": json.dumps(profile["component_weights"]),
                "risk_filters_json": json.dumps(profile["risk_filters"]),
                "no_signal_rules_json": json.dumps(profile["no_signal_rules"]),
            },
        )
