from app.core.errors import AppError
from app.modules.equity_research.models import EquityUniverse, EquityUniverseStatus


def ensure_universe_can_change(universe: EquityUniverse) -> None:
    if universe.status == EquityUniverseStatus.ARCHIVED.value:
        raise AppError(422, "equity_universe_archived", "Archived universes cannot be changed")
