from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class StrategyProfile(Base):
    __tablename__ = "strategy_profiles"
    __table_args__ = (
        CheckConstraint(
            "minimum_candidate_strength >= 0 and minimum_candidate_strength <= 1",
            name="strategy_profile_minimum_candidate_strength_range",
        ),
        CheckConstraint(
            "minimum_confidence >= 0 and minimum_confidence <= 1",
            name="strategy_profile_minimum_confidence_range",
        ),
        UniqueConstraint("key", "version", name="uq_strategy_profiles_key_version"),
        Index("ix_strategy_profiles_key_version", "key", "version"),
        Index("ix_strategy_profiles_is_active", "is_active"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    allowed_patterns_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    excluded_patterns_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    minimum_candidate_strength: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    minimum_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    component_weights_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    risk_filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    no_signal_rules_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
