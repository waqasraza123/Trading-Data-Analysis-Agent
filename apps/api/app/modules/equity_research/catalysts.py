from app.modules.equity_research.models import EquityCatalystImportance


def catalyst_importance_score(importance: str) -> float:
    return {
        EquityCatalystImportance.HIGH.value: 0.85,
        EquityCatalystImportance.MEDIUM.value: 0.65,
        EquityCatalystImportance.LOW.value: 0.52,
        EquityCatalystImportance.UNKNOWN.value: 0.50,
    }.get(importance, 0.50)
