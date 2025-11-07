from typing import Dict

from app.agents.news import NewsGenerationCoordinator


class AgentNewsService:
    """Entry point for agent-based news generation."""

    def __init__(self) -> None:
        self.coordinator = NewsGenerationCoordinator()

    def generate_for_dashboard(self, dashboard_id: str, max_items: int = 5) -> Dict:
        return self.coordinator.generate_for_dashboard(dashboard_id, max_items=max_items)

    def generate_for_all_dashboards(self, max_items: int = 5, limit: int = 1) -> Dict[str, Dict]:
        return self.coordinator.generate_for_all_dashboards(max_items=max_items, limit=limit)


