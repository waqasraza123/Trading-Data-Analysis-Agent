from dataclasses import dataclass, field
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.modules.product_readiness.models import ProductReadinessCheckStatus


@dataclass(frozen=True)
class ProductReadinessCheckResult:
    key: str
    status: ProductReadinessCheckStatus
    title: str
    summary: str
    remediation: str
    related_route: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def readiness_check(
    key: str,
    status: ProductReadinessCheckStatus,
    title: str,
    summary: str,
    remediation: str,
    related_route: str | None = None,
    metadata: dict[str, object] | None = None,
) -> ProductReadinessCheckResult:
    return ProductReadinessCheckResult(
        key=key,
        status=status,
        title=title,
        summary=summary,
        remediation=remediation,
        related_route=related_route,
        metadata=metadata or {},
    )


def readiness_check_payload(check: ProductReadinessCheckResult) -> dict[str, object]:
    return {
        "key": check.key,
        "status": check.status.value,
        "title": check.title,
        "summary": check.summary,
        "remediation": check.remediation,
        "related_route": check.related_route,
        "metadata": check.metadata,
    }


def known_alembic_heads() -> list[str] | None:
    alembic_root = find_alembic_root()
    if alembic_root is None:
        return None
    config = Config(str(alembic_root / "alembic.ini"))
    config.set_main_option("script_location", str(alembic_root / "alembic"))
    script_directory = ScriptDirectory.from_config(config)
    return sorted(script_directory.get_heads())


def find_alembic_root() -> Path | None:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if (parent / "alembic.ini").exists() and (parent / "alembic").exists():
            return parent
    return None
